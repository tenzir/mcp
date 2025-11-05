"""Access to bundled Tenzir documentation and search helpers."""

import json
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from importlib.resources import files
except ImportError:
    # Python < 3.9 compatibility
    from importlib_resources import files  # type: ignore


__all__ = [
    "DocsMetadata",
    "TenzirDocs",
    "docs",
    "get_docs",
    "read_doc_file",
    "list_doc_files",
    "get_docs_metadata",
    "load_doc_index",
    "normalize_doc_request",
    "lookup_doc",
    "infer_doc_type",
    "filter_by_category",
    "format_search_result",
    "build_related_tree",
]


class DocsMetadata:
    """Metadata about the bundled documentation."""

    def __init__(self, metadata: dict[str, str]) -> None:
        self.commit_sha = metadata.get("commit_sha", "unknown")
        self.repository = metadata.get("repository", "https://github.com/tenzir/docs")
        self.download_timestamp = metadata.get("download_timestamp", "unknown")

    def __repr__(self) -> str:
        return f"DocsMetadata(commit_sha='{self.commit_sha[:8]}...', timestamp='{self.download_timestamp}')"


class TenzirDocs:
    """Access to bundled Tenzir documentation."""

    def __init__(self) -> None:
        self._docs_root: Path | None = None
        self._metadata: DocsMetadata | None = None

    @property
    def docs_root(self) -> Path:
        """Get the root directory of the bundled docs."""
        if self._docs_root is None:
            # First try fallback for development
            import tenzir_mcp

            pkg_root = Path(tenzir_mcp.__file__).parent
            potential_docs_path = pkg_root / "data" / "docs"

            if potential_docs_path.exists():
                self._docs_root = potential_docs_path
            else:
                try:
                    # Try to find docs in package data
                    docs_pkg = files("tenzir_mcp.data.docs")
                    if hasattr(docs_pkg, "_path"):
                        # For editable installs or direct path access
                        self._docs_root = docs_pkg._path
                    else:
                        # For wheel installs, we need to extract to a temp location
                        # This is a simplified approach - in practice you might want
                        # to cache this in a temp directory
                        raise NotImplementedError(
                            "Wheel-based docs access not yet implemented"
                        )
                except (ModuleNotFoundError, FileNotFoundError):
                    raise FileNotFoundError(
                        f"Documentation not found at {potential_docs_path}. "
                        "Run 'make update-docs' or rebuild the package."
                    ) from None

            if not self._docs_root.exists():
                raise FileNotFoundError(
                    f"Documentation not found at {self._docs_root}. "
                    "Run 'make update-docs' or rebuild the package."
                )

        return self._docs_root

    @property
    def metadata(self) -> DocsMetadata:
        """Get metadata about the bundled documentation."""
        if self._metadata is None:
            metadata_file = self.docs_root / ".metadata.json"
            if metadata_file.exists():
                with metadata_file.open("r", encoding="utf-8") as f:
                    metadata_dict = json.load(f)
                self._metadata = DocsMetadata(metadata_dict)
            else:
                # Default metadata if file doesn't exist
                self._metadata = DocsMetadata({})

        return self._metadata

    def list_files(self, pattern: str = "**/*") -> list[Path]:
        """List all files in the docs matching the given pattern."""
        docs_root = self.docs_root
        return [p for p in docs_root.glob(pattern) if p.is_file()]

    def read_file(self, relative_path: str | Path) -> str:
        """Read a documentation file by its relative path."""
        file_path = self.docs_root / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {relative_path}")

        with file_path.open("r", encoding="utf-8") as f:
            return f.read()

    def find_files(self, name_pattern: str) -> list[Path]:
        """Find files by name pattern (e.g., '*.md', 'index.*')."""
        return [p for p in self.docs_root.rglob(name_pattern) if p.is_file()]

    def get_file_path(self, relative_path: str | Path) -> Path:
        """Get the absolute path to a documentation file."""
        file_path = self.docs_root / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {relative_path}")
        return file_path

    def exists(self, relative_path: str | Path) -> bool:
        """Check if a documentation file exists."""
        return (self.docs_root / relative_path).exists()


# Global instance for easy access
docs = TenzirDocs()


def get_docs() -> TenzirDocs:
    """Get the global TenzirDocs instance."""
    return docs


def read_doc_file(relative_path: str | Path) -> str:
    """Convenience function to read a documentation file."""
    return docs.read_file(relative_path)


def list_doc_files(pattern: str = "**/*") -> list[Path]:
    """Convenience function to list documentation files."""
    return docs.list_files(pattern)


def get_docs_metadata() -> DocsMetadata:
    """Convenience function to get documentation metadata."""
    return docs.metadata


