"""Tenzir MCP Server - Main entry point."""

from importlib import import_module

from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger

from tenzir_mcp import __version__
from tenzir_mcp.bootstrap import ensure_data
from tenzir_mcp.prompts import load_system_prompt

logger = get_logger(__name__)

# Ensure documentation data exists before starting (lazy initialization).
ensure_data()

# Shared FastMCP application for all tool registrations.
mcp = FastMCP(
    name="Tenzir MCP Server",
    version=__version__,
    instructions=load_system_prompt(),
)

logger.debug("Initializing Tenzir MCP Server v%s", __version__)

# Import tool packages so FastMCP registers their tools on startup.
_TOOL_PACKAGES = (
    "tenzir_mcp.tools.coding",
    "tenzir_mcp.tools.documentation",
    "tenzir_mcp.tools.execution",
    "tenzir_mcp.tools.ocsf",
    "tenzir_mcp.tools.packaging",
)

for _module_name in _TOOL_PACKAGES:
    import_module(_module_name)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
