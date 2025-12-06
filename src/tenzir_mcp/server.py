"""Tenzir MCP Server - Main entry point."""

import logging
import os
from importlib import import_module

from fastmcp import FastMCP

from tenzir_mcp.bootstrap import ensure_data
from tenzir_mcp.prompts import load_system_prompt

# Ensure documentation data exists before starting (lazy initialization).
ensure_data()

# Shared FastMCP application for all tool registrations.
mcp = FastMCP(
    name="Tenzir MCP Server",
    instructions=load_system_prompt(),
)

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

# Configure logging for MCP protocol (file-based to avoid stdout interference).
debug_mode = os.getenv("DEBUG") is not None
log_file = os.path.join(os.getcwd(), "tenzir-mcp.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file)],
)

if debug_mode:
    logging.getLogger("tenzir_mcp").setLevel(logging.DEBUG)

logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.INFO)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
