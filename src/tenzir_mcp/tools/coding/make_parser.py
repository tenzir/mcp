"""Log parser TQL code generator."""

from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool(
    name="make_parser",
    tags={"coding"},
    annotations={
        "title": "Generate a TQL parser",
        "readOnlyHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def make_parser(
    sample: Annotated[
        str, Field(description="Sample log events to generate parser from")
    ],
    ctx: Any = None,
) -> ToolResult:
    """Generate a TQL parser for the given log format.

    Use this tool when:
    - You have sample log events and need to parse them into structured data
    - You're starting a new parser for JSON, CSV, syslog, or key-value logs
    - You want guidance on format detection and TQL operator selection
    - You need to infer types and create proper schema transformations

    This tool provides a complete workflow with step-by-step instructions for:
    1. Analyzing log format and structure
    2. Selecting appropriate TQL operators
    3. Generating parsing code with type conversions
    4. Creating a package with the parser
    5. Testing the parser with sample data

    Follow the workflow instructions provided in the response."""
    try:
        # Read the instructions from prompts directory
        prompt_file = Path(__file__).parent.parent.parent / "prompts" / "make_parser.md"
        assert prompt_file.exists(), f"Prompt file must exist: {prompt_file}"
        prompt = prompt_file.read_text()

        content = prompt
        content += "\n\n"
        content += "# Sample Log Events\n\n"
        content += "```\n"
        content += sample
        content += "\n```\n"

        structured_result = {
            "workflow": prompt,
            "sample": sample,
        }

        return ToolResult(content=content, structured_content=structured_result)

    except Exception as e:
        error_msg = f"Failed to generate parser: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
