"""Abstract base class for documentation search backends."""

from abc import ABC, abstractmethod
from typing import Any


class SearchBackend(ABC):
    """Abstract interface for documentation search backends."""

    @abstractmethod
    def search(
        self,
        query: str,
        doc_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for documents matching the query.

        Args:
            query: Search query string
            doc_types: List of document types to filter by (operator, function, tutorial, etc.)
                      None means search all types
            limit: Maximum number of results to return

        Returns:
            List of document dictionaries with keys: path, title, type, category, example, see_also
            Results should be sorted by relevance (best matches first)
        """
        pass

    @abstractmethod
    def lookup(self, path: str) -> dict[str, Any] | None:
        """
        Look up a specific document by its normalized path.

        Args:
            path: Normalized document path (e.g., "reference/operators/select")

        Returns:
            Document dictionary or None if not found
        """
        pass

    @abstractmethod
    def get_all_docs(self) -> dict[str, Any]:
        """
        Get the complete document index.

        Returns:
            Full index structure with operators, functions, tutorials, documents sections
        """
        pass
