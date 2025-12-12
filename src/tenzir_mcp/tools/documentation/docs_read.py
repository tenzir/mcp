"""Documentation reading tool."""

from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.docs import TenzirDocs
from tenzir_mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool(
    name="docs_read",
    tags={"documentation"},
    annotations={
        "title": "Read documentation",
        "readOnlyHint": True,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def docs_read(
    path: Annotated[
        str,
        Field(
            description="Documentation path without extension (e.g., 'reference/operators/select', "
            "'reference/functions/abs', 'tutorials/map-data-to-ocsf')"
        ),
    ],
) -> ToolResult:
    """Read documentation content from the embedded Tenzir documentation.

    Use this tool to:
    - Read operator documentation BEFORE using any TQL operator
    - Read function documentation BEFORE using any TQL function
    - Study tutorials and guides for learning workflows
    """
    try:
        clean_path = path.strip("/")

        for ext in [".md", ".mdx", ".mdoc"]:
            if clean_path.endswith(ext):
                clean_path = clean_path[: -len(ext)]
                break

        docs = TenzirDocs()

        possible_paths = [
            f"src/content/docs/{clean_path}.md",
            f"src/content/docs/{clean_path}.mdx",
            f"src/content/docs/{clean_path}.mdoc",
            f"src/content/docs/{clean_path}/index.mdx",
        ]

        for try_path in possible_paths:
            if docs.exists(try_path):
                requested_path = path.strip() or "/"
                normalized_path = clean_path or "index"
                resolved_content = docs.read_file(try_path)
                metadata_header = "\n".join(
                    [
                        f"**Requested Path**: `{requested_path}`",
                        f"**Normalized Path**: `{normalized_path}`",
                        f"**Resolved File**: `{try_path}`",
                    ]
                )
                content = f"{metadata_header}\n\n---\n\n{resolved_content}"
                return ToolResult(
                    content=content,  # Markdown text for display
                    structured_content={
                        "path": normalized_path,
                        "resolved_path": try_path,
                        "content": resolved_content,  # Same content for structured access
                    },
                )

        error_msg = f"Documentation file not found for path '{path}'. Please check the path and try again."
        return ToolResult(
            content=error_msg,
            structured_content={
                "error": error_msg,
                "path": clean_path or path,
            },
        )

    except Exception as e:
        logger.error(f"Failed to get docs markdown for path {path}: {e}")
        error_msg = f"Error retrieving documentation: {e}"
        return ToolResult(
            content=error_msg,
            structured_content={"error": error_msg, "path": path},
        )