_DOC_INDEX_EXTENSIONS = (".md", ".mdx", ".mdoc")


@lru_cache(maxsize=1)
def load_doc_index() -> dict[str, Any]:
    """Load the pre-computed documentation index."""
    content = files("tenzir_mcp.data").joinpath("doc_index.json").read_text()
    index: dict[str, Any] = json.loads(content)
    return index


def normalize_doc_request(path: str) -> str:
    """Normalize a docs path by trimming slashes, extensions, and index suffix."""
    cleaned = path.strip().strip("/")
    for ext in _DOC_INDEX_EXTENSIONS:
        if cleaned.endswith(ext):
            cleaned = cleaned[: -len(ext)]
            break
    if cleaned.endswith("/index"):
        cleaned = cleaned[: -len("/index")]
    return cleaned or "index"


def lookup_doc(path: str, index: dict[str, Any]) -> dict[str, Any] | None:
    """Look up a document entry in the loaded index using a normalized path."""
    normalized = normalize_doc_request(path)
    documents = index.get("documents", {})
    doc = documents.get(normalized)
    if doc:
        return dict(doc)

    for section in ("operators", "functions"):
        section_docs = index.get(section, {})
        if normalized in section_docs:
            return dict(section_docs[normalized])

    return None


def infer_doc_type(path: str) -> str:
    """Infer a document type from its normalized path."""
    # Top-level categories
    if path.startswith("tutorials/"):
        return "tutorial"
    if path.startswith("guides/"):
        return "guide"
    if path.startswith("explanations/"):
        return "explanation"
    if path.startswith("integrations/"):
        return "integration"

    # Reference subcategories
    if path.startswith("reference/operators/"):
        return "operator"
    if path.startswith("reference/functions/"):
        return "function"
    if path.startswith("reference/mcp-server/"):
        return "mcp"
    if path.startswith("reference/node/"):
        return "api"
    if path.startswith("reference/platform/"):
        return "api"
    if path.startswith("reference/test-framework/"):
        return "test"
    if path.startswith("reference/changelog-framework/"):
        return "changelog"
    if path.startswith("reference/"):
        return "reference"

    return "doc"


def filter_by_category(
    entries: Iterable[dict[str, Any]],
    category: str | None,
) -> list[dict[str, Any]]:
    """Filter index entries by category, preserving list semantics."""
    if category is None:
        return list(entries)
    category_lower = category.lower()
    return [
        entry
        for entry in entries
        if entry.get("category", "").lower() == category_lower
    ]


def format_search_result(
    entry: dict[str, Any],
    doc_type: str,
    query: str,
) -> dict[str, Any] | None:
    """Create a formatted search result with scoring metadata."""
    query_lower = query.lower()
    name = entry.get("name", "")
    title = entry.get("title", "")
    category = entry.get("category", "")
    example = entry.get("example", "")
    path = entry.get("path", "")

    def _score_field(value: str) -> int:
        value_lower = value.lower()
        if value_lower == query_lower:
            return 0
        if value_lower.startswith(query_lower):
            return 1
        if query_lower in value_lower:
            return 2
        return 4

    searchable_values = [
        value for value in (name, title, category, example, path) if value
    ]
    if not any(query_lower in value.lower() for value in searchable_values):
        return None

    score_candidates = [_score_field(value) for value in searchable_values]
    score = min(score_candidates) if score_candidates else 4

    result = {
        "path": entry.get("path"),
        "title": title or name or entry.get("path"),
        "type": doc_type,
        "name": name,
        "category": category,
        "example": example,
        "see_also": entry.get("see_also", []),
        "_score": score,
    }
    return result


def build_related_tree(
    path: str,
    index: dict[str, Any],
    depth: int,
    visited: set[str],
) -> dict[str, Any] | None:
    """Recursively expand See Also relationships for a normalized path."""
    doc = lookup_doc(path, index)
    if not doc:
        return None

    node = {
        key: doc.get(key)
        for key in ("path", "title", "type", "category", "example", "name")
        if doc.get(key) is not None
    }
    node.setdefault("path", normalize_doc_request(path))
    node.setdefault("type", infer_doc_type(node["path"] or "doc"))
    node["see_also"] = doc.get("see_also", [])

    if depth <= 0:
        return node

    related_nodes: list[dict[str, Any]] = []
    for link in doc.get("see_also", []):
        target_path = link.get("path")
        if not target_path or target_path in visited:
            continue
        visited.add(target_path)
        child = build_related_tree(target_path, index, depth - 1, visited)
        if child:
            related_nodes.append(child)
    if related_nodes:
        node["related"] = related_nodes
    return node
