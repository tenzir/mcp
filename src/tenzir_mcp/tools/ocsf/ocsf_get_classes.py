"""OCSF classes tool for listing event classes and their descriptions."""

import json
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp

from ._helpers import load_ocsf_schema

logger = get_logger(__name__)


@mcp.tool(
    name="ocsf_get_classes",
    tags={"ocsf"},
    annotations={
        "title": "List OCSF event classes",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ocsf_get_classes(
    version: Annotated[str, Field(description="OCSF schema version (e.g., '1.6.0')")],
) -> ToolResult:
    """Get all OCSF event classes and their descriptions for a specific schema version.

    Use this tool to:
    - Browse available OCSF event classes before creating a mapping
    - Identify which class best matches your log data
    - Understand the purpose and scope of each event class

    Once you identify a candidate class, use `ocsf_get_class` to see its
    complete schema with all fields and attributes."""
    try:
        schema = load_ocsf_schema(version)

        # Extract event classes from the schema
        event_classes = {}

        if "classes" in schema:
            for class_id, class_data in schema["classes"].items():
                class_name = class_data.get("name", class_id)
                description = class_data.get("description", "No description available")
                event_classes[class_name] = description

        # Format as markdown list
        markdown_lines = [f"## OCSF Event Classes (v{version})\n"]
        for name, desc in sorted(event_classes.items()):
            markdown_lines.append(f"- **{name}**: {desc}")

        return ToolResult(
            content="\n".join(markdown_lines),  # Markdown list
            structured_content={"classes": event_classes, "version": version},  # JSON
        )

    except FileNotFoundError:
        error_msg = f"OCSF schema version {version} not found"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse OCSF schema for version {version}: {e}"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
    except Exception as e:
        error_msg = f"Failed to get OCSF event classes for version {version}: {e}"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
