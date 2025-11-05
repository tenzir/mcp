# Tenzir MCP Server

[![PyPI](https://img.shields.io/pypi/v/tenzir-mcp.svg)](https://pypi.org/project/tenzir-mcp)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
enables AI assistants to interact with [Tenzir](https://tenzir.com)—a data
pipeline engine for security operations. This server provides tools for
executing TQL pipelines, working with OCSF schemas, managing packages,
generating parsers, and exploring documentation.

For complete documentation, see the [official
reference](https://docs.tenzir.com/reference/mcp-server).

## Features

- **Pipeline Execution**: Run TQL (Tenzir Query Language) pipelines and tests
- **Documentation Access**: Search and browse embedded Tenzir documentation with
  cross-reference support
- **OCSF Integration**: Query and work with Open Cybersecurity Schema Framework
  definitions
- **Package Management**: Create and manage Tenzir packages with operators,
  contexts, and tests
- **Code Generation**: Auto-generate TQL parsers and OCSF mapping packages from
  sample data

## Getting Started

### Using Docker

The fastest way to get started:

```bash
docker run -i tenzir/mcp
```

### Using uvx

```bash
uvx tenzir-mcp
```

> [!TIP]
> For detailed setup instructions and various MCP client configurations, see the
> [official
  documentation](https://docs.tenzir.com/guides/mcp-setup/install-mcp-server).

## Available Tools

The MCP server exposes the following tools, organized by category:

### Execution

- `run_pipeline` – Execute a TQL pipeline using the local `tenzir` binary
- `run_test` – Run tenzir-test on test selections with passthrough/update modes

### Documentation

- `docs_read` – Read documentation content from any path (operators,
  functions, tutorials)
- `docs_search` – Search documentation with keyword matching and
  cross-reference traversal

### OCSF Schema

- `ocsf_get_versions` – List available OCSF schema versions
- `ocsf_get_latest_version` – Get the latest stable OCSF version
- `ocsf_get_classes` – Retrieve class names and descriptions for a schema
  version
- `ocsf_get_class` – Get a specific OCSF class definition
- `ocsf_get_object` – Get an OCSF object definition

### Package Management

- `package_create` – Create a new package scaffold with interactive metadata
  prompts
- `package_add_operator` – Add a user-defined operator (UDO) to a package
- `package_add_context` – Add a context entry to package.yaml
- `package_add_test` – Add a test file with frontmatter and baseline
- `package_add_changelog` – Add a changelog entry (breaking, change, bugfix,
  or feature)

### Code Generation

- `make_parser` – Generate TQL parsers from sample log events (JSON, CSV,
  syslog, KV)
- `make_ocsf_mapping` – Generate complete OCSF mapping packages from sample
  events

## Requirements

- Python 3.12 or higher
- [Tenzir](https://tenzir.com) installed and available in PATH (for pipeline
  execution)

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup, testing, and
contributing guidelines.

## License

This project is licensed under the [Apache License 2.0](LICENSE).
