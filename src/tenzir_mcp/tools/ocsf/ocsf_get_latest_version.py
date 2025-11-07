"""OCSF latest version tool for getting the latest stable schema version."""

from fastmcp.tools.tool import ToolResult

from tenzir_mcp.server import mcp

from .ocsf_get_versions import list_ocsf_versions


def latest_stable_ocsf_version() -> str:
    """
    Returns the newest non-development OCSF schema version.
    """
    # Get all available versions
    versions = list_ocsf_versions()

    # Filter out development versions (containing 'dev', 'alpha', 'beta', 'rc')
    stable_versions: list[str] = []
    for version in versions:
        version_lower = version.lower()
        if not any(
            dev_marker in version_lower for dev_marker in ["dev", "alpha", "beta", "rc"]
        ):
            stable_versions.append(version)

    if not stable_versions:
        raise RuntimeError("No stable OCSF versions found")

    # Return the last (newest) stable version
    result: str = stable_versions[-1]
    return result


@mcp.tool(
    name="ocsf_get_latest_version",
    tags={"ocsf"},
    annotations={
        "title": "Get latest OCSF version",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ocsf_get_latest_version() -> ToolResult:
    """Return the latest stable OCSF schema version.

    Use this tool to:
    - Get the current recommended OCSF version for new mappings
    - Ensure you're using up-to-date schema definitions
    - Start OCSF mapping workflows with the latest standard

    This filters out development versions (alpha, beta, rc) and returns
    only stable releases."""
    version = latest_stable_ocsf_version()
    return ToolResult(
        content=f"Latest OCSF version: {version}",  # Human-readable
        structured_content={"version": version},  # JSON
    )
