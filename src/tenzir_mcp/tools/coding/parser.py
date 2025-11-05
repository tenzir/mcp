"""Log parser code generator."""

import json
import logging
import re
from typing import Annotated, Any

from fastmcp.tools.tool import ToolResult
from pydantic import Field

from tenzir_mcp.server import mcp

logger = logging.getLogger(__name__)


def _score_json(events: list[str]) -> float:
    """Score how likely events are JSON format."""
    if not events:
        return 0.0

    json_count = 0
    for event in events[:10]:  # Sample first 10
        try:
            json.loads(event)
            json_count += 1
        except (json.JSONDecodeError, ValueError):
            pass

    return json_count / min(len(events), 10)


def _score_csv(events: list[str]) -> float:
    """Score how likely events are CSV format."""
    if not events:
        return 0.0

    # Check for consistent delimiter patterns
    delimiters = [",", ";", "\t", "|"]
    scores = []

    for delimiter in delimiters:
        counts = [len(event.split(delimiter)) for event in events[:10]]
        if counts and min(counts) == max(counts) and min(counts) > 1:
            scores.append(0.9)
        elif counts and len(set(counts)) <= 2:
            scores.append(0.6)
        else:
            scores.append(0.0)

    return max(scores) if scores else 0.0


def _score_syslog(events: list[str]) -> float:
    """Score how likely events are syslog format."""
    if not events:
        return 0.0

    # Check for syslog patterns: timestamp + hostname + message
    syslog_pattern = r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    matches = sum(1 for event in events[:10] if re.match(syslog_pattern, event))

    return matches / min(len(events), 10)


def _score_kv(events: list[str]) -> float:
    """Score how likely events are key=value format."""
    if not events:
        return 0.0

    # Check for key=value patterns
    kv_pattern = r"\w+=[^\s]+"
    matches = 0

    for event in events[:10]:
        kv_pairs = re.findall(kv_pattern, event)
        if len(kv_pairs) >= 3:  # At least 3 key=value pairs
            matches += 1

    return matches / min(len(events), 10)


def _detect_csv_delimiter(events: list[str]) -> str:
    """Detect CSV delimiter from samples."""
    delimiters = [",", ";", "\t", "|"]
    delimiter_scores = []

    for delimiter in delimiters:
        counts = [len(event.split(delimiter)) for event in events[:10]]
        if counts and min(counts) == max(counts) and min(counts) > 1:
            delimiter_scores.append((delimiter, min(counts)))

    if delimiter_scores:
        return max(delimiter_scores, key=lambda x: x[1])[0]

    return ","


def _infer_schema(events: list[str], format_type: str) -> dict[str, dict[str, Any]]:
    """Infer schema from sample events."""
    schema: dict[str, dict[str, Any]] = {}

    if format_type == "json":
        # Parse JSON and infer types
        for event in events[:5]:
            try:
                obj = json.loads(event)
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if key not in schema:
                            schema[key] = {
                                "type": _infer_type(value),
                                "nullable": False,
                            }
            except (json.JSONDecodeError, ValueError):
                pass

    elif format_type == "csv":
        # Use first line as headers
        delimiter = _detect_csv_delimiter(events)
        if events:
            headers = events[0].split(delimiter)
            for header in headers:
                header_clean = header.strip()
                schema[header_clean] = {"type": "string", "nullable": False}

    elif format_type == "kv":
        # Extract all key names
        kv_pattern = r"(\w+)=[^\s]+"
        all_keys = []
        for event in events[:10]:
            keys = re.findall(kv_pattern, event)
            all_keys.extend(keys)

        for key in set(all_keys):
            schema[key] = {"type": "string", "nullable": False}

    return schema


def _infer_type(value: Any) -> str:
    """Infer TQL type from Python value."""
    if isinstance(value, bool):
        return "bool"
    elif isinstance(value, int):
        return "int"
    elif isinstance(value, float):
        return "double"
    elif isinstance(value, str):
        # Try to detect time strings
        if re.match(r"\d{4}-\d{2}-\d{2}", value):
            return "time"
        return "string"
    elif isinstance(value, list):
        return "list"
    elif isinstance(value, dict):
        return "record"
    else:
        return "string"


