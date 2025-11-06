"""OCSF mapping package generator."""

import logging
from pathlib import Path
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp
from tenzir_mcp.tools.coding.make_parser import (
    _detect_csv_delimiter,
    _infer_schema,
    _score_csv,
    _score_json,
    _score_kv,
    _score_syslog,
)
from tenzir_mcp.tools.ocsf import ocsf_get_class, ocsf_get_latest_version
from tenzir_mcp.tools.packaging import (
    package_add_changelog,
    package_add_operator,
    package_add_test,
    package_create,
)

logger = logging.getLogger(__name__)


def _identify_ocsf_classes(samples: list[str]) -> list[str]:
    """
    Identify potential OCSF classes based on sample content.

    Args:
        samples: Sample log events

    Returns:
        List of candidate OCSF class names
    """
    # Analyze content for keywords
    content = " ".join(samples).lower()

    candidates = []

    # Network activity indicators
    if any(
        kw in content for kw in ["src_ip", "dst_ip", "network", "connection", "packet"]
    ):
        candidates.append("Network Activity")

    # File activity indicators
    if any(kw in content for kw in ["file", "path", "filename", "directory"]):
        candidates.append("File Activity")

    # Process activity indicators
    if any(kw in content for kw in ["process", "pid", "command", "executable"]):
        candidates.append("Process Activity")

    # Authentication indicators
    if any(kw in content for kw in ["login", "auth", "user", "password", "session"]):
        candidates.append("Authentication")

    # Security finding indicators
    if any(
        kw in content
        for kw in ["alert", "finding", "vulnerability", "threat", "malware"]
    ):
        candidates.append("Security Finding")

    # HTTP activity indicators
    if any(
        kw in content for kw in ["http", "url", "request", "response", "status_code"]
    ):
        candidates.append("HTTP Activity")

    # Default if nothing matches
    if not candidates:
        candidates.append("Base Event")

    return candidates


def _propose_mappings(
    samples: list[str],
    class_schema: dict[str, Any],
    detected_format: str,
) -> dict[str, str]:
    """
    Propose field mappings from source to OCSF schema.

    Args:
        samples: Sample log events
        class_schema: OCSF class schema
        detected_format: Detected log format

    Returns:
        Dictionary mapping source fields to OCSF fields
    """
    mappings: dict[str, str] = {}

    # Get source schema
    source_schema = _infer_schema(samples, detected_format)

    # Get OCSF attributes
    ocsf_attributes = class_schema.get("data", {}).get("attributes", {})

    # Simple heuristic mapping based on field names
    for source_field in source_schema:
        source_lower = source_field.lower()

        # Direct name matching
        for ocsf_field, _ocsf_meta in ocsf_attributes.items():
            ocsf_lower = ocsf_field.lower()

            # Exact match
            if source_lower == ocsf_lower:
                mappings[source_field] = ocsf_field
                break

            # Common variations
            if source_lower in ocsf_lower or ocsf_lower in source_lower:
                mappings[source_field] = ocsf_field
                break

            # Handle underscore/camelCase variations
            if source_lower.replace("_", "") == ocsf_lower.replace("_", ""):
                mappings[source_field] = ocsf_field
                break

    return mappings


def _generate_ocsf_mapping_code(
    mappings: dict[str, str],
    target_class: str,
    class_schema: dict[str, Any],
) -> str:
    """
    Generate TQL code for OCSF mapping.

    Args:
        mappings: Field mappings (source -> OCSF)
        target_class: Target OCSF class name
        class_schema: OCSF class schema

    Returns:
        TQL code for mapping
    """
    code_lines = []

    # Add comment header
    code_lines.append(f"# Map to OCSF {target_class}")
    code_lines.append("")

    # Generate field mappings
    code_lines.append("# Field mappings")
    for source_field, ocsf_field in mappings.items():
        code_lines.append(f"{ocsf_field} = {source_field}")

    # Add OCSF class metadata
    class_id = class_schema.get("id", "")
    code_lines.append("")
    code_lines.append("# OCSF metadata")
    code_lines.append(f'class_name = "{target_class}"')
    code_lines.append(f"class_uid = {class_id}")

    # Add category_uid (required field)
    code_lines.append("")
    code_lines.append("# Required OCSF fields")
    code_lines.append("category_uid = 1  # TODO: Set appropriate category")

    return "\n".join(code_lines)


