"""Shared helpers for TQL workflow tools."""

from __future__ import annotations

from textwrap import dedent

__all__ = [
    "CHECKLIST_ITEMS",
    "TASK_TYPES",
    "STYLE_LEVELS",
    "load_general_tql_base",
    "get_task_specific_guidance",
    "get_style_guidance",
]

_GENERAL_TQL_BASE = dedent(
    """
    VERY IMPORTANT: BEFORE YOU USE ANY OPERATOR, YOU MUST READ ITS DOCUMENTATION.
    THIS APPLIES TO ALL SITUATIONS AND EVERY SINGLE OPERATOR. NO EXCEPTIONS!
    BEFORE YOU USE A FUNCTION, YOU MUST READ ITS DOCUMENTATION.
    DO NOT USE OPERATORS OR FUNCTIONS WITHOUT READING THEIR DOCUMENTATION.
    FAILURE TO READ DOCUMENTATION WILL RESULT IN INCORRECT CODE.
    BEFORE WRITING ANY TQL, MAKE SURE YOU READ THE DOCUMENTATION.

    MUST: ALWAYS read and follow the TQL style guide at tutorials/learn-idiomatic-tql.

    IMPORTANT: Following documentation is important to understand the language:
    - explanations/language/
    - explanations/language/types/
    - explanations/language/statements/
    - explanations/language/expressions/
    - explanations/language/programs/
    - reference/operators => List of all available operators
    - reference/functions => List of all available functions
    """
).strip()

_TASK_GUIDANCE = {
    "general": "",
    "parsing": dedent(
        """

        PARSING FOCUS:
        - Prototype with representative samples before scaling to the full dataset.
        - Compare multiple readers (e.g., `read_grok`, `read_syslog`, `read_lines`) and explain the chosen trade-offs.
        - Capture assumptions about malformed or optional fields so downstream stages can validate them.
        """
    ).rstrip(),
    "transformation": dedent(
        """

        TRANSFORMATION FOCUS:
        - Track schema changes after each operator; reference `schema` output where possible.
        - Highlight opportunities to collapse redundant operations or push filters closer to the source.
        - Document every aggregation with its intended business meaning.
        """
    ).rstrip(),
    "output": dedent(
        """

        OUTPUT FOCUS:
        - Validate formatting and field ordering using small verification queries.
        - Note how downstream systems consume the output (streaming vs. batch, enrichment expectations, etc.).
        - Include fallback behaviour for missing or unexpected values.
        """
    ).rstrip(),
}

_STYLE_GUIDANCE = {
    "strict": dedent(
        """

        STYLE ENFORCEMENT (STRICT):
        - Enforce naming, indentation, and comment rules from tutorials/learn-idiomatic-tql without exception.
        - Require evidence (execution logs or diffs) for every claimed improvement.
        - Log every deviation from best practices with justification and remediation plan.
        """
    ).rstrip(),
    "moderate": dedent(
        """

        STYLE ENFORCEMENT (MODERATE):
        - Prioritise clarity and consistency; explain any deliberate deviations from the style guide.
        - Ensure all helper comments clarify business intent, not obvious mechanics.
        """
    ).rstrip(),
    "relaxed": dedent(
        """

        STYLE ENFORCEMENT (RELAXED):
        - Follow critical readability and correctness rules, but balance speed when iterating.
        - Leave TODO comments for any styling follow-up the user should revisit.
        """
    ).rstrip(),
}

CHECKLIST_ITEMS: list[str] = [
    "Execute the pipeline and confirm it succeeds without warnings.",
    "Ensure every required OCSF field is populated when building mappings.",
    "Verify the mapping handles representative variations in the input.",
    "Confirm no values were lost or misrouted into `unmapped`.",
    "Keep unmapped residuals only for values that truly have no mapping.",
    "Summarize any remaining risks or follow-ups before delivery.",
]

TASK_TYPES: tuple[str, ...] = tuple(_TASK_GUIDANCE.keys())
STYLE_LEVELS: tuple[str, ...] = tuple(_STYLE_GUIDANCE.keys())


def load_general_tql_base() -> str:
    """Return the core TQL workflow guidance text."""

    return _GENERAL_TQL_BASE


def get_task_specific_guidance(task_type: str) -> str:
    """Return task-specific guidance for the given task type."""

    return _TASK_GUIDANCE.get(task_type, "")


def get_style_guidance(style_level: str) -> str:
    """Return style guidance text for the requested level."""

    return _STYLE_GUIDANCE.get(style_level, "")
