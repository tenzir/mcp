"""Package operator management tool."""

from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import validate_package_dir

logger = get_logger(__name__)


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
    package_dir: Annotated[str, Field(description="Path to the package directory")],
    name: Annotated[
        str,
        Field(
            description="Name of the operator. Supports nested namespaces using '::' separator (e.g., 'parse', 'ocsf::logs::firewall')",
            examples=["parse", "to_ocsf", "ocsf::logs::my_log_type"],
        ),
    ],
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
    """Add a user-defined operator (UDO) to a package.

    Use this tool to:
    - Add custom TQL operators to your package
    - Organize operators using nested namespaces (e.g., 'ocsf::logs::firewall')
    - Create parsers, transformations, or OCSF mappings as reusable operators
    - Automatically generate test scaffolds for new operators

    Operators become available as package_id::operator_name in TQL pipelines
    after the package is installed."""
    try:
        # Validate package directory
        pkg_data = validate_package_dir(package_dir)
        pkg_path = Path(package_dir)
        package_id = pkg_data.get("id", pkg_path.name)

        # Parse operator name for nested structure
        # Convert :: separators to path separators
        name_parts = name.split("::")
        operator_name = name_parts[-1]  # Last part is the actual operator name
        namespace_parts = name_parts[:-1]  # Everything before is namespace

        # Create operators directory with nested structure
        operators_dir = pkg_path / "operators"
        for part in namespace_parts:
            operators_dir = operators_dir / part
        operators_dir.mkdir(parents=True, exist_ok=True)

        # Write operator file
        operator_file = operators_dir / f"{operator_name}.tql"
        operator_file.write_text(code)

        # Fully qualified operator name
        full_name = f"{package_id}::{name}"

        # Create test scaffold if requested
        test_created = False
        if not no_tests:
            tests_dir = pkg_path / "tests"
            tests_dir.mkdir(exist_ok=True)

            # Flatten nested name with dashes for test file
            test_name = name.replace("::", "-")
            test_file = tests_dir / f"test-{test_name}.tql"
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
        test_status = "Created" if test_created else "Not created"
        content = (
            "# Operator Added\n\n"
            f"**Name**: `{full_name}`\n"
            f"**File**: `{operator_file}`\n"
            f"**Summary**: {result['summary']}\n"
            f"**Test Scaffold**: {test_status}\n"
        )

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
