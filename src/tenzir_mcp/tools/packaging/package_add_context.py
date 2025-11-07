"""Package context management tool."""

import logging
from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import (
    read_package_yaml,
    validate_package_dir,
    write_package_yaml,
)

logger = logging.getLogger(__name__)


@mcp.tool(
    name="package_add_context",
    tags={"packaging"},
    annotations={
        "title": "Add context to package",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def package_add_context(
    package_dir: Annotated[str, Field(description="Path to the package directory")],
    name: Annotated[str, Field(description="Name of the context")],
    description: Annotated[str, Field(description="Description of the context")],
    type: Annotated[
        str, Field(description="The context type (e.g., 'lookup-table', 'geoip')")
    ],
) -> ToolResult:
    """Add a context to a package.

    Use this tool to:
    - Declare lookup tables for enrichment (e.g., threat intel, asset inventory)
    - Define GeoIP contexts for IP address geolocation

    Contexts are defined in package.yaml and pipelines must populate them
    separately."""
    try:
        # Validate package directory
        validate_package_dir(package_dir)
        pkg_path = Path(package_dir)

        # Read current package.yaml
        pkg_data = read_package_yaml(pkg_path)

        # Initialize contexts section if it doesn't exist
        if "contexts" not in pkg_data:
            pkg_data["contexts"] = []

        # Add context entry
        context_entry = {
            "name": name,
            "description": description,
            "type": type,
        }
        pkg_data["contexts"].append(context_entry)

        # Write updated package.yaml
        write_package_yaml(pkg_path, pkg_data)

        result = {
            "context_name": name,
            "type": type,
            "summary": f"Added context '{name}' of type '{type}' to package",
        }

        content = f"# Context Added\n\n**Name**: `{name}`\n**Type**: `{type}`\n**Description**: {description}"
        return ToolResult(content=content, structured_content=result)

    except ValueError as e:
        error_msg = str(e)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
    except Exception as e:
        error_msg = f"Failed to add context: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
