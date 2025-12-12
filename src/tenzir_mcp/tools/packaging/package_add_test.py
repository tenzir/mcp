"""Package test management tool."""

from pathlib import Path
from typing import Annotated

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import (
    generate_frontmatter,
    validate_package_dir,
)

logger = get_logger(__name__)


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
    package_dir: Annotated[str, Field(description="Path to the package directory")],
    test: Annotated[
        str,
        Field(description="TQL code written in the test file"),
    ],
    test_file: Annotated[
        str | None,
        Field(
            default=None,
            description="Path to the test file relative to package tests directory. If not provided, a default name will be generated.",
            examples=["ocsf/map.tql", "onboard.tql"],
        ),
    ],
    input: Annotated[
        str | None,
        Field(
            default=None,
            description="Input data to feed to the pipeline. Pairs with `output` to define test expectations. Omit when the test generates data inline using TQL operators like `from`.",
        ),
    ],
    output: Annotated[
        str | None,
        Field(
            default=None,
            description="Expected output from the pipeline. Pairs with `input` for input/output tests, or used alone when the test generates data inline.",
        ),
    ],
    fixtures: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="List of fixture names (optional)",
            examples=["node", "http"],
        ),
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
    """Add a test to a package.

    Use this tool to:
    - Create test cases for your operators
    - Define expected behavior with input/output pairs
    - Set up integration tests with fixtures (e.g., embedded Tenzir nodes)
    - Generate test scaffolds to be populated later with run_test

    Tests use the tenzir-test framework. Provide input/output when known,
    or omit output and use the `run_test` tool with `update=True` to generate
    baselines from actual execution."""
    try:
        # Validate required parameters
        if not package_dir:
            raise ValueError(
                "'package_dir' must be provided. Use 'package_create' tool to create a package first."
            )
        if not test:
            raise ValueError("'test' must be provided")

        # Validate package directory
        validate_package_dir(package_dir)
        pkg_path = Path(package_dir)

        # Create tests directory if needed
        tests_dir = pkg_path / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Generate test filename if not provided
        if not test_file:
            # Find next available test_NNN.tql filename
            counter = 1
            while (tests_dir / f"test_{counter:03d}.tql").exists():
                counter += 1
            test_file = f"test_{counter:03d}.tql"

        # Build test file path
        test_file_path = tests_dir / test_file
        test_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Build frontmatter metadata
        metadata: dict[str, int | list[str]] = {}
        if fixtures:
            metadata["fixtures"] = fixtures
        if timeout:
            metadata["timeout"] = timeout

        # Generate frontmatter
        frontmatter = generate_frontmatter(metadata)

        # Build test file content (frontmatter + TQL code)
        test_content = frontmatter + test
        if not test.endswith("\n"):
            test_content += "\n"

        # Write test file
        test_file_path.write_text(test_content)

        # Create input file if input data is provided
        input_file = None
        if input:
            # Create inputs directory
            inputs_dir = tests_dir / "inputs"
            inputs_dir.mkdir(exist_ok=True)

            # Derive input filename from test path (e.g., foo/bar.tql -> inputs/foo/bar.txt)
            input_file = inputs_dir / Path(test_file).with_suffix(".txt")
            input_file.parent.mkdir(parents=True, exist_ok=True)

            input_content = input
            if not input_content.endswith("\n"):
                input_content += "\n"
            input_file.write_text(input_content)

        # Create output (baseline) file
        baseline_file = test_file_path.with_suffix(".txt")
        if output:
            baseline_content = output
            if not baseline_content.endswith("\n"):
                baseline_content += "\n"
            baseline_file.write_text(baseline_content)

        result = {
            "test_file": str(test_file_path),
            "input_file": str(input_file) if input_file else None,
            "baseline_file": str(baseline_file) if output else None,
            "package_dir": str(pkg_path),
            "generated_test_name": test_file,
            "input": input,
            "output": output,
            "fixtures": fixtures,
            "timeout": timeout,
        }

        fixtures_value = ", ".join(fixtures) if fixtures else "None"
        baseline_path = result["baseline_file"] or "Not created"
        input_path = result["input_file"] or "Not created"
        timeout_value = result["timeout"] if result["timeout"] is not None else "None"

        details_lines = [
            f"- Package Directory: `{result['package_dir']}`",
            f"- Test File: `{result['test_file']}`",
            f"- Generated Name: `{result['generated_test_name']}`",
            f"- Input File: `{input_path}`",
            f"- Baseline File: `{baseline_path}`",
            f"- Fixtures: {fixtures_value}",
            f"- Timeout: {timeout_value}",
        ]

        def format_block(title: str, value: str | None) -> str:
            if value is None:
                return f"## {title}\n_None provided_\n"
            return f"## {title}\n```\n{value}\n```\n"

        content = (
            "# Test Added\n\n"
            + "\n".join(details_lines)
            + "\n\n"
            + format_block("Input Data", input)
            + "\n"
            + format_block("Expected Output", output)
        )

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
