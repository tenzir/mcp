"""OCSF versions tool for listing available schema versions."""

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore

from fastmcp.tools.tool import ToolResult

from tenzir_mcp.server import mcp


def list_ocsf_versions() -> list[str]:
    """
    Get all available OCSF schema versions.
    """
    # Get the OCSF data directory
    ocsf_files = files("tenzir_mcp.data.ocsf")

    # Extract version numbers from JSON filenames
    versions = []
    for file_path in ocsf_files.iterdir():
        if file_path.name.endswith(".json"):
            # Remove .json extension to get version
            version = file_path.name[:-5]
            versions.append(version)

    # Sort versions (simple string sort works for semantic versions)
    versions.sort()
    return versions


@mcp.tool(
    name="ocsf_get_versions",
    tags={"ocsf"},
    annotations={
        "title": "List OCSF versions",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ocsf_get_versions() -> ToolResult:
    """List all bundled OCSF schema versions.

    Use this tool to:
    - See which OCSF schema versions are available
    - Choose a specific version for your mapping work
    - Understand schema evolution across versions

    Typically you'll want to use `ocsf_get_latest_version` instead to get
    the most recent stable version automatically."""
    versions = list_ocsf_versions()
    return ToolResult(
        content="\n".join([f"- {v}" for v in versions]),  # Markdown list
        structured_content={"versions": versions},  # JSON array
    )
