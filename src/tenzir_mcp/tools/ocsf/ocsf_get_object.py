"""OCSF object definition tool for getting specific object type details."""

import json
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp

from ._helpers import load_ocsf_schema

logger = get_logger(__name__)


@mcp.tool(
    name="ocsf_get_object",
    tags={"ocsf"},
    annotations={
        "title": "Get OCSF object",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ocsf_get_object(
    version: Annotated[str, Field(description="OCSF schema version (e.g., '1.3.0')")],
    name: Annotated[
        str, Field(description="OCSF object name (e.g., 'email', 'file', 'process')")
    ],
) -> ToolResult:
    """Get the complete definition of an OCSF object type including all fields and metadata.

    Use this tool to:
    - Understand complex nested object structures in OCSF classes
    - See the fields and types within objects like 'file', 'process', 'user'
    - Map source data to nested OCSF structures correctly
    - Reference when constructing TQL operators for OCSF mapping

    Objects are reusable components within OCSF event classes, defining
    standard structures like endpoints, files, processes, etc."""
    try:
        schema = load_ocsf_schema(version)

        # Look for the object in the schema
        if "objects" not in schema:
            error_msg = f"No objects found in OCSF schema version {version}"
            return ToolResult(
                content=error_msg, structured_content={"error": error_msg}
            )

        # Search for object by name (case-insensitive)
        for object_id, object_data in schema["objects"].items():
            object_name = object_data.get("name", object_id)
            if object_name.lower() == name.lower() or object_id.lower() == name.lower():
                # Format as markdown
                description = object_data.get("description", "No description")
                schema_json = json.dumps(object_data, indent=2, sort_keys=True)
                markdown = (
                    f"# {object_name}\n\n"
                    f"**ID**: {object_id}\n\n"
                    f"**Description**: {description}\n\n"
                    "## Schema\n"
                    f"```json\n{schema_json}\n```"
                )

                result = {"id": object_id, "name": object_name, "data": object_data}
                return ToolResult(
                    content=markdown,  # Markdown summary
                    structured_content=result,  # Full JSON data
                )

        error_msg = f"Object '{name}' not found in OCSF schema version {version}"
        return ToolResult(content=error_msg, structured_content={"error": error_msg})

    except FileNotFoundError:
        error_msg = f"OCSF schema version {version} not found"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse OCSF schema for version {version}: {e}"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
    except Exception as e:
        error_msg = f"Failed to get OCSF object {name} for version {version}: {e}"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
