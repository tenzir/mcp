"""Workflow guidance for building OCSF mappings."""

from __future__ import annotations

from textwrap import dedent
from typing import Any

from tenzir_mcp.app import mcp

__all__ = ["workflow_ocsf_mapping"]

_OCSF_BASE_INSTRUCTIONS = dedent(
    """
    CRITICAL: You MUST follow these phases in EXACT order. Do NOT proceed to the next phase until the current one is COMPLETE, DOCUMENTED, and VERIFIED.

    PHASE 0: Requirements Analysis (MANDATORY)
    - MANDATORY: Document the complete task requirements and constraints
    - REQUIRED OUTPUT: Write a structured analysis of what needs to be accomplished
    - REQUIRED: Identify the data source format, target schema, and key transformation requirements
    - BLOCKING: You MUST state "PHASE 0 COMPLETE" before proceeding

    PHASE 1: Input Schema Analysis (MANDATORY)
    - MANDATORY: Document the complete input schema before any coding
    - REQUIRED OUTPUT: Write a structured description of all input fields and formats
    - REQUIRED: Provide at least 3 sample input records with field-by-field breakdown
    - BLOCKING: You MUST state "PHASE 1 COMPLETE" before proceeding

    PHASE 2: Approach Exploration (MANDATORY NEW PHASE)
    - MANDATORY: Survey at least 3 different technical approaches for the task
    - REQUIRED: For parsing tasks, explore operators like read_grok, read_syslog, read_lines+parsing, from_file
    - REQUIRED: Execute small test samples (3-5 records) of each approach
    - REQUIRED: Document trade-offs, performance, and complexity of each approach
    - REQUIRED: Justify chosen approach with specific reasons
    - BLOCKING: You MUST state "PHASE 2 COMPLETE" with chosen approach before proceeding

    PHASE 3: Documentation Review (BLOCKING REQUIREMENT)
    - MANDATORY: Create complete checklist of ALL operators and functions you will use
    - FOR EACH item on checklist:
      - FIRST: Read its documentation using docs_read tool
      - THEN: Document its syntax, parameters, and usage notes
      - MARK: Check off the item on your checklist
    - VIOLATION CHECK: Using ANY operator/function not on pre-approved checklist requires IMMEDIATE restart of Phase 3
    - VERIFICATION: Show completed checklist with all items checked
    - BLOCKING: You MUST state "PHASE 3 COMPLETE" with verified checklist before proceeding

    PHASE 4: Incremental Pipeline Construction (MANDATORY)
    - CHUNK RULE: Write pipeline in chunks of maximum 5 operators
    - MANDATORY EXECUTION: Execute and verify each chunk before adding more
    - REQUIRED TEST POINTS:
      * Chunk 1: Data input + initial parsing (MUST EXECUTE)
      * Chunk 2: + core transformations (MUST EXECUTE)
      * Chunk 3: + classification/mapping (MUST EXECUTE)
      * Chunk 4: + final formatting (MUST EXECUTE)
    - REQUIRED: Document schema changes at each step
    - REQUIRED: Fix any issues before proceeding to next chunk
    - VERIFICATION: Show execution results for each chunk
    - BLOCKING: You MUST state "PHASE 4 COMPLETE" with all chunk verifications before proceeding

    PHASE 5: Style Guide Compliance (NON-NEGOTIABLE)
    - MANDATORY: Read tutorials/learn-idiomatic-tql BEFORE any style changes
    - REQUIRED: Explicitly check EVERY line against style guide rules
    - REQUIRED: List specific style guide rules you applied
    - REQUIRED: Preserve all meaningful comments (especially OCSF attribute groups, business logic explanations)
    - BLOCKING: You MUST state "PHASE 5 COMPLETE" with style compliance verification before proceeding

    PHASE 6: Integration Testing (MANDATORY NEW PHASE)
    - MANDATORY: Execute complete pipeline on representative sample (minimum 10 records)
    - REQUIRED: Test edge cases (malformed data, missing fields, unusual values)
    - REQUIRED: Verify output schema compliance
    - REQUIRED: Document any limitations or known issues
    - BLOCKING: You MUST state "PHASE 6 COMPLETE" with test results before proceeding

    PHASE 7: Critical Analysis (MANDATORY FINAL STEP)
    - REQUIRED: List at least 3 potential improvements with specific implementation suggestions
    - REQUIRED: Identify any performance concerns with proposed solutions
    - REQUIRED: Note any error handling gaps with recommended fixes
    - REQUIRED: Suggest alternative approaches that could be more efficient
    - BLOCKING: You MUST state "PHASE 7 COMPLETE" when finished

    ENFORCEMENT MECHANISMS:
    - TodoWrite tool MUST be used to track each phase completion
    - After each phase, EXPLICITLY STATE: "PHASE X COMPLETE" with verification
    - If you proceed without completing a phase, IMMEDIATELY STOP and restart that phase
    - Each BLOCKING requirement must be satisfied before proceeding
    - Violations of any MANDATORY requirement trigger immediate restart of that phase

    VERIFICATION REQUIREMENTS:
    - Each phase must produce specific deliverables as listed
    - All execution requirements must show actual results
    - All documentation requirements must be explicitly shown
    - Cannot proceed to next phase without stating "PHASE X COMPLETE"

    IMPORTANT DOCUMENTATION PATHS (MUST READ BEFORE USING):
    - tutorials/map-data-to-ocsf => OCSF mapping patterns (MANDATORY for OCSF tasks)
    - reference/operators/* => Individual operator docs (MANDATORY READ in Phase 3)
    - reference/functions/* => Individual function docs (MANDATORY READ in Phase 3)

    CRITICAL NOTES:
    - Comments explaining business logic, domain mappings, and non-obvious decisions are MANDATORY
    - Incremental execution is NON-NEGOTIABLE - cannot build entire pipeline then test
    - Operator/function documentation must be read BEFORE first use, not after encountering errors
    - Alternative approach exploration is REQUIRED to ensure optimal solution
    """
).strip()


