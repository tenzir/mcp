"""Package operator management tool."""

import logging
from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import validate_package_dir

logger = logging.getLogger(__name__)


@mcp.tool(
    name="package_add_operator",
    tags={"packaging"},
    annotations={
        "title": "Add operator to package",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def package_add_operator(
    package: Annotated[str, Field(description="Path to the package directory")],
    name: Annotated[str, Field(description="Name of the operator")],
    description: Annotated[
        str, Field(description="Description of what the operator does")
    ],
    code: Annotated[str, Field(description="TQL code implementing the operator")],
    no_tests: Annotated[
        bool,
        Field(
            default=False,
            description="Skip creating test scaffold for this operator",
        ),
    ],
) -> ToolResult:
    """Add a user-defined operator (UDO) to a package."""
    try:
        # Validate package directory
        pkg_data = validate_package_dir(package)
        pkg_path = Path(package)
        package_id = pkg_data.get("id", pkg_path.name)

        # Create operators directory if it doesn't exist
        operators_dir = pkg_path / "operators"
        operators_dir.mkdir(exist_ok=True)

        # Write operator file
        operator_file = operators_dir / f"{name}.tql"
        operator_file.write_text(code)

        # Fully qualified operator name
        full_name = f"{package_id}::{name}"

        # Create test scaffold if requested
        test_created = False
        if not no_tests:
            tests_dir = pkg_path / "tests"
            tests_dir.mkdir(exist_ok=True)

            test_file = tests_dir / f"test-{name}.tql"
            if not test_file.exists():
                # Create basic test scaffold
                test_content = f"""---
runner: tenzir
timeout: 30
---
# Test for {full_name}
# TODO: Add test inputs and expected outputs
from stdin | {full_name}
"""
                test_file.write_text(test_content)
                test_created = True

        result = {
            "file_path": str(operator_file),
            "operator_name": full_name,
            "test_created": test_created,
            "summary": f"Added operator {full_name} to package",
        }

        # Format as markdown
        content = f"# Operator Added\n\n**Name**: `{full_name}`\n**File**: `{operator_file}`\n"
        if test_created:
            content += "\n✓ Test scaffold created"

        return ToolResult(content=content, structured_content=result)

    except ValueError as e:
        error_msg = str(e)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
    except Exception as e:
        error_msg = f"Failed to add operator: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
