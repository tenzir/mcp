"""Completion checklist workflow for TQL pipelines."""

from __future__ import annotations

from typing import Any

from tenzir_mcp.app import mcp

from ._tql_common import CHECKLIST_ITEMS

__all__ = ["workflow_tql_completion"]


@mcp.tool(name="workflow_tql_completion", tags={"tql", "workflow"})
async def workflow_tql_completion() -> dict[str, Any]:
    """Checklist to run after finishing TQL authoring."""

    checklist_text = "Final TQL validation checklist:\n- " + "\n- ".join(
        CHECKLIST_ITEMS
    )

    return {
        "items": CHECKLIST_ITEMS,
        "checklist": checklist_text,
    }
