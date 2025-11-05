#!/usr/bin/env python3
"""Build a searchable index of the bundled Tenzir documentation.

The index captures metadata for operators, functions, and tutorials, while also
recording cross-links from `See Also` sections so that MCP tools can enable
deep navigation without re-running global searches.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from logging_utils import get_logger

logger = get_logger("build-doc-index")

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = (
    REPO_ROOT
    / "src"
    / "tenzir_mcp"
    / "data"
    / "docs"
    / "src"
    / "content"
    / "docs"
)
OUTPUT_PATH = REPO_ROOT / "src" / "tenzir_mcp" / "data" / "doc_index.json"

SEE_ALSO_PATTERN = re.compile(r"^##\s+See\s+Also\s*$", re.IGNORECASE | re.MULTILINE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def extract_frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    """Return the frontmatter dict and body for a markdown document."""
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
        # Malformed frontmatter; treat entire document as body
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


def _resolve_link_target(
    target: str,
    current_file: Path,
    docs_root: Path,
) -> Path | None:
    """Resolve a markdown link target to an on-disk documentation file."""
    target = target.strip()
    if not target or target.startswith("#"):
        return None
    if re.match(r"^[a-z]+://", target):
        return None

    normalized = target.lstrip("/")
    raw_path = Path(normalized)
    candidate = (
        (docs_root / raw_path)
        if target.startswith("/")
        else (current_file.parent / raw_path)
    )

    # Handle directory links by looking for index files
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
        resolved.relative_to(docs_root)
    except ValueError:
        return None

    return resolved


def _normalize_doc_path(resolved: Path, docs_root: Path) -> str:
    """Convert a resolved path into the normalized index key."""
    relative = resolved.relative_to(docs_root)
    if relative.name.startswith("index."):
        relative = relative.parent
    else:
        relative = relative.with_suffix("")
    if not relative.parts:
        return "index"
    return "/".join(relative.parts)


def _classify_doc(normalized_path: str) -> str:
    """Classify a document based on its path structure."""
    # Top-level categories
    if normalized_path.startswith("tutorials/"):
        return "tutorial"
    if normalized_path.startswith("guides/"):
        return "guide"
    if normalized_path.startswith("explanations/"):
        return "explanation"
    if normalized_path.startswith("integrations/"):
        return "integration"

    # Reference subcategories
    if normalized_path.startswith("reference/operators/"):
        return "operator"
    if normalized_path.startswith("reference/functions/"):
        return "function"
    if normalized_path.startswith("reference/mcp-server/"):
        return "mcp"
    if normalized_path.startswith("reference/node/"):
        return "api"  # Node API
    if normalized_path.startswith("reference/platform/"):
        return "api"  # Platform API
    if normalized_path.startswith("reference/test-framework/"):
        return "test"
    if normalized_path.startswith("reference/changelog-framework/"):
        return "changelog"
    if normalized_path.startswith("reference/"):
        return "reference"  # Other reference docs

    return "doc"


def extract_cross_links(
    markdown_body: str,
    current_file: Path,
    docs_root: Path,
) -> tuple[list[dict[str, str]], list[str]]:
    """Extract See Also cross-links from a markdown document."""
    match = SEE_ALSO_PATTERN.search(markdown_body)
    if not match:
        return [], []

    start = match.end()
    subsequent_heading = re.search(r"^##\s+", markdown_body[start:], re.MULTILINE)
    end = start + subsequent_heading.start() if subsequent_heading else len(markdown_body)
    section = markdown_body[start:end]

    links: list[dict[str, str]] = []
    missing: list[str] = []

    for link_text, target in MARKDOWN_LINK_PATTERN.findall(section):
        resolved = _resolve_link_target(target, current_file, docs_root)
        if resolved is None:
            missing.append(target.strip())
            continue
        normalized_path = _normalize_doc_path(resolved, docs_root)
        links.append(
            {
                "title": link_text.strip(),
                "path": normalized_path,
                "type": _classify_doc(normalized_path),
            }
        )

    return links, missing


def _doc_entry(
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


def build_index() -> dict[str, Any]:
    docs_root = DOCS_ROOT
    if not docs_root.exists():
        raise FileNotFoundError(f"Documentation root not found: {docs_root}")

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

    for source_path in sorted(docs_root.rglob("*.md*")):
        if source_path.name.startswith("_"):
            # Skip partials or hidden helper files
            continue
        normalized = _normalize_doc_path(source_path, docs_root)
        # Skip changelog pages from the index
        if "changelog" in source_path.relative_to(docs_root).parts:
            continue
        if normalized in index["documents"]:
            continue
        markdown = source_path.read_text(encoding="utf-8")
        frontmatter, body = extract_frontmatter(markdown)
        see_also, unresolved = extract_cross_links(body, source_path, docs_root)
        for unresolved_target in unresolved:
            key = str(source_path.relative_to(docs_root))
            missing_links[key].append(unresolved_target)
        cross_link_total += len(see_also)

        doc_type = _classify_doc(normalized)
        entry = _doc_entry(normalized, doc_type, frontmatter, see_also)
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
            # Only capture top-level tutorials (e.g., tutorials/foo)
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
        raise RuntimeError(
            "Failed to resolve See Also links:\n" + "\n".join(failures)
        )

    # Sort nested dictionaries for stable output
    index["operators"] = dict(sorted(index["operators"].items()))
    index["functions"] = dict(sorted(index["functions"].items()))
    index["tutorials"] = dict(sorted(index["tutorials"].items()))
    index["documents"] = dict(sorted(index["documents"].items()))

    return index


def main() -> None:
    index = build_index()
    OUTPUT_PATH.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.success(
        "generated documentation index with %s operators, %s functions, %s tutorials, and %s cross-links",
        index['metadata']['operator_count'],
        index['metadata']['function_count'],
        index['metadata']['tutorial_count'],
        index['metadata']['cross_link_count'],
    )


if __name__ == "__main__":
    main()
