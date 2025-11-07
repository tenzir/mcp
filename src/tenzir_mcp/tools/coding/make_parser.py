"""Log parser TQL code generator."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    name="make_parser",
    tags={"coding"},
    annotations={
        "title": "Generate a TQL parser",
        "readOnlyHint": False,
        "idempotentHint": False,
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

    Use this tool when you need to parse structured or semi-structured logs into
    a well-typed schema. Provide sample log events, and this tool will guide you
    through creating a complete parser package with tests. Ideal for building
    parsers for logs (e.g., firewall logs, application logs, security events).
    """
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
