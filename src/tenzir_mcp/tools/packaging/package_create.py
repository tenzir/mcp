"""Package creation tool."""

from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from fastmcp.utilities.logging import get_logger
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.packaging._helpers import (
    ensure_directory,
    generate_tree,
    validate_package_id,
    write_package_yaml,
)

logger = get_logger(__name__)


@mcp.tool(
    name="package_create",
    tags={"packaging"},
    annotations={
        "title": "Create package",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    },
)
async def package_create(
    package_dir: Annotated[
        str, Field(description="Directory path for the new package")
    ],
    ctx: Any = None,
) -> ToolResult:
    """Create a new Tenzir package scaffold.

    Use this tool to:
    - Start a new Tenzir package project
    - Set up the standard directory structure for operators, tests, and documentation
    - Initialize package metadata (ID, name, author, description)

    This creates the foundation for building custom TQL operators, parsers,
    and OCSF mappings. After creation, use `package_add_operator` to add
    functionality and `package_add_test` to add tests."""
    try:
        pkg_path = Path(package_dir).resolve()

        # Validate directory doesn't exist
        if pkg_path.exists():
            error_msg = f"Directory {package_dir} already exists"
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        # Elicit package metadata
        package_id = pkg_path.name
        package_name = package_id.replace("_", " ").replace("-", " ").title()
        package_author = "Unknown"
        package_description = "Package description"

        if ctx:
            try:
                # Elicit package ID
                result = await ctx.elicit(
                    message=f"Enter package ID (default: {package_id})",
                    response_type=str,
                )
                if result.action == "accept" and result.data:
                    package_id = result.data.strip()

                # Validate package ID
                if not validate_package_id(package_id):
                    error_msg = f"Invalid package ID '{package_id}'. Must be lowercase alphanumeric with underscores/hyphens."
                    return ToolResult(
                        content=f"Error: {error_msg}",
                        structured_content={"error": error_msg},
                    )

                # Elicit package name
                result = await ctx.elicit(
                    message=f"Enter package name (default: {package_name})",
                    response_type=str,
                )
                if result.action == "accept" and result.data:
                    package_name = result.data.strip()

                # Elicit author
                result = await ctx.elicit(
                    message="Enter author name (default: Unknown)",
                    response_type=str,
                )
                if result.action == "accept" and result.data:
                    package_author = result.data.strip()

                # Elicit description
                result = await ctx.elicit(
                    message="Enter package description",
                    response_type=str,
                )
                if result.action == "accept" and result.data:
                    package_description = result.data.strip()

            except Exception as e:
                logger.warning(f"Elicitation failed, using defaults: {e}")

        # Create directory structure
        ensure_directory(pkg_path)
        ensure_directory(pkg_path / "operators")
        ensure_directory(pkg_path / "pipelines")
        ensure_directory(pkg_path / "tests" / "inputs")
        ensure_directory(pkg_path / "changelog")

        # Create package.yaml
        package_yaml = {
            "id": package_id,
            "name": package_name,
            "description": package_description,
            "author": package_author,
            "version": "0.1.0",
        }
        write_package_yaml(pkg_path, package_yaml)

        # Create README.md
        readme_content = f"""# {package_name}

{package_description}

## Installation

```bash
tenzir-ctl install {package_id}
```

## Usage

<!-- Add usage examples here -->

## Operators

<!-- List operators here -->

## License

<!-- Add license information here -->
"""
        (pkg_path / "README.md").write_text(readme_content)

        # Generate tree structure
        tree = generate_tree(pkg_path)

        result = {
            "directory": str(pkg_path),
            "structure": tree,
            "package_id": package_id,
            "next_steps": [
                "Add operators with package_add_operator",
                "Add tests with package_add_test",
                "Add changelog entries with package_add_changelog",
            ],
        }

        next_steps_lines = "\n".join(f"- {step}" for step in result["next_steps"])
        structure_block = tree or "(empty directory)"
        content = (
            "# Package Created\n\n"
            f"**Package ID**: `{result['package_id']}`\n"
            f"**Directory**: `{result['directory']}`\n\n"
            "## Structure\n"
            f"```\n{structure_block}\n```\n\n"
            "## Next Steps\n"
            f"{next_steps_lines}"
        )

        return ToolResult(content=content, structured_content=result)

    except Exception as e:
        error_msg = f"Failed to create package: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}",
            structured_content={"error": error_msg, "directory": package_dir},
        )
