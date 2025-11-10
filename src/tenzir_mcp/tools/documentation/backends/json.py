"""JSON-based documentation search backend."""

from typing import Any

from tenzir_mcp.docs import load_doc_index, lookup_doc
from tenzir_mcp.tools.documentation.backends.base import SearchBackend


class JSONSearchBackend(SearchBackend):
    """Simple substring-based search using the JSON index."""

    def __init__(self) -> None:
        self._index = load_doc_index()

    def search(
        self,
        query: str,
        doc_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search using simple substring matching."""
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        results: list[dict[str, Any]] = []
        seen_paths: set[str] = set()

        # Determine which sections to search based on doc_types
        # The index has: operators, functions, tutorials, documents
        # doc_types contains: operator, function, tutorial, guide, explanation, integration, api, etc.
        search_all = doc_types is None
        search_sections: list[tuple[str, str]] = []

        if search_all or (doc_types and "operator" in doc_types):
            search_sections.append(("operators", "operator"))
        if search_all or (doc_types and "function" in doc_types):
            search_sections.append(("functions", "function"))
        if search_all or (doc_types and "tutorial" in doc_types):
            search_sections.append(("tutorials", "tutorial"))

        # All other types are in the documents section
        if search_all or (
            doc_types
            and any(
                t in doc_types
                for t in [
                    "guide",
                    "explanation",
                    "integration",
                    "api",
                    "mcp",
                    "test",
                    "changelog",
                    "reference",
                    "doc",
                ]
            )
        ):
            search_sections.append(("documents", "doc"))

        # Search each section
        for section_name, fallback_type in search_sections:
            section = self._index.get(section_name, {})
            for entry in section.values():
                result = self._format_search_result(entry, fallback_type, query_lower)
                if result is None:
                    continue

                path = result.get("path")
                if path and path not in seen_paths:
                    seen_paths.add(path)
                    results.append(result)

        # Sort by score (lower is better) and path
        results.sort(key=lambda item: (item.pop("_score", 4), item.get("path", "")))

        return results[:limit]

    def lookup(self, path: str) -> dict[str, Any] | None:
        """Look up a document by normalized path."""
        return lookup_doc(path, self._index)

    def get_all_docs(self) -> dict[str, Any]:
        """Get the complete index."""
        return self._index

    def _format_search_result(
        self,
        entry: dict[str, Any],
        doc_type: str,
        query_lower: str,
    ) -> dict[str, Any] | None:
        """Format and score a search result."""
        name = entry.get("name", "")
        title = entry.get("title", "")
        category = entry.get("category", "")
        example = entry.get("example", "")
        path = entry.get("path", "")

        # Check if query matches any searchable field
        searchable_values = [
            value for value in (name, title, category, example, path) if value
        ]
        if not any(query_lower in value.lower() for value in searchable_values):
            return None

        # Score the match (lower is better)
        def score_field(value: str) -> int:
            value_lower = value.lower()
            if value_lower == query_lower:
                return 0  # Exact match
            if value_lower.startswith(query_lower):
                return 1  # Prefix match
            if query_lower in value_lower:
                return 2  # Substring match
            return 4  # No match

        score_candidates = [score_field(value) for value in searchable_values]
        score = min(score_candidates) if score_candidates else 4

        return {
            "path": path,
            "title": title or name or path,
            "type": doc_type,
            "name": name,
            "category": category,
            "example": example,
            "see_also": entry.get("see_also", []),
            "_score": score,
        }