@mcp.tool(
    name="make_ocsf_mapping",
    tags={"coding"},
    annotations={
        "title": "Generate OCSF mapping package",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def make_ocsf_mapping(
    samples: Annotated[
        list[str], Field(description="Sample events to generate OCSF mapping from")
    ],
    ctx: Any = None,
) -> ToolResult:
    """Generate a complete OCSF mapping package."""
    if not samples:
        error_msg = "No sample events provided"
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )

    warnings: list[str] = []

    try:
        # 1. Infer log format
        format_scores = {
            "json": _score_json(samples),
            "csv": _score_csv(samples),
            "syslog": _score_syslog(samples),
            "kv": _score_kv(samples),
        }

        detected_format = max(format_scores, key=format_scores.get)  # type: ignore
        confidence = format_scores[detected_format]

        logger.info(f"Detected format: {detected_format} ({confidence:.0%})")

        if confidence < 0.8:
            warnings.append(f"Low confidence ({confidence:.0%}) in format detection")

        # 2. Determine OCSF target class
        candidates = _identify_ocsf_classes(samples)
        target_class = candidates[0]

        if len(candidates) > 1 and ctx:
            try:
                result = await ctx.elicit(
                    message=f"Multiple OCSF classes match: {', '.join(candidates)}. Which one?",
                    response_type=candidates,
                )
                if result.action == "accept" and result.data:
                    target_class = result.data
            except Exception as e:
                logger.warning(f"Elicitation failed: {e}")

        logger.info(f"Selected OCSF class: {target_class}")

        # 3. Get OCSF schema
        latest = await ocsf_get_latest_version.fn()
        class_schema = await ocsf_get_class.fn(version=latest, name=target_class)

        if "error" in class_schema:
            error_msg = f"Failed to get OCSF schema: {class_schema['error']}"
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        # 4. Generate field mappings
        mappings = _propose_mappings(samples, class_schema, detected_format)

        logger.info(f"Generated {len(mappings)} field mappings")

        # 5. Create package
        package_name = f"ocsf_{target_class.lower().replace(' ', '_')}"
        package_path = f"/tmp/{package_name}"

        # Check if package already exists
        if Path(package_path).exists():
            # Add timestamp to make unique
            import time

            timestamp = int(time.time())
            package_path = f"/tmp/{package_name}_{timestamp}"

        create_result = await package_create.fn(directory=package_path, ctx=None)

        if "error" in create_result:
            error_msg = f"Failed to create package: {create_result['error']}"
            return ToolResult(
                content=f"Error: {error_msg}", structured_content={"error": error_msg}
            )

        # 6. Add parser operator
        parser_code = _generate_parser_code(detected_format, samples)
        parser_result = await package_add_operator.fn(
            package=package_path,
            name="parse",
            description=f"Parse {detected_format} logs",
            code=parser_code,
            no_tests=True,  # We'll create integrated tests
        )

        if "error" in parser_result:
            warnings.append(f"Failed to add parser operator: {parser_result['error']}")

        # 7. Add OCSF mapping operator
        mapping_code = _generate_ocsf_mapping_code(mappings, target_class, class_schema)
        mapping_result = await package_add_operator.fn(
            package=package_path,
            name="map_ocsf",
            description=f"Map to OCSF {target_class}",
            code=mapping_code,
            no_tests=True,
        )

        if "error" in mapping_result:
            warnings.append(
                f"Failed to add mapping operator: {mapping_result['error']}"
            )

        # 8. Add integrated test
        test_input = [
            "# Full pipeline test",
            f"from stdin | {package_name}::parse | {package_name}::map_ocsf",
        ]
        test_result = await package_add_test.fn(
            package=package_path,
            path="test_mapping.tql",
            input=test_input,
            output=[],  # Will be generated with --update
        )

        if "error" in test_result:
            warnings.append(f"Failed to add test: {test_result['error']}")

        # 9. Add changelog entry
        changelog_result = await package_add_changelog.fn(
            package=package_path,
            type="feature",
            description=f"Initial OCSF {target_class} mapping for {detected_format} logs",
        )

        if "error" in changelog_result:
            warnings.append(f"Failed to add changelog: {changelog_result['error']}")

        # 10. Return package summary
        structured_result = {
            "package_path": package_path,
            "structure": create_result.get("structure", ""),
            "summary": f"Created OCSF {target_class} mapping package for {detected_format} logs",
            "operators": [
                {
                    "name": f"{package_name}::parse",
                    "description": f"Parse {detected_format} logs",
                },
                {
                    "name": f"{package_name}::map_ocsf",
                    "description": f"Map to OCSF {target_class}",
                },
            ],
            "warnings": warnings,
            "mappings": mappings,
        }

        content = f"""# OCSF Mapping Package Created

**Target Class**: `{target_class}`
**Source Format**: `{detected_format}`
**Package Path**: `{package_path}`
**Samples Analyzed**: {len(samples)}
**Field Mappings**: {len(mappings)}

## Operators
- `{package_name}::parse` - Parse {detected_format} logs
- `{package_name}::map_ocsf` - Map to OCSF {target_class}"""

        return ToolResult(content=content, structured_content=structured_result)

    except Exception as e:
        error_msg = f"Failed to generate OCSF mapping: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )


def _generate_parser_code(format_type: str, events: list[str]) -> str:
    """Generate parser code for the detected format."""
    code_lines = []

    if format_type == "json":
        code_lines.append("read_json")
        code_lines.append("unflatten")

    elif format_type == "csv":
        delimiter = _detect_csv_delimiter(events)
        code_lines.append(f'read_csv delimiter="{delimiter}"')

    elif format_type == "syslog":
        code_lines.append("read_syslog")

    elif format_type == "kv":
        code_lines.append('read_kv separator="="')

    return "\n".join(code_lines)
