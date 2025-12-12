"""OCSF mapping code generator."""

from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool(
    name="make_ocsf_mapping",
    tags={"coding"},
    annotations={
        "title": "Add OCSF mapping to parser",
        "readOnlyHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def make_ocsf_mapping(
    sample: Annotated[
        str, Field(description="Sample log events to generate OCSF mapping from")
    ],
    ctx: Any = None,
) -> ToolResult:
    """Add OCSF mapping to a TQL parsing pipeline.

    Use this tool when:
    - You need to map security logs to the OCSF standard
    - You're normalizing data from multiple sources into a common schema
    - You want to make your data compatible with OCSF-aware tools
    - You need guidance on OCSF class selection and field mapping

    Follow the workflow instructions provided in the response."""
    try:
        # Read the instructions from prompts directory
        prompt_file = (
            Path(__file__).parent.parent.parent / "prompts" / "make_ocsf_mapping.md"
        )
        assert prompt_file.exists(), f"Prompt file must exist: {prompt_file}"
        prompt = prompt_file.read_text()

        content = prompt
        content += "\n\n"
        content += "# Sample Data\n\n"
        content += "```\n"
        content += sample
        content += "\n```\n"

        structured_content = {
            "workflow": prompt,
            "sample": sample,
        }

        return ToolResult(content=content, structured_content=structured_content)

    except Exception as e:
        error_msg = f"Failed to generate OCSF mapping: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
