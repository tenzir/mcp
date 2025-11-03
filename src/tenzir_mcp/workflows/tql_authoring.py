"""Authoring workflow for TQL pipelines."""

from __future__ import annotations

from typing import Any

from tenzir_mcp.app import mcp

from ._tql_common import (
    STYLE_LEVELS,
    TASK_TYPES,
    get_style_guidance,
    get_task_specific_guidance,
    load_general_tql_base,
)

__all__ = ["workflow_tql_authoring"]


@mcp.tool(name="workflow_tql_authoring", tags={"tql", "workflow"})
async def workflow_tql_authoring(
    task_type: str = "general",
    style_level: str = "strict",
) -> dict[str, Any]:
    """Provide workflow guidance for writing TQL pipelines."""

    normalized_task = task_type.lower()
    normalized_style = style_level.lower()
    instructions = load_general_tql_base()
    warnings: list[str] = []

    task_guidance = get_task_specific_guidance(normalized_task)
    if not task_guidance and normalized_task not in TASK_TYPES:
        warnings.append(
            f"Unsupported task type '{task_type}'. Falling back to general guidance."
        )
    else:
        if task_guidance:
            instructions = f"{instructions}\n{task_guidance}"

    style_guidance = get_style_guidance(normalized_style)
    if not style_guidance and normalized_style not in STYLE_LEVELS:
        warnings.append(
            f"Unsupported style level '{style_level}'. Defaulting to strict guidance."
        )
        style_guidance = get_style_guidance("strict")

    if style_guidance:
        instructions = f"{instructions}\n{style_guidance}"

    return {
        "instructions": instructions.strip(),
        "task_type": normalized_task if normalized_task in TASK_TYPES else "general",
        "style_level": (
            normalized_style if normalized_style in STYLE_LEVELS else "strict"
        ),
        "warnings": warnings,
    }