def _load_ocsf_base_instructions() -> str:
    """Return the unmodified OCSF workflow instructions."""

    return _OCSF_BASE_INSTRUCTIONS


def _add_beginner_guidance(instructions: str) -> str:
    """Add beginner-friendly guidance."""

    tips = dedent(
        """

        BEGINNER SUPPORT:
        - Keep checkpoints short and explicit; list questions you still need answered.
        - When exploring operators, run `docs_search` to gather candidates before deep-diving.
        - Record every execution command you run so you can repeat or adjust quickly.
        """
    ).rstrip()
    return f"{instructions}\n{tips}"


def _add_detailed_examples(instructions: str) -> str:
    """Add requirements for deeper documentation references and validation."""

    addendum = dedent(
        """

        DETAILED MODE:
        - Provide concrete before/after record examples for each chunk in Phase 4.
        - Cross-reference the exact documentation snippets that justify every operator/function choice.
        - Capture timing metrics or resource notes during Phase 6 to baseline performance.
        """
    ).rstrip()
    return f"{instructions}\n{addendum}"


@mcp.tool(name="workflow_ocsf_mapping", tags={"ocsf", "workflow", "tql"})
async def workflow_ocsf_mapping(
    version: str = "1.6.0",
    target_class: str | None = None,
    complexity: str = "standard",
) -> dict[str, Any]:
    """Structured workflow for mapping data to OCSF."""

    instructions = _load_ocsf_base_instructions()
    warnings: list[str] = []

    if target_class:
        target_section = dedent(
            f"""

            TARGET CLASS CONTEXT:
            - Focus on OCSF class `{target_class}` using schema `{version}`.
            - Use `ocsf_get_class("{version}", "{target_class}")` and `ocsf_get_object("{version}", "...")` for precise field definitions.
            - Verify enumerations and optional fields before implementation.
            """
        ).rstrip()
        instructions = f"{instructions}\n{target_section}"

    complexity_lower = complexity.lower()
    if complexity_lower == "beginner":
        instructions = _add_beginner_guidance(instructions)
    elif complexity_lower == "detailed":
        instructions = _add_detailed_examples(instructions)
    elif complexity_lower != "standard":
        warnings.append(
            f"Unsupported complexity '{complexity}'. Using standard workflow."
        )

    return {
        "instructions": instructions.strip(),
        "version": version,
        "target_class": target_class,
        "complexity": (
            complexity_lower
            if complexity_lower in {"standard", "beginner", "detailed"}
            else "standard"
        ),
        "warnings": warnings,
    }
