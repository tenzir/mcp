"""FastMCP application instance for the Tenzir MCP server."""

from fastmcp import FastMCP

__all__ = ["mcp"]

mcp = FastMCP(
    name="Tenzir MCP Server",
    instructions=(
        "Workflow guidance, cross-linked documentation discovery, and execution tools "
        "for Tenzir's TQL and OCSF workflows."
    ),
)
