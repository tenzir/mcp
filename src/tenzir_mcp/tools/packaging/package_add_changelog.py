"""Package changelog management tool."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field
from tenzir_changelog import Changelog  # type: ignore[import-untyped]

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import validate_package_dir

logger = get_logger(__name__)


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
    package_dir: Annotated[str, Field(description="Path to the package directory")],
    type: Annotated[
        str, Field(description="The entry type: breaking, change, bugfix, or feature")
    ],
    description: Annotated[str, Field(description="Description of the change")],
    author: Annotated[
        str | None,
        Field(
            description="GitHub handle to attribute the entry to. Leave unset to use the changelog default.",
            default=None,
        ),
    ],
) -> ToolResult:
    """Add a changelog entry to a package.

    Use this tool to:
    - Document changes to your package
    - Track breaking changes, new features, bug fixes, and general changes
    - Maintain a history of package evolution
    - Communicate updates to package users

    Changelog entries are timestamped and categorized. They help users
    understand what changed between package versions."""
    try:
        # Validate entry type
        valid_types = ("breaking", "change", "bugfix", "feature")
        normalized_type = type.strip().lower()
        if normalized_type not in valid_types:
            allowed = ", ".join(valid_types)
            error_msg = f"Invalid type '{type}'. Must be one of: {allowed}"
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        # Validate package directory
        validate_package_dir(package_dir)
        pkg_path = Path(package_dir)

        entry_body = description.strip()
        if not entry_body:
            error_msg = "Description cannot be empty."
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        entry_title = _derive_entry_title(entry_body)

        changelog_client = Changelog(root=pkg_path)
        entry_file = changelog_client.add(
            title=entry_title,
            entry_type=normalized_type,
            description=entry_body,
            authors=(author,) if author else None,
        )

        result = {
            "entry_file": str(entry_file),
            "type": normalized_type,
            "title": entry_title,
            "description": entry_body,
            "author": author,
            "summary": f"Added {normalized_type} changelog entry",
        }

        content = (
            "# Changelog Entry Added\n\n"
            f"**Type**: `{normalized_type}`\n"
            f"**Title**: {entry_title}\n"
            f"**File**: `{entry_file}`\n"
            f"**Author**: {author or 'Changelog default'}\n"
            f"**Summary**: {result['summary']}\n\n"
            f"## Description\n{entry_body}"
        )
        return ToolResult(content=content, structured_content=result)

    except SystemExit as e:
        error_msg = f"Changelog library failed with SystemExit: {e}"
        logger.error(error_msg, exc_info=True)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
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


def _derive_entry_title(description: str) -> str:
    """Use the first non-empty line as the title, trimmed for brevity."""

    for raw_line in description.splitlines():
        candidate = raw_line.strip()
        if candidate:
            return candidate[:120]
    return "Changelog update"
