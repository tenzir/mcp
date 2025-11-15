# Add OCSF mapping to a TQL parsing pipeline

You MUST follow the following phases in EXACT order.

## Phase 0: Create Parser Package

Use the `make_parser` tool to create a parser package that transforms raw log
data into structured events. Complete all phases of the parser creation before
proceeding with OCSF mapping.

Note the package directory and identifier for the next phase.

You MUST state "Phase 0 complete" before proceeding.

## Phase 1: OCSF Target Analysis

**Steps**:

1. Examine the parsed data schema (from the `parse` operator output) to
   understand available fields in the to-be-mapped event(s).
2. You may use the `ocsf_get_latest_version` tool to determine the current OCSF
   version.
3. Use the `ocsf_get_classes` tool to list all available OCSF event classes to
   identify the most appropriate OCSF event class based on the data type (e.g.,
   Network Activity, File Activity, Authentication, System Activity). Do not map
   to a deprecated class!
4. Document which OCSF attribute groups will be populated (i.e., Classification,
   Occurence, Context, Primary). For each attribute group, list the fields that
   you will populate.
5. Identify needed profiles to achieve mapping completeness (e.g., Host, OSINT,
   Security Control)
6. Note any gaps in the source data for populating OCSF fields

You MUST state "Phase 1 complete" before proceeding.

## Phase 2: OCSF Mapping Operator

**Prerequisites**: (read with `read_docs` once per session)

- tutorials/map-data-to-ocsf/

**Steps**:

Let `pkg` be the package ID that you chose in Phase 1.

1. Use the `package_add_operator` tool to create a new operator called
   `pkg::ocsf::X` where `X` is the event/log type, e.g., `proxy`, `flow`,
   `process`.
2. Write TQL code that transforms the parsed data into OCSF format:
   - Go through every attribute group, exactly as in the tutorial, and segment
     the TQL code into the following sections with clear comments:
     1. Preamble
     2. OCSF Attribute groups
        1. Classification
        2. Occurrence
        3. Context
        4. Primary
        5. Profiles
     3. Epilogue
   - Each section should start with a comment like this, surrounded by an empty
     newline on each side:
     ```tql
     // --- Preamble ---------------------------------
     // --- OCSF: Classification ---------------------
     // --- OCSF: Occurrence -------------------------
     // --- OCSF: Context ----------------------------
     // --- OCSF: Primary ----------------------------
     // --- OCSF: Profile: Host ----------------------
     // ...
     // --- OCSF: Profile: OSINT ---------------------
     // --- Epilogue ---------------------------------
     ```
   - Populate all required OCSF fields
   - Take particular note of the OCSF `metadata` object:
     - `log_name`: Populate only when unambiguous statically or when in data
     - `product`: Populate from the log or fill statically
     - `uid`: Attempt to extract a unique event ID from the data
   - Add comments explaining non-obvious field mappings
3. Use the `package_add_operator` tool to add the TQL code for the OCSF mapping:
   - Pass as `name` parameter `ocsf::X`
   - Set `no_tests` to True
4. Use the `package_add_test` tool to add the TQL code for the OCSF mapping:
   - Pass as `test_file` parameter `ocsf/X.tql`
   - Pass as `input` parameter sample parsed events (same as in make_parser)
   - Pass as `test` parameter the following TQL code:
     ```tql
     from_file f"{env("TENZIR_INPUTS")}/sample.json" {
       pkg::ocsf::parse
     }
     pkg::ocsf::X
     ocsf::cast
     ```
     NB:
     - `pkg::ocsf::parse` was previously created via the `make_parser` tool.
     - If the log sample has a known format, such as JSON or CSV, use an
       appropriate file extension, e.g., `sample.json` or `sample.csv` instead of
       `sample.log`.
5. From here, loop with the `run_test` tool to execute the test until the
   following conditions are met:
   - All warnings are gone. Note that we added `ocsf::cast` at the end of the
     test, which validates that the output is proper OCSF and emits a warning on
     schema mismatch.
6. Perform an `unmapped` loop that attempts to remove as much fields as possible
   from the `unmapped` field:
   - If need be, try adding a profile.

You MUST state "Phase 2 complete" before proceeding.

## Phase 3: Summarize

Provide a final summary of the complete parser with OCSF mapping. Include:

- Package name and structure (in tree format)
- Parser functionality overview
- Target OCSF class and version
- OCSF attribute groups populated
- OCSF profiles used
- Field mapping overview (source → parsed → OCSF)
- Sample input (raw log)
- Sample intermediate (parsed data)
- Sample output (OCSF data)
- Any limitations or missing OCSF fields, highlighting `unmapped` fields
