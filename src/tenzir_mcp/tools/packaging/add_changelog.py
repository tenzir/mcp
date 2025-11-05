"""Package changelog management tool."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import validate_package_dir

logger = logging.getLogger(__name__)


@mcp.tool(
    name="package_add_changelog",
    tags={"packaging"},
    annotations={
        "title": "Add changelog entry to package",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def package_add_changelog(
    package: Annotated[str, Field(description="Path to the package directory")],
    type: Annotated[
        str, Field(description="The entry type: breaking, change, bugfix, or feature")
    ],
    description: Annotated[str, Field(description="Description of the change")],
) -> ToolResult:
    """Add a changelog entry to a package."""
    try:
        # Validate type
        valid_types = ["breaking", "change", "bugfix", "feature"]
        if type not in valid_types:
            error_msg = (
                f"Invalid type '{type}'. Must be one of: {', '.join(valid_types)}"
            )
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        # Validate package directory
        validate_package_dir(package)
        pkg_path = Path(package)

        # Create changelog directory if needed
        changelog_dir = pkg_path / "changelog"
        changelog_dir.mkdir(exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        entry_file = changelog_dir / f"{type}-{timestamp}.md"

        # Write changelog entry
        entry_file.write_text(description + "\n")

        result = {
            "entry_file": str(entry_file),
            "type": type,
            "summary": f"Added {type} changelog entry",
        }

        content = f"# Changelog Entry Added\n\n**Type**: `{type}`\n**File**: `{entry_file}`\n**Description**: {description}"
        return ToolResult(content=content, structured_content=result)

    except ValueError as e:
        error_msg = str(e)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
    except Exception as e:
        error_msg = f"Failed to add changelog entry: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
