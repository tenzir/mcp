"""Shared utility functions for OCSF schema tools."""

import json
from typing import Any

try:
    from importlib.resources import files
except ImportError:
    from importlib_resources import files  # type: ignore


def load_ocsf_schema(version: str) -> dict[str, Any]:
    """
    Load and parse an OCSF schema for the specified version.

    Args:
        version: The OCSF schema version to load

    Returns:
        Dictionary containing the parsed OCSF schema

    Raises:
        FileNotFoundError: If the schema version is not found
        json.JSONDecodeError: If the schema JSON is invalid
        Exception: For other loading errors
    """
    schema_text = files("tenzir_mcp.data.ocsf").joinpath(f"{version}.json").read_text()
    schema: dict[str, Any] = json.loads(schema_text)
    return schema
