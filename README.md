# Tenzir MCP Server

[![PyPI](https://img.shields.io/pypi/v/tenzir-mcp.svg)](https://pypi.org/project/tenzir-mcp)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A [Model Context Protocol](https://modelcontextprotocol.io) server for
[Tenzir](https://tenzir.com) that enables AI assistants to interact with
security data pipelines.

## Installation

Quick install with uvx:

```sh
uvx --from tenzir-mcp tenzir-mcp
```

Or install with pip:

```sh
pip install tenzir-mcp
```

## Usage with Claude

### Claude Desktop

Add the server to your Claude Desktop app configuration:

```json
{
  "mcpServers": {
    "tenzir": {
      "command": "uvx",
      "args": ["--from", "tenzir-mcp", "tenzir-mcp"]
    }
  }
}
```

### Claude Code

Use the Claude MCP CLI to add the server:

```sh
# For production use (from PyPI)
claude mcp add tenzir --scope user -- uvx --from tenzir-mcp tenzir-mcp

# For development (from source)
claude mcp add tenzir --scope user -- uv run --project $(pwd) tenzir-mcp
```

Don't forget to restart Claude after making changes to the server.

## Configuration

```bash
# Optional: Set Tenzir node endpoint (default: http://localhost:5158)
export TENZIR_ENDPOINT=http://your-tenzir-node:5158

# Optional: Set API token if authentication is required
export TENZIR_API_TOKEN=your-api-token
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development setup.

## License

This project ships with an [Apache License 2.0](LICENSE).
