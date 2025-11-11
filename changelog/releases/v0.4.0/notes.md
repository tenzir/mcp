## 💥 Breaking changes

### Refactor MCP tools

This release completely redesigns the MCP server with a comprehensive suite of tools that dramatically expand functionality beyond the original OCSF mapping capabilities. The MCP server now provides a complete development environment for working with Tenzir pipelines, OCSF schemas, and package management.

For detailed documentation, see https://docs.tenzir.com/reference/mcp-server.

**Pipeline Execution**:

- `run_pipeline`: Execute and validate TQL pipelines with automatic error detection and diagnostic output
- `run_test`: Run package test suites with baseline comparison and update capabilities

**Interactive Documentation**:

- `docs_read`: Access operator, function, and tutorial documentation with exact path navigation
- `docs_search`: Explore Tenzir concepts with keyword search, cross-reference traversal, and category filtering

**OCSF Schema Access**:

- `ocsf_get_versions`: List all available OCSF schema versions
- `ocsf_get_latest_version`: Retrieve the current stable OCSF version
- `ocsf_get_classes`: Browse available OCSF event classes by category
- `ocsf_get_class`: Get complete class schemas with field definitions
- `ocsf_get_object`: Access reusable object definitions for nested structures

**Package Management**:

- `package_create`: Initialize new package projects with standard structure
- `package_add_operator`: Create user-defined operators (UDOs) with automatic test scaffolding
- `package_add_test`: Add test cases with fixtures and baseline support
- `package_add_changelog`: Maintain structured changelog entries

**Code Generation**:

- `make_parser`: Generate TQL parsers from sample logs (JSON, CSV, syslog, key-value formats) with type inference and schema generation
- `make_ocsf_mapping`: Generate complete OCSF mapping packages with parser, transformation logic, and test suite

*By @mavam in [#11](https://github.com/tenzir/mcp/pull/11).*
