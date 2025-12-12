"""Tenzir test execution tool using tenzir-test framework."""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field
from tenzir_test import execute

from tenzir_mcp.server import mcp

logger = get_logger(__name__)


@mcp.tool(
    name="run_test",
    tags={"execution"},
    annotations={
        "title": "Run Tenzir tests",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def run_test(
    root: Annotated[str, Field(description="Root directory containing the test files")],
    selection: Annotated[
        list[str],
        Field(
            description="List of test files or directories to run (empty list runs all tests)"
        ),
    ],
    passthrough: Annotated[
        bool,
        Field(
            default=False,
            description="Show actual vs expected output for debugging",
        ),
    ],
    update: Annotated[
        bool,
        Field(
            default=False,
            description="Update test baselines with new outputs (use with caution)",
        ),
    ],
    ctx: Any = None,
) -> ToolResult:
    """Run tests for TQL pipelines using the tenzir-test framework.

    Use this tool to:
    - Verify package operators work correctly
    - Run regression tests after making changes
    - Generate test baselines (with update=True)
    - Debug failing tests (with passthrough=True)

    Tests can include fixtures like embedded Tenzir nodes for integration testing.
    The `selection` parameter accepts files, directories, or an empty list for all tests.
    """
    test_paths = [Path(p) for p in selection]
    root_path = Path(root)

    if not root_path.exists():
        raise FileNotFoundError(f"Test root directory not found: {root}")

    logger.debug(f"Running tests: {test_paths} with root: {root_path}")

    # Use TextIOWrapper around BytesIO to provide .buffer attribute
    stdout_buffer = io.BytesIO()
    stderr_buffer = io.BytesIO()
    stdout_capture = io.TextIOWrapper(
        stdout_buffer, encoding="utf-8", line_buffering=True
    )
    stderr_capture = io.TextIOWrapper(
        stderr_buffer, encoding="utf-8", line_buffering=True
    )

    logger.debug(f"stdout_capture has buffer: {hasattr(stdout_capture, 'buffer')}")
    logger.debug(f"stderr_capture has buffer: {hasattr(stderr_capture, 'buffer')}")

    result = None
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            logger.debug("Calling tenzir_test.execute()")
            result = execute(
                tests=test_paths,
                root=root_path,
                update=update,
                passthrough=passthrough,
                show_summary=True,
            )
            logger.debug(f"Test completed with exit code: {result.exit_code}")
    except SystemExit as e:
        logger.error(f"Test execution failed with SystemExit: {e}", exc_info=True)
        exit_code = e.code if isinstance(e.code, int) else 1
    except Exception as e:
        logger.error(f"Test execution failed with exception: {e}", exc_info=True)
        exit_code = 1
    else:
        exit_code = result.exit_code if result else 1

    # Flush the wrappers and get output from the underlying buffers
    stdout_capture.flush()
    stderr_capture.flush()
    stdout = stdout_buffer.getvalue().decode("utf-8")
    stderr = stderr_buffer.getvalue().decode("utf-8")

    # Combine stdout and stderr
    output = stdout
    if stderr:
        output += f"\n{stderr}"

    # Format as markdown
    status = "✓ Passed" if exit_code == 0 else "✗ Failed"
    content = f"**Status**: {status}\n**Exit Code**: {exit_code}\n\n```\n{output}\n```"

    return ToolResult(
        content=content,  # Markdown formatted output
        structured_content={
            "exit_code": exit_code,
            "success": exit_code == 0,
            "output": output,
            "passthrough": passthrough,
            "update": update,
        },
    )
