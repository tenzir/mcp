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
- `make build-doc-index` - Build JSON documentation index
- `make build-doc-db` - Build SQLite FTS5 documentation database

### Utilities

- `make verify-install` - Verify package installation
- `make check-tenzir` - Check if Tenzir is installed
- `make test-search QUERY="your query"` - Test documentation search
- `make help` - Show all available commands

## Architecture

### Modular Structure

The server is organized into category-based modules:

1. **server.py** – Entry point that imports all tools and initializes FastMCP.
2. **prompts/** – System prompts for AI assistants.
   - **system.md** – Main system instructions loaded into FastMCP.
3. **tools/** – MCP tool implementations organized by category:
   - **execution/** – Pipeline and test execution tools.
   - **documentation/** – Documentation search and retrieval tools.
   - **ocsf/** – OCSF schema query tools.
   - **packaging/** – Package creation and management tools.
   - **coding/** – Code generation tools for parsers and OCSF mappings.
4. **docs.py** – Access utilities for the embedded documentation bundle.
5. **data/** – Embedded resources (`ocsf/` schemas, `docs/` content, `doc_index.json`).
6. **scripts/build_doc_index.py** – Generates the cross-linked documentation index.

### MCP Tools

#### Execution (🔴)

- `run_pipeline` – Execute a TQL pipeline using the local `tenzir` binary.
- `run_test` – Execute tenzir-test on a test file with optional passthrough/update modes.

#### Documentation (🟢)

- `docs_read` – Read documentation content from any path (including `/reference/operators`, `/reference/functions`).
- `docs_search` – Keyword search with See Also traversal across operators, functions, tutorials, and docs.

#### OCSF (🟡)

- `ocsf_get_versions` – List available OCSF schema versions.
- `ocsf_get_latest_version` – Return the latest stable OCSF version.
- `ocsf_get_classes` – Retrieve class names and descriptions for a schema version.
- `ocsf_get_class` – Return a specific OCSF class definition.
- `ocsf_get_object` – Return an OCSF object definition.

#### Packaging (🔵)

- `package_create` – Create a new package scaffold with interactive metadata elicitation.
- `package_add_operator` – Add a user-defined operator (UDO) to a package.
- `package_add_context` – Add a context entry to package.yaml.
- `package_add_test` – Add a test file with frontmatter and baseline.
- `package_add_changelog` – Add a changelog entry (breaking, change, bugfix, or feature).

#### Coding (⚪️)

- `make_parser` – Generate a TQL parser from sample log events (supports JSON, CSV, syslog, KV formats).
- `make_ocsf_mapping` – Generate a complete OCSF mapping package from sample events.

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
- Python 3.12+ is required
- FastMCP handles the MCP protocol implementation
