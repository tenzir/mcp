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

1. **server.py** - Main MCP server implementation using FastMCP
   - Defines all MCP tools as decorated async functions
   - Handles TQL pipeline execution and validation
   - Provides OCSF schema access and mapping tools

2. **docs.py** - Documentation management
   - TenzirDocs class for accessing embedded documentation
   - Supports .md, .mdx, and .mdoc formats

3. **data/** - Embedded data resources
   - `ocsf/` - OCSF schema JSON files for different versions
   - `docs/` - Tenzir documentation files

### MCP Tools

The server exposes these tools via the Model Context Protocol:

- `execute_tql_pipeline` - Execute TQL pipelines with optional input data
- `validate_tql_pipeline` - Validate pipeline syntax without execution
- `get_ocsf_versions` - List available OCSF schema versions
- `default_ocsf_version` - Get the latest stable OCSF version
- `get_ocsf_event_classes` - List OCSF event classes and descriptions
- `get_ocsf_class` - Get detailed OCSF class definition
- `get_ocsf_object` - Get OCSF object definition
- `ocsf_instructions_generic` - Get OCSF mapping guidelines
- `read_docs` - Access Tenzir documentation
- `ocsf_instructions` - Special instructions for OCSF mapping tasks

## Best Practices

- ALWAYS run `make check` before committing any changes.

## Important Notes

- Always run `make check` before committing to ensure code quality
- The server requires Tenzir to be installed for pipeline execution
- OCSF schemas are embedded in the package and updated via `make update-schemas`
- Documentation is embedded and updated via `make update-docs`
- The project uses uv for dependency management and virtual environments
- Python 3.10+ is required
