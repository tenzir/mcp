"""Package test management tool."""

import logging
from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import (
    generate_frontmatter,
    validate_package_dir,
)

logger = logging.getLogger(__name__)


@mcp.tool(
    name="package_add_test",
    tags={"packaging"},
    annotations={
        "title": "Add test to package",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def package_add_test(
    package: Annotated[str, Field(description="Path to the package directory")],
    path: Annotated[
        str,
        Field(description="Path to the test file relative to package tests directory"),
    ],
    input: Annotated[list[str], Field(description="TQL pipeline code or input data")],
    output: Annotated[list[str], Field(description="Expected output lines")],
    fixtures: Annotated[
        list[str] | None,
        Field(default=None, description="List of fixture names (optional)"),
    ],
    timeout: Annotated[
        int | None,
        Field(
            default=None,
            ge=1,
            description="Maximum time in seconds for the test to complete (optional)",
        ),
    ],
) -> ToolResult:
    """Add a test to a package."""
    try:
        # Validate package directory
        validate_package_dir(package)
        pkg_path = Path(package)

        # Create tests directory if needed
        tests_dir = pkg_path / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Build test file path
        test_file = tests_dir / path
        test_file.parent.mkdir(parents=True, exist_ok=True)

        # Build frontmatter metadata
        metadata: dict[str, int | list[str]] = {}
        if fixtures:
            metadata["fixtures"] = fixtures
        if timeout:
            metadata["timeout"] = timeout

        # Generate frontmatter
        frontmatter = generate_frontmatter(metadata)

        # Build test content
        test_content = frontmatter
        if input:
            test_content += "\n".join(input)

        # Write test file
        test_file.write_text(test_content)

        # Create baseline file
        baseline_file = test_file.with_suffix(".txt")
        if output:
            baseline_content = "\n".join(output) + "\n"
            baseline_file.write_text(baseline_content)

        result = {
            "test_path": str(test_file),
            "baseline_path": str(baseline_file) if output else None,
            "summary": f"Added test {path} to package",
        }

        # Format as markdown
        content = f"# Test Added\n\n**Path**: `{test_file}`\n"
        if baseline_file.exists():
            content += f"**Baseline**: `{baseline_file}`\n"

        return ToolResult(content=content, structured_content=result)

    except ValueError as e:
        error_msg = str(e)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
    except Exception as e:
        error_msg = f"Failed to add test: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
