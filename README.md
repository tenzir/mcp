# Tenzir MCP Server

A FastMCP server that provides integration with Tenzir data pipelines through the Model Context Protocol.

## Development

### Installation

Run the following in this directory:

```bash
claude mcp add tenzir --scope user -- uv run --project $(pwd) tenzir-mcp
```

Don't forget to restart Claude when you make changes to the server.


### Code formatting and linting

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Running tests

```bash
pytest
```

### Running tests with coverage

```bash
pytest --cov=src/tenzir_mcp --cov-report=html
```
