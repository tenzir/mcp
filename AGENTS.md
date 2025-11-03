# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Model Context Protocol (MCP) server for Tenzir that enables AI
assistants to interact with security data pipelines and map data to the Open
Cybersecurity Schema Framework (OCSF). The server is built using FastMCP and
provides tools for executing TQL (Tenzir Query Language) pipelines and working
with OCSF schemas.

## Prerequisites

Tenzir must be installed and available in the PATH. Check with:

```bash
make check-tenzir
```

## Common Development Commands

Use these Makefile targets for development:

### Setup and Installation

- `make install-dev` - Install with development dependencies
- `make install` - Install the package without dev dependencies

### Development and Testing

- `make dev` - Run the development server
- `make dev-module` - Run as Python module
- `make test` - Run all tests
- `make test-cov` - Run tests with coverage report

### Code Quality

- `make lint` - Run linting checks (ruff)
- `make fix` - Auto-fix formatting and linting issues
- `make format` - Format code with black and isort
- `make format-check` - Check code formatting without changes
- `make type-check` - Run type checking with mypy
- `make check` - Run ALL checks (format, lint, type-check, test)

### Building and Publishing

- `make build` - Build distribution packages (cleans first)
- `make publish` - Publish to PyPI (runs all checks first)
- `make clean` - Clean all build artifacts

### Data Updates

- `make update-schemas` - Update OCSF schemas
- `make update-docs` - Update Tenzir documentation

### Utilities

- `make verify-install` - Verify package installation
- `make help` - Show all available commands

## Architecture

### Core Components

1. **app.py** – Exposes the shared `FastMCP` application instance used across modules.
2. **server.py** – Main MCP server implementation.
   - Hosts execution, schema, and documentation tools.
   - Loads the documentation index generated at build time.
3. **workflows/** – Modular workflow tools (`general_tql`, `ocsf_mapping`, etc.).
4. **docs.py** – Access utilities for the embedded documentation bundle.
5. **data/** – Embedded resources (`ocsf/` schemas, `docs/` content, `doc_index.json`).
6. **scripts/build_doc_index.py** – Generates the cross-linked documentation index consumed by the MCP tools.

### MCP Tools

#### Workflow Guidance
- `workflow_tql_authoring` – Parameterized guidance for common TQL authoring scenarios.
- `workflow_ocsf_mapping` – Seven-phase workflow for building OCSF mappings with optional specialization.
- `workflow_tql_completion` – Post-completion validation checklist for TQL work.

#### Documentation Discovery
- `docs_read` – Fetch documentation content along with resolved metadata.
- `docs_list_operators` – List operator metadata with category filters and See Also links.
- `docs_list_functions` – List function metadata with category filters and See Also links.
- `docs_search` – Keyword search across operators, functions, tutorials, and general docs; set `depth` to traverse See Also links or pass `paths` to start from specific pages.

#### Execution & Schemas
- `pipeline_execute` – Execute a TQL pipeline using the local `tenzir` binary.
- `ocsf_get_versions` – List available OCSF schema versions.
- `ocsf_get_latest_version` – Return the latest stable OCSF version.
- `ocsf_get_classes` – Retrieve class names and descriptions for a schema version.
- `ocsf_get_class` – Return a specific OCSF class definition.
- `ocsf_get_object` – Return an OCSF object definition.

## Best Practices

- CRITICAL: ALWAYS run `make check` before committing any changes.
- Regenerate the documentation index (`make build-doc-index`) whenever the bundled docs change.
- All MCP tools return structured error dictionaries for consistent error handling.
- Use async/await patterns consistently throughout the codebase.
- Follow strict type hints (mypy with strict settings enforced).

## Important Notes

- Always run `make check` before committing to ensure code quality
- The server requires Tenzir to be installed for pipeline execution
- OCSF schemas are embedded in the package and updated via `make update-schemas`
- Documentation is embedded and updated via `make update-docs`
- The project uses uv for dependency management and virtual environments
- Python 3.10+ is required
- FastMCP handles the MCP protocol implementation
