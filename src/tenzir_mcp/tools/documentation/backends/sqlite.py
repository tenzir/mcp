"""SQLite FTS5-based documentation search backend."""

import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from tenzir_mcp.tools.documentation.backends.base import SearchBackend


class SQLiteSearchBackend(SearchBackend):
    """FTS5-powered search backend with BM25 ranking."""

    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None
        self._db_path = self._get_db_path()

    def _get_db_path(self) -> Path:
        """Get path to the SQLite database."""
        # Try development path first
        try:
            import tenzir_mcp

            pkg_root = Path(tenzir_mcp.__file__).parent
            db_path = pkg_root / "data" / "docs.db"
            if db_path.exists():
                return db_path
        except Exception:
            pass

        # Try package resources
        try:
            data_pkg = files("tenzir_mcp.data")
            if hasattr(data_pkg, "_path"):
                # _path is not part of the public API but works for editable installs
                db_path = Path(data_pkg._path) / "docs.db"
                if db_path.exists():
                    return db_path
        except Exception:
            pass

        raise FileNotFoundError(
            "Documentation database not found. Run 'make build-doc-db' to create it."
        )

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection (lazy initialization)."""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def search(
        self,
        query: str,
        doc_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search using SQLite FTS5 with BM25 ranking."""
        query_stripped = query.strip()
        if not query_stripped:
            return []

        # Build FTS5 query - tokenize and combine with OR for better recall
        # FTS5 will handle stemming (porter) automatically
        tokens = query_stripped.split()
        if len(tokens) > 1:
            # Multi-word: use OR to find documents matching any term
            # BM25 will rank documents with more matches higher
            fts_query = " OR ".join(tokens)
        else:
            # Single word: use as-is
            fts_query = query_stripped

        # Build type filter
        type_filter = ""
        if doc_types is not None and len(doc_types) > 0:
            placeholders = ",".join("?" * len(doc_types))
            type_filter = f"AND type IN ({placeholders})"

        # Query FTS5 table with BM25 ranking
        sql = f"""
            SELECT
                path,
                title,
                name,
                category,
                example,
                type,
                bm25(docs_fts) as score
            FROM docs_fts
            WHERE docs_fts MATCH ?
            {type_filter}
            ORDER BY score
            LIMIT ?
        """

        params: list[Any] = [fts_query]
        if doc_types:
            params.extend(doc_types)
        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(sql, params)

        results: list[dict[str, Any]] = []
        for row in cursor.fetchall():
            # Get see_also links
            see_also = self._get_see_also(row["path"])

            results.append(
                {
                    "path": row["path"],
                    "title": row["title"] or row["name"] or row["path"],
                    "type": row["type"],
                    "name": row["name"] or "",
                    "category": row["category"] or "",
                    "example": row["example"] or "",
                    "see_also": see_also,
                }
            )

        return results

    def lookup(self, path: str) -> dict[str, Any] | None:
        """Look up a document by normalized path."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT path, title, name, category, example, type
            FROM docs_fts
            WHERE path = ?
            LIMIT 1
            """,
            (path,),
        )

        row = cursor.fetchone()
        if row is None:
            return None

        see_also = self._get_see_also(row["path"])

        return {
            "path": row["path"],
            "title": row["title"] or row["name"] or row["path"],
            "type": row["type"],
            "name": row["name"] or "",
            "category": row["category"] or "",
            "example": row["example"] or "",
            "see_also": see_also,
        }

    def get_all_docs(self) -> dict[str, Any]:
        """Get the complete index (cached for depth traversal)."""
        return self._build_complete_index()

    @lru_cache(maxsize=1)  # noqa: B019
    def _build_complete_index(self) -> dict[str, Any]:
        """Build a complete index structure from the database."""
        cursor = self.conn.cursor()

        # Get metadata
        cursor.execute("SELECT key, value FROM metadata")
        metadata = {row["key"]: row["value"] for row in cursor.fetchall()}

        # Get all documents organized by type
        index: dict[str, Any] = {
            "operators": {},
            "functions": {},
            "tutorials": {},
            "documents": {},
            "metadata": metadata,
        }

        cursor.execute(
            """
            SELECT path, title, name, category, example, type
            FROM docs_fts
            """
        )

        for row in cursor.fetchall():
            see_also = self._get_see_also(row["path"])

            doc_entry = {
                "path": row["path"],
                "title": row["title"] or row["name"] or row["path"],
                "type": row["type"],
                "category": row["category"] or "",
                "example": row["example"] or "",
                "see_also": see_also,
            }

            # Add to appropriate section
            if row["type"] == "operator":
                doc_entry["name"] = row["name"] or ""
                index["operators"][row["path"]] = doc_entry
            elif row["type"] == "function":
                doc_entry["name"] = row["name"] or ""
                index["functions"][row["path"]] = doc_entry
            elif row["type"] == "tutorial":
                index["tutorials"][row["path"]] = doc_entry
            else:
                doc_entry["name"] = row["name"] or ""
                index["documents"][row["path"]] = doc_entry

        return index

    def _get_see_also(self, doc_path: str) -> list[dict[str, str]]:
        """Get see_also links for a document."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT see_also_path, see_also_title, see_also_type
            FROM see_also
            WHERE doc_path = ?
            """,
            (doc_path,),
        )

        return [
            {
                "path": row["see_also_path"],
                "title": row["see_also_title"],
                "type": row["see_also_type"],
            }
            for row in cursor.fetchall()
        ]

    def __del__(self) -> None:
        """Close database connection on cleanup."""
        conn = getattr(self, "_conn", None)
        if conn is not None:
            conn.close()
