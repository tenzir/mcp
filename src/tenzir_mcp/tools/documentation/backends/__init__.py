"""Documentation search backends."""

from tenzir_mcp.tools.documentation.backends.base import SearchBackend
from tenzir_mcp.tools.documentation.backends.json import JSONSearchBackend
from tenzir_mcp.tools.documentation.backends.sqlite import SQLiteSearchBackend

__all__ = ["SearchBackend", "JSONSearchBackend", "SQLiteSearchBackend"]