def _generate_parser_code(
    format_type: str, schema: dict[str, dict[str, Any]], events: list[str]
) -> str:
    """Generate TQL parser code for the detected format."""
    code_lines = []

    if format_type == "json":
        code_lines.append("read_json")
        if any("." in key for key in schema):
            code_lines.append("unflatten")

    elif format_type == "csv":
        delimiter = _detect_csv_delimiter(events)
        code_lines.append(f'read_csv delimiter="{delimiter}"')
        # Add field selection if we have headers
        if schema:
            fields = ", ".join(schema.keys())
            code_lines.append(f"select {fields}")

    elif format_type == "syslog":
        code_lines.append("read_syslog")

    elif format_type == "kv":
        # Detect separator (= or :)
        separator = "="
        if events and ":" in events[0] and "=" not in events[0]:
            separator = ":"
        code_lines.append(f'read_kv separator="{separator}"')

    elif format_type == "cef":
        code_lines.append("read_cef")

    return "\n".join(code_lines)


def _generate_type_conversions(schema: dict[str, dict[str, Any]]) -> str:
    """Generate type conversion operators for rich typing."""
    conversions = []

    for field, type_info in schema.items():
        field_type = type_info["type"]

        # Skip string types (default)
        if field_type == "string":
            continue

        # Generate appropriate type conversion
        if field_type == "int":
            conversions.append(f"{field} = int({field})")
        elif field_type == "double":
            conversions.append(f"{field} = double({field})")
        elif field_type == "bool":
            conversions.append(f"{field} = bool({field})")
        elif field_type == "time":
            conversions.append(f"{field} = time({field})")

    if conversions:
        return "\n" + "\n".join(conversions)
    return ""


@mcp.tool(
    name="make_parser",
    tags={"coding"},
    annotations={
        "title": "Generate TQL parser",
        "readOnlyHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def make_parser(
    events: Annotated[
        list[str], Field(description="Sample log events to generate parser from")
    ],
    ctx: Any = None,
) -> ToolResult:
    """Generate a TQL parser for the given log format."""
    if not events:
        error_msg = "No events provided"
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )

    warnings: list[str] = []

    try:
        # 1. Detect format from samples
        format_scores = {
            "json": _score_json(events),
            "csv": _score_csv(events),
            "syslog": _score_syslog(events),
            "kv": _score_kv(events),
        }

        detected = max(format_scores, key=format_scores.get)  # type: ignore
        confidence = format_scores[detected]

        logger.info(f"Detected format: {detected} ({confidence:.0%} confidence)")
        logger.info(f"All scores: {format_scores}")

        # 2. Elicit if low confidence
        if confidence < 0.8 and ctx:
            try:
                result = await ctx.elicit(
                    message=f"Detected {detected} format with {confidence:.0%} confidence. Is this correct?",
                    response_type=["json", "csv", "syslog", "cef", "kv", "other"],
                )
                if result.action == "accept" and result.data:
                    detected = result.data
                    logger.info(f"User confirmed format: {detected}")
            except Exception as e:
                logger.warning(f"Elicitation failed: {e}")
                warnings.append(
                    f"Could not confirm format (using detected: {detected})"
                )

        if confidence < 0.8:
            warnings.append(
                f"Low confidence ({confidence:.0%}) in format detection. Parser may need adjustments."
            )

        # 3. Infer schema (field names, types)
        schema = _infer_schema(events, detected)

        # 4. Generate parser code
        code = _generate_parser_code(detected, schema, events)

        # 5. Add type conversions
        code += _generate_type_conversions(schema)

        # 6. Build explanation
        explanation = (
            f"Detected {detected} format with {len(schema)} fields. "
            f"Parser uses {detected}-specific operators"
        )
        if detected == "json":
            explanation += " with JSON parsing and optional flattening."
        elif detected == "csv":
            delimiter = _detect_csv_delimiter(events)
            explanation += f' with delimiter "{delimiter}".'
        elif detected == "kv":
            explanation += " with key=value pair extraction."

        structured_result = {
            "code": code,
            "format": detected,
            "schema": schema,
            "explanation": explanation,
            "warnings": warnings,
        }

        content = f"""# Parser Generated

**Format**: `{detected}`
**Fields**: {len(schema)}
**Explanation**: {explanation}

## Generated Parser
```tql
{code}
```"""

        return ToolResult(content=content, structured_content=structured_result)

    except Exception as e:
        error_msg = f"Failed to generate parser: {e}"
        logger.error(error_msg)
        return ToolResult(
            content=f"Error: {error_msg}", structured_content={"error": error_msg}
        )
