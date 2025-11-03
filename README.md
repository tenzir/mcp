# Tenzir MCP Server

[![PyPI](https://img.shields.io/pypi/v/tenzir-mcp.svg)](https://pypi.org/project/tenzir-mcp)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A [Model Context Protocol](https://modelcontextprotocol.io) server for
[Tenzir](https://tenzir.com) that enables AI agents to interact with
Tenzir.

### Getting started

The fastest way to get started is using Docker:

```sh
docker run -i tenzir/mcp
```

> [!TIP]
> For detailed setup instructions, see the [official documentation](https://docs.tenzir.com/guides/mcp-setup/install-mcp-server).

## Available Tools

The server registers the following MCP tools:

- Workflow guidance: `workflow_tql_authoring`, `workflow_ocsf_mapping`, `workflow_tql_completion`
- Documentation discovery: `docs_read`, `docs_list_operators`, `docs_list_functions`, `docs_search`
- Execution & schemas: `pipeline_execute`, `ocsf_get_versions`, `ocsf_get_latest_version`, `ocsf_get_classes`, `ocsf_get_class`, `ocsf_get_object`

Each workflow tool returns structured instructions so agents can follow best practices, while the discovery tools expose a cross-linked index of the bundled Tenzir documentation. Use `docs_search` with the `depth` parameter to explore See Also relationships without making additional calls.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup.

## License

This project ships with an [Apache License 2.0](LICENSE).
