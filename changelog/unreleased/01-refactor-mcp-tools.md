---
title: Refactor MCP tools
type: breaking
authors:
- mavam
prs:
- 11
created: 2025-11-10
---

We relaunched all MCP tools. This breaking change dramatically expands the
previous MCP server functionality by supporting many more use cases. The
previous OCSF mapping use case is now part of the `make_ocsf_mapping` MCP tool.

Here is an overview of the new tools. For a comprehensive reference, check the
(new) docs at https://docs.tenzir.com/reference/mcp-server.

**Execution Tools**:

- `run_pipeline`: Execute TQL pipelines using a `tenzir` binary
  - Make adaptions to the pipeline based on error messages
  - Iterate until warnings are resolved

- `run_test`: Run package tests with tenzir-test
  - Use `passthrough=true` to see actual instead of diff-to-expected output
  - Use `update=true` only when explicitly requested to update baselines

**Documentation Tools**:

- `docs_read`: Primary tool for accessing documentation
  - Use exact paths: `reference/operators/name` or `reference/functions/name`
  - Read multiple related docs to understand context

- `docs_search`: learn about any concept in Tenzir
  - Use for exploration when unsure about a concept
  - Follow *See Also* links to build comprehensive understanding
  - Use category filters when appropriate.

**OCSF Tools**:

- `ocsf_get_versions`: List available schema versions
- `ocsf_get_latest_version`: Get current stable version (use this by default)
- `ocsf_get_classes`: Browse available event classes
- `ocsf_get_class`: Get detailed class schema before mapping
- `ocsf_get_object`: Get object definitions for complex types

**Package Management Tools**:

- `package_create`: Scaffold new packages with interactive prompts
- `package_add_operator`: Add user-defined operators (UDOs)
- `package_add_test`: Add test files with frontmatter
- `package_add_changelog`: Document changes properly

**Generation Tools**:

- `make_parser`: Generate TQL parsers from sample logs
  - Supports JSON, CSV, syslog, key-value formats
  - Requires samples for accurate parsing
  - Review and test generated parsers with `run_pipeline`

- `make_ocsf_mapping`: Generate complete OCSF mapping packages
  - Requires sample events and target OCSF class
  - Creates full package with parser, mapper, and tests
  - Always review generated mappings for correctness
