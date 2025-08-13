# Tenzir MCP Server

[![PyPI](https://img.shields.io/pypi/v/tenzir-mcp.svg)](https://pypi.org/project/tenzir-mcp)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A [Model Context Protocol](https://modelcontextprotocol.io) server for
[Tenzir](https://tenzir.com) that enables AI assistants to interact with
security data pipelines and map data to the [Open Cybersecurity Schema
Framework (OCSF)](https://ocsf.io).

## Installation

### Prerequisites

The MCP server requires [Tenzir](https://tenzir.com) to be installed and available in your `$PATH`:

```sh
# Check if Tenzir is installed
tenzir --version
```

If not installed, follow the
[documentation](https://docs.tenzir.com/guides/node-setup/deploy-a-node) or just
run:

```sh
curl https://get.tenzir.app | sh
```

### Quick Test

Run without installation:

```sh
uv tool run tenzir-mcp --help
```

## Usage with Claude

### Claude Desktop

Add the server to your Claude Desktop app configuration:

```json
{
  "mcpServers": {
    "tenzir": {
      "command": "uv",
      "args": ["tool", "run", "tenzir-mcp"]
    }
  }
}
```

### Claude Code

Use the Claude MCP CLI to add the server:

```sh
# For production use (from PyPI)
claude mcp add tenzir --scope user -- uv tool run tenzir-mcp

# For development (from source)
claude mcp add tenzir --scope user -- uv run --project $(pwd) tenzir-mcp
```

Don't forget to restart Claude after making changes to the server.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup.

## License

This project ships with an [Apache License 2.0](LICENSE).
