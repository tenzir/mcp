"""OCSF class definition tool for getting specific event class details."""

import json
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp

from ._helpers import load_ocsf_schema

logger = get_logger(__name__)


@mcp.tool(
    name="ocsf_get_class",
    tags={"ocsf"},
    annotations={
        "title": "Get OCSF event class",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def ocsf_get_class(
    version: Annotated[str, Field(description="OCSF schema version (e.g., '1.6.0')")],
    name: Annotated[
        str, Field(description="OCSF class name (e.g., 'security_finding')")
    ],
) -> ToolResult:
    """Get the complete definition of a specific OCSF event class including all fields and metadata.

    Use this tool to:
    - Understand the full schema of an OCSF event class before mapping
    - See required vs optional fields
    - Discover nested object structures and their field definitions
    - Validate that your source data can map to the class

    This returns the complete class definition including all attributes, types,
    and constraints needed to create accurate OCSF mappings."""
    try:
        schema = load_ocsf_schema(version)

        # Look for the class in the schema
        if "classes" not in schema:
            error_msg = f"No classes found in OCSF schema version {version}"
            return ToolResult(
                content=error_msg, structured_content={"error": error_msg}
            )

        # Search for class by name (case-insensitive)
        for class_id, class_data in schema["classes"].items():
            class_name = class_data.get("name", class_id)
            if class_name.lower() == name.lower() or class_id.lower() == name.lower():
                # Format as markdown
                description = class_data.get("description", "No description")
                schema_json = json.dumps(class_data, indent=2, sort_keys=True)
                markdown = (
                    f"# {class_name}\n\n"
                    f"**ID**: {class_id}\n\n"
                    f"**Description**: {description}\n\n"
                    "## Schema\n"
                    f"```json\n{schema_json}\n```"
                )

                result = {"id": class_id, "name": class_name, "data": class_data}
                return ToolResult(
                    content=markdown,  # Markdown summary
                    structured_content=result,  # Full JSON data
                )

        error_msg = f"Class '{name}' not found in OCSF schema version {version}"
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
        error_msg = f"Failed to get OCSF class {name} for version {version}: {e}"
        logger.error(error_msg)
        return ToolResult(content=error_msg, structured_content={"error": error_msg})
