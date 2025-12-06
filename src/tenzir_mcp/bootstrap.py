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
import zipfile
from collections import defaultdict
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
DOCS_CONTENT_DIR = DOCS_DIR / "src" / "content" / "docs"
INDEX_PATH = DATA_DIR / "doc_index.json"
DB_PATH = DATA_DIR / "docs.db"
OCSF_DIR = DATA_DIR / "ocsf"

# GitHub configuration for docs
DOCS_REPO = "https://api.github.com/repos/tenzir/docs"
DOWNLOAD_URL_TEMPLATE = "https://github.com/tenzir/docs/archive/{}.zip"

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
    """Download documentation from GitHub."""
    try:
        import requests
    except ImportError:
        logger.error("requests library not available - install with: uv add requests")
        sys.exit(1)

    logger.info("downloading documentation from tenzir/docs")

    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    # Get latest commit SHA
    try:
        response = requests.get(
            f"{DOCS_REPO}/commits/main", headers=headers, timeout=TIMEOUT
        )
        response.raise_for_status()
        commit_sha = response.json()["sha"]
        logger.info("latest commit: %s", commit_sha[:8])
    except requests.RequestException as e:
        logger.error("failed to fetch commit info: %s", e)
        sys.exit(1)

    # Download archive
    download_url = DOWNLOAD_URL_TEMPLATE.format(commit_sha)
    try:
        response = requests.get(download_url, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error("failed to download docs: %s", e)
        sys.exit(1)

    # Extract documentation files
    doc_extensions = {".md", ".mdx", ".mdoc"}

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_file = temp_path / "docs.zip"

        with zip_file.open("wb") as f:
            f.write(response.content)

        with zipfile.ZipFile(zip_file, "r") as zf:
            zf.extractall(temp_path)

        extracted_dirs = [
            d for d in temp_path.iterdir() if d.is_dir() and d.name.startswith("docs-")
        ]
        if not extracted_dirs:
            logger.error("could not find extracted docs directory")
            sys.exit(1)

        extracted_dir = extracted_dirs[0]
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        files_copied = 0

        for file_path in extracted_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in doc_extensions:
                rel_path = file_path.relative_to(extracted_dir)
                dest_path = DOCS_DIR / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                files_copied += 1

    # Create metadata file
    metadata = {
        "commit_sha": commit_sha,
        "repository": "https://github.com/tenzir/docs",
        "download_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metadata_file = DOCS_DIR / ".metadata.json"
    with metadata_file.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("downloaded %d documentation files", files_copied)


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
    """Build the documentation index from downloaded docs."""
    import re

    logger.info("building documentation index")

    if not DOCS_CONTENT_DIR.exists():
        logger.error("documentation content not found at %s", DOCS_CONTENT_DIR)
        sys.exit(1)

    see_also_pattern = re.compile(r"^##\s+See\s+Also\s*$", re.IGNORECASE | re.MULTILINE)
    markdown_link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    def extract_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
        lines = markdown.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}, markdown

        frontmatter_lines: list[str] = []
        closing_index = None
        for idx, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                closing_index = idx
                break
            frontmatter_lines.append(line)

        if closing_index is None:
            return {}, markdown

        frontmatter: dict[str, str] = {}
        buffer: list[str] = []
        key: str | None = None

        def flush_buffer() -> None:
            nonlocal key, buffer
            if key is None:
                buffer = []
                return
            value = "\n".join(buffer).strip()
            if value.startswith(("'", '"')) and value.endswith(("'", '"')):
                value = value[1:-1]
            frontmatter[key] = value
            key = None
            buffer = []

        for line in frontmatter_lines:
            if not line.strip():
                continue
            if ":" in line and not line.startswith((" ", "\t")):
                flush_buffer()
                key_part, value_part = line.split(":", 1)
                key = key_part.strip()
                value = value_part.strip()
                if value:
                    buffer = [value]
                    flush_buffer()
                else:
                    buffer = []
            else:
                buffer.append(line)

        flush_buffer()
        body = "\n".join(lines[closing_index + 1 :])
        return frontmatter, body

    def resolve_link_target(target: str, current_file: Path) -> Path | None:
        target = target.strip()
        if not target or target.startswith("#"):
            return None
        if re.match(r"^[a-z]+://", target):
            return None

        normalized = target.lstrip("/")
        raw_path = Path(normalized)
        candidate = (
            (DOCS_CONTENT_DIR / raw_path)
            if target.startswith("/")
            else (current_file.parent / raw_path)
        )

        def candidate_with_suffix(path: Path) -> Path | None:
            if path.exists() and path.is_file():
                return path
            if path.exists() and path.is_dir():
                for index_name in ("index.md", "index.mdx", "index.mdoc"):
                    index_path = path / index_name
                    if index_path.exists():
                        return index_path
                return None
            for extension in (".md", ".mdx", ".mdoc"):
                with_suffix = path.with_suffix(extension)
                if with_suffix.exists():
                    return with_suffix
            return None

        resolved = candidate_with_suffix(candidate.resolve(strict=False))
        if resolved is None:
            return None

        try:
            resolved.relative_to(DOCS_CONTENT_DIR)
        except ValueError:
            return None

        return resolved

    def normalize_doc_path(resolved: Path) -> str:
        relative = resolved.relative_to(DOCS_CONTENT_DIR)
        if relative.name.startswith("index."):
            relative = relative.parent
        else:
            relative = relative.with_suffix("")
        if not relative.parts:
            return "index"
        return "/".join(relative.parts)

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

    def extract_cross_links(
        markdown_body: str, current_file: Path
    ) -> tuple[list[dict[str, str]], list[str]]:
        match = see_also_pattern.search(markdown_body)
        if not match:
            return [], []

        start = match.end()
        subsequent_heading = re.search(r"^##\s+", markdown_body[start:], re.MULTILINE)
        end = (
            start + subsequent_heading.start()
            if subsequent_heading
            else len(markdown_body)
        )
        section = markdown_body[start:end]

        links: list[dict[str, str]] = []
        missing: list[str] = []

        for link_text, target in markdown_link_pattern.findall(section):
            resolved = resolve_link_target(target, current_file)
            if resolved is None:
                missing.append(target.strip())
                continue
            normalized_path = normalize_doc_path(resolved)
            links.append(
                {
                    "title": link_text.strip(),
                    "path": normalized_path,
                    "type": classify_doc(normalized_path),
                }
            )

        return links, missing

    def doc_entry(
        normalized_path: str,
        doc_type: str,
        frontmatter: dict[str, str],
        see_also: Iterable[dict[str, str]],
    ) -> dict[str, Any]:
        return {
            "path": normalized_path,
            "title": frontmatter.get("title", normalized_path.split("/")[-1]),
            "category": frontmatter.get("category", "Uncategorized"),
            "example": frontmatter.get("example", ""),
            "type": doc_type,
            "see_also": list(see_also),
        }

    missing_links: dict[str, list[str]] = defaultdict(list)
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

    for source_path in sorted(DOCS_CONTENT_DIR.rglob("*.md*")):
        if source_path.name.startswith("_"):
            continue
        normalized = normalize_doc_path(source_path)
        if "changelog" in source_path.relative_to(DOCS_CONTENT_DIR).parts:
            continue
        if normalized in index["documents"]:
            continue
        markdown = source_path.read_text(encoding="utf-8")
        frontmatter, body = extract_frontmatter(markdown)
        see_also, unresolved = extract_cross_links(body, source_path)
        for unresolved_target in unresolved:
            key = str(source_path.relative_to(DOCS_CONTENT_DIR))
            missing_links[key].append(unresolved_target)
        cross_link_total += len(see_also)

        doc_type = classify_doc(normalized)
        entry = doc_entry(normalized, doc_type, frontmatter, see_also)
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

    if missing_links:
        failures = [
            f"{source} -> {', '.join(sorted(targets))}"
            for source, targets in sorted(missing_links.items())
        ]
        raise RuntimeError("Failed to resolve See Also links:\n" + "\n".join(failures))

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
