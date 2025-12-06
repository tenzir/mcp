# ⚙️ Tenzir MCP Server

[![PyPI](https://img.shields.io/pypi/v/tenzir-mcp.svg)](https://pypi.org/project/tenzir-mcp)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that
enables AI assistants to interact with [Tenzir](https://tenzir.com)—a data
pipeline engine for security operations.

This MCP server provides tools for executing pipelines written in the [Tenzir
Query Language (TQL))](https://docs.tenzir.com/explanations/language), working
with Open Cybersecurity Schema Framework (OCSF), managing packages, generating parsers, and exploring documentation.

## ✨ Features

- **Pipeline Execution**: Run TQL pipelines and tests
- **Documentation Access**: Search and browse embedded Tenzir documentation with
  cross-reference support
- **OCSF Integration**: Query and work with OCSF definitions, event classes,
  objects, and profiles.
- **Package Management**: Create and manage Tenzir packages with operators,
  pipelines, enrichment contexts, and tests
- **Code Generation**: Auto-generate TQL parsers and OCSF mapping packages

## 📦 Installation

Use Docker as the fastest way to get started:

```bash
docker run -i tenzir/mcp
```

Or use [`uvx`](https://docs.astral.sh/uv/) when you have a local Tenzir
installation:

```bash
uvx tenzir-mcp
```

## 📚 Documentation

Consult our [setup guide](https://docs.tenzir.com/guides/mcp-usage/install-mcp-server)
for installation and MCP client configuration.

We also provide a [reference](https://docs.tenzir.com/reference/mcp-server) that
explains usage and available tools.

## 🤝 Contributing

Want to contribute? We're all-in on agentic coding with [Claude
Code](https://claude.ai/code)! The repo comes pre-configured with our [custom
plugins](https://github.com/tenzir/claude-plugins)—just clone and start hacking.

## 📜 License

This project is licensed under the [Apache License 2.0](LICENSE).
