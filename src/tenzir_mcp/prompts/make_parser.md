# Create a TQL parsing pipeline

You MUST follow the following phases in EXACT order.

## Phase 1: Input Schema Analysis

**Objective**:

Learn about the input data and understand its structure.

**Steps**:

1. Identify the data source format (CSV, JSON, YAML, etc.)
2. Identify vendor and product that may have generated this data.
3. Document the complete input schema in terms of fields and types

You MUST state "Phase 1 complete" before proceeding.

## Phase 2: Package Scaffolding

**Objective**:

Create package for the parser that you can build and test incrementaly in the
next phase.

**Prerequisites**: (read with `read_docs` once per session)

- explanations/packages
- reference/test-framework
- guides/testing/write-tests

**Steps**:

0. Choose a suitable ID for the package consisting of the vendor and product
   name, e.g., `fortinet`, `cisco`, `microsoft`. In the instructions, below
   replace `pkg` with the name you chose.
1. Use the `package_create` tool to create a package structure for the new
   parser. For the `package_dir` parameter, use the chosen package ID.
2. Use the `package_add_operator` tool to create a new operator called `parse`.
   The sole responsibility of this operator is to convert the input into the
   most structured and type representation possible.
   - Pass as `code` just `read_lines`.
3. Use the `package_add_test` operator to add a test.
   - Pass as `test_file` parameter the `parse.tql`
   - Pass as `input` parameter the log sample(s)
   - Pass as `test` parameter the TQL code that reads the input file:
     ```tql
     from_file f"{env("TENZIR_INPUTS")}/sample.log" {
       pkg::parse
     }
     ```
     NB:
     - If the log sample has a known format, such as JSON or CSV, use an
       appropriate file extension, e.g., `sample.json` or `sample.csv` instead of
       `sample.log`.
4. Use the `run_test` tool to execute the test, with `update` enabled, to
   produce an initial baseline.

You MUST state "Phase 2 complete" before proceeding.

## Phase 3: Iterate & Test

**Prerequisites**: (read with `read_docs` once per session)

- guides/data-shaping/transform-basic-values/
- guides/data-shaping/extract-structured-data-from-text/
- guides/data-shaping/convert-data-formats/
- guides/data-shaping/reshape-complex-data/

**Objective**:

Loop with the `run_test` tool until the package has all fields parsed and
properly typed. (Do NOT use the `run_pipeline` to execute pipelines during
package development, as this tool does not have the necessary package context.)

**Steps**:

1. Make ONE modification of the `parse` operator to handle additional fields.
   Typical actions include:
   - **Date & time parsing**: Do not keep dates and times as timestamps, but
     rather parse them as type `time` or `duration`. keeping a broad type type
     like `string`.
   - **IP addresses**: TQL has first-class IP address types; an `ip` literal has
     the form `1.2.3.4` as opposed to `"1.2.3.4"`. Ensure that all IP addresses
     are parsed as type `ip`.
   - **Subnets**: TQL has first-class subnet types; a `subnet` literal has
     the form `10.0.0.0/8` as opposed to `"10.0.0.0/8"`. Ensure that all
     CIDR subnets are parsed as `subnet` type.
   - **Strings**: Clean string artifacts with the `trim` function.
   - **Lists**: Parse comma-separated values surrounded by brackets as lists.
   - **Nested structures**: Parse nested structures using the `parse_*`
     functions according to the value format.
   - **Sentinel values**: Use the `replace` operator to normalize sentinel
     values, such as:
     ```tql
     replace what="None", with=null
     replace what="N/A", with=null
     replace fieldname, what="NO", with=false
     ```
2. Re-run `run_test` and observe the output diff.
3. If the diff looks good, call `run_test` with `update` enabled.
4. Go back to Step 1 and continue with the next modification.

You MUST state "Phase 3 complete" before proceeding.

## Phase 4: Bootstrap Sampling

**Objective**:

Create additional input samples to expand test coverage and test robustness of
the parser.

**Steps**:

1. Synthesize at least 3 sample input records based on the identified input fields.
2. Add the synthetic data to the package inputs, as separate file with a
   `-synthetic` suffix, but otherwise identical name to the original input.
3. Repeat Phase 3.

## Phase 5: Summarize

Provide a final summary of the parser's functionality. Include:

- Input
- TQL to parse the input
- Output
- Package structure (in tree format)
- Noteworthy findings
