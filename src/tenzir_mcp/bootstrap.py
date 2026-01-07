"""Bootstrap documentation data on first run.

This module checks for required documentation assets and builds them
if missing. This enables a smooth first-run experience for developers
without requiring manual setup steps.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tenzir_mcp.logging_utils import get_logger

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = get_logger("bootstrap")

# Paths relative to this module
DATA_DIR = Path(__file__).parent / "data"
DOCS_DIR = DATA_DIR / "docs"
INDEX_PATH = DATA_DIR / "doc_index.json"
DB_PATH = DATA_DIR / "docs.db"
OCSF_DIR = DATA_DIR / "ocsf"

# Docs configuration
DOCS_REPO = "https://github.com/tenzir/docs.git"

# OCSF configuration
OCSF_SERVER = "https://schema.ocsf.io"
OCSF_EXCLUDE_VERSIONS = ["1.0.0-rc.2", "1.0.0-rc.3"]

# Network timeout (OCSF server can be slow)
TIMEOUT = 120


def ensure_data(*, docs: bool = True, ocsf: bool = True) -> None:
    """Ensure data exists, building if necessary.

    Args:
        docs: Whether to ensure documentation exists
        ocsf: Whether to ensure OCSF schemas exist
    """
    if docs and not DB_PATH.exists():
        logger.info("documentation database not found, building...")
        if not DOCS_DIR.exists():
            _download_docs()
        if not INDEX_PATH.exists():
            _build_index()
        _build_database()

    if ocsf:
        needs_ocsf = not OCSF_DIR.exists() or not any(OCSF_DIR.glob("*.json"))
        if needs_ocsf:
            _download_ocsf()


def _download_docs() -> None:
    """Clone docs repo, build with LLMS_TXT, and copy built .md files."""
    import subprocess

    logger.info("building documentation from tenzir/docs")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        repo_dir = temp_path / "docs"

        # Clone the docs repo (shallow clone for speed)
        logger.info("cloning docs repository...")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", DOCS_REPO, str(repo_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.error("failed to clone docs repo: %s", result.stderr)
            sys.exit(1)

        # Get commit SHA for metadata
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
        )
        commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
        logger.info("commit: %s", commit_sha[:8])

        # Install dependencies
        logger.info("installing dependencies...")
        result = subprocess.run(
            ["pnpm", "install", "--frozen-lockfile"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=300,
        )
        if result.returncode != 0:
            logger.error("failed to install dependencies: %s", result.stderr)
            sys.exit(1)

        # Generate excalidraw placeholders (needed for build)
        logger.info("generating excalidraw placeholders...")
        result = subprocess.run(
            ["pnpm", "generate:excalidraw:placeholders"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning("excalidraw placeholders failed: %s", result.stderr)

        # Build with LLMS_TXT to generate .md files
        logger.info("building documentation (this may take a few minutes)...")
        env = os.environ.copy()
        env["LLMS_TXT"] = "true"
        result = subprocess.run(
            ["pnpm", "build"],
            capture_output=True,
            text=True,
            cwd=repo_dir,
            env=env,
            timeout=600,
        )
        if result.returncode != 0:
            logger.error("failed to build docs: %s", result.stderr)
            sys.exit(1)

        # Copy built .md files from dist/
        dist_dir = repo_dir / "dist"
        if not dist_dir.exists():
            logger.error("dist directory not found after build")
            sys.exit(1)

        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        files_copied = 0

        for md_file in dist_dir.rglob("*.md"):
            rel_path = md_file.relative_to(dist_dir)
            dest_path = DOCS_DIR / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest_path)
            files_copied += 1

    # Create metadata file
    metadata = {
        "commit_sha": commit_sha,
        "repository": "https://github.com/tenzir/docs",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metadata_file = DOCS_DIR / ".metadata.json"
    with metadata_file.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("built and copied %d documentation files", files_copied)


def _download_ocsf() -> None:
    """Download OCSF schemas from schema.ocsf.io."""
    import re

    try:
        import requests
    except ImportError:
        logger.error("requests library not available - install with: uv add requests")
        sys.exit(1)

    logger.info("downloading OCSF schemas from %s", OCSF_SERVER)

    # Fetch available versions
    try:
        response = requests.get(OCSF_SERVER, timeout=TIMEOUT)
        response.raise_for_status()
        body = response.content.decode()
        versions = sorted(
            version
            for version in re.findall("<option value=[^>]*>v([^<]*)</option>", body)
            if version not in OCSF_EXCLUDE_VERSIONS
        )
        logger.info("found %d OCSF versions", len(versions))
    except requests.RequestException as e:
        logger.error("failed to fetch OCSF versions: %s", e)
        sys.exit(1)

    OCSF_DIR.mkdir(parents=True, exist_ok=True)

    # Download each version
    downloaded = 0
    for version in versions:
        url = f"{OCSF_SERVER}/{version}/export/schema"
        try:
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            schema = response.json()
            filepath = OCSF_DIR / f"{version}.json"
            with filepath.open("w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
            downloaded += 1
        except requests.RequestException as e:
            logger.warning("failed to download OCSF %s: %s", version, e)
            continue

    logger.info("downloaded %d OCSF schema files", downloaded)


def _build_index() -> None:
    """Build the documentation index from built docs."""
    import re

    logger.info("building documentation index")

    if not DOCS_DIR.exists():
        logger.error("documentation not found at %s", DOCS_DIR)
        sys.exit(1)

    see_also_pattern = re.compile(r"^##\s+See\s+Also\s*$", re.IGNORECASE | re.MULTILINE)
    markdown_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    title_pattern = re.compile(r"^#\s+(.+)$", re.MULTILINE)

    def extract_title(markdown: str) -> str:
        match = title_pattern.search(markdown)
        return match.group(1).strip() if match else ""

    def resolve_link_target(target: str) -> str | None:
        """Resolve a link target to a normalized doc path."""
        target = target.strip()
        if not target or target.startswith("#"):
            return None
        if re.match(r"^[a-z]+://", target):
            return None

        # Remove leading slash and .md extension
        normalized = target.lstrip("/")
        if normalized.endswith(".md"):
            normalized = normalized[:-3]
        return normalized

    def normalize_doc_path(file_path: Path) -> str:
        """Convert file path to normalized doc path."""
        relative = file_path.relative_to(DOCS_DIR)
        # Remove .md extension
        path_str = str(relative.with_suffix(""))
        return path_str

    def classify_doc(normalized_path: str) -> str:
        if normalized_path.startswith("tutorials/"):
            return "tutorial"
        if normalized_path.startswith("guides/"):
            return "guide"
        if normalized_path.startswith("explanations/"):
            return "explanation"
        if normalized_path.startswith("integrations/"):
            return "integration"
        if normalized_path.startswith("reference/operators/"):
            return "operator"
        if normalized_path.startswith("reference/functions/"):
            return "function"
        if normalized_path.startswith("reference/mcp-server/"):
            return "mcp"
        if normalized_path.startswith("reference/node/"):
            return "api"
        if normalized_path.startswith("reference/platform/"):
            return "api"
        if normalized_path.startswith("reference/test-framework/"):
            return "test"
        if normalized_path.startswith("reference/changelog-framework/"):
            return "changelog"
        if normalized_path.startswith("reference/"):
            return "reference"
        return "doc"

    def extract_cross_links(markdown: str) -> list[dict[str, str]]:
        """Extract See Also links from markdown."""
        match = see_also_pattern.search(markdown)
        if not match:
            return []

        start = match.end()
        subsequent_heading = re.search(r"^##\s+", markdown[start:], re.MULTILINE)
        end = (
            start + subsequent_heading.start() if subsequent_heading else len(markdown)
        )
        section = markdown[start:end]

        links: list[dict[str, str]] = []

        for link_text, target in markdown_link_pattern.findall(section):
            resolved = resolve_link_target(target)
            if resolved is None:
                continue
            links.append(
                {
                    "title": link_text.strip(),
                    "path": resolved,
                    "type": classify_doc(resolved),
                }
            )

        return links

    def doc_entry(
        normalized_path: str,
        doc_type: str,
        title: str,
        see_also: Iterable[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "path": normalized_path,
            "title": title or normalized_path.split("/")[-1],
            "category": "Uncategorized",
            "example": "",
            "type": doc_type,
            "see_also": list(see_also),
        }

    cross_link_total = 0

    index: dict[str, Any] = {
        "operators": {},
        "functions": {},
        "tutorials": {},
        "documents": {},
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "operator_count": 0,
            "function_count": 0,
            "tutorial_count": 0,
            "cross_link_count": 0,
        },
    }

    for source_path in sorted(DOCS_DIR.rglob("*.md")):
        if source_path.name.startswith("_") or source_path.name.startswith("."):
            continue
        normalized = normalize_doc_path(source_path)
        if "changelog" in source_path.relative_to(DOCS_DIR).parts:
            continue
        if normalized in index["documents"]:
            continue
        markdown = source_path.read_text(encoding="utf-8")
        title = extract_title(markdown)
        see_also = extract_cross_links(markdown)
        cross_link_total += len(see_also)

        doc_type = classify_doc(normalized)
        entry = doc_entry(normalized, doc_type, title, see_also)
        index["documents"][normalized] = entry

        if doc_type == "operator":
            index["operators"][normalized] = {
                **{
                    key: entry[key]
                    for key in ("path", "title", "category", "example", "see_also")
                },
                "name": normalized.split("/")[-1],
            }
        elif doc_type == "function":
            index["functions"][normalized] = {
                **{
                    key: entry[key]
                    for key in ("path", "title", "category", "example", "see_also")
                },
                "name": normalized.split("/")[-1],
            }
        elif doc_type == "tutorial":
            if normalized.count("/") == 1:
                index["tutorials"][normalized] = {
                    "path": normalized,
                    "title": entry["title"],
                    "see_also": entry["see_also"],
                }

    index["metadata"]["operator_count"] = len(index["operators"])
    index["metadata"]["function_count"] = len(index["functions"])
    index["metadata"]["tutorial_count"] = len(index["tutorials"])
    index["metadata"]["cross_link_count"] = cross_link_total

    index["operators"] = dict(sorted(index["operators"].items()))
    index["functions"] = dict(sorted(index["functions"].items()))
    index["tutorials"] = dict(sorted(index["tutorials"].items()))
    index["documents"] = dict(sorted(index["documents"].items()))

    INDEX_PATH.write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    logger.info(
        "indexed %d operators, %d functions, %d tutorials",
        index["metadata"]["operator_count"],
        index["metadata"]["function_count"],
        index["metadata"]["tutorial_count"],
    )


def _build_database() -> None:
    """Build SQLite FTS5 database from the JSON index."""
    logger.info("building sqlite database")

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        index = json.load(f)

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE VIRTUAL TABLE docs_fts USING fts5(
            path UNINDEXED,
            title,
            name,
            category,
            example,
            type UNINDEXED,
            tokenize = 'porter ascii'
        )
    """)

    cursor.execute("""
        CREATE TABLE see_also (
            doc_path TEXT NOT NULL,
            see_also_path TEXT NOT NULL,
            see_also_title TEXT NOT NULL,
            see_also_type TEXT NOT NULL,
            PRIMARY KEY (doc_path, see_also_path)
        )
    """)

    cursor.execute("""
        CREATE INDEX idx_see_also_doc_path ON see_also(doc_path)
    """)

    doc_count = 0
    link_count = 0
    inserted_paths: set[str] = set()

    for section in ["operators", "functions", "tutorials", "documents"]:
        section_data = index.get(section, {})
        for path, entry in section_data.items():
            if path in inserted_paths:
                continue
            inserted_paths.add(path)

            doc_type = entry.get("type", section.rstrip("s"))

            cursor.execute(
                """
                INSERT INTO docs_fts (path, title, name, category, example, type)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    path,
                    entry.get("title", ""),
                    entry.get("name", ""),
                    entry.get("category", ""),
                    entry.get("example", ""),
                    doc_type,
                ),
            )
            doc_count += 1

            for see_also in entry.get("see_also", []):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO see_also
                    (doc_path, see_also_path, see_also_title, see_also_type)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        path,
                        see_also.get("path", ""),
                        see_also.get("title", ""),
                        see_also.get("type", ""),
                    ),
                )
                link_count += 1

    cursor.execute("""
        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    metadata = index.get("metadata", {})
    for key, value in metadata.items():
        cursor.execute(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            (key, str(value)),
        )

    conn.commit()
    conn.close()

    logger.info(
        "built database with %d documents and %d cross-links", doc_count, link_count
    )


def clean() -> None:
    """Remove all generated data files."""
    import shutil

    removed = []

    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
        removed.append("docs/")

    if INDEX_PATH.exists():
        INDEX_PATH.unlink()
        removed.append("doc_index.json")

    if DB_PATH.exists():
        DB_PATH.unlink()
        removed.append("docs.db")

    for schema_file in OCSF_DIR.glob("*.json"):
        schema_file.unlink()
        removed.append(f"ocsf/{schema_file.name}")

    if removed:
        for item in removed:
            logger.info("removed %s", item)
    else:
        logger.info("nothing to clean")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bootstrap Tenzir MCP data")
    parser.add_argument(
        "--clean", action="store_true", help="Remove all generated data files"
    )
    parser.add_argument(
        "--docs-only",
        action="store_true",
        help="Only bootstrap documentation (skip OCSF)",
    )
    parser.add_argument(
        "--ocsf-only",
        action="store_true",
        help="Only bootstrap OCSF schemas (skip docs)",
    )

    args = parser.parse_args()

    if args.clean:
        clean()
    else:
        ensure_data(docs=not args.ocsf_only, ocsf=not args.docs_only)
