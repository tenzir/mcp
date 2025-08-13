# Development Guide

## Quick Start

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Running from Source

There are several ways to run the MCP server from the source tree:

#### Method 1: Using uvx with local path (Quickest for testing)

```bash
# From anywhere, point to your local development directory
uvx --from /path/to/tenzir-mcp tenzir-mcp --help

# Or from within the project directory
uvx --from . tenzir-mcp --help
```

#### Method 2: Using uv run (Recommended for development)

```bash
# From the project root directory
uv run tenzir-mcp

# Or run the module directly
uv run python -m tenzir_mcp.server

# With environment variables
TENZIR_ENDPOINT=http://localhost:5158 uv run tenzir-mcp
```

#### Method 3: Install in editable mode

```bash
# Create a virtual environment
uv venv

# Activate it
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package in editable/development mode
uv pip install -e ".[dev]"

# Now you can use the command directly
tenzir-mcp --help
```

#### Method 4: Direct Python execution

```bash
# Make sure dependencies are installed
uv pip install fastmcp pydantic httpx python-dotenv

# Run directly
python src/tenzir_mcp/server.py
```

## Development Workflow

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/tenzir/mcp
cd mcp

# Create a virtual environment (optional, uv handles this automatically)
uv venv

# Install with development dependencies
uv pip install -e ".[dev]"
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with black
uv run black src/ tests/

# Check formatting (no changes)
uv run black --check src/ tests/

# Sort imports with isort
uv run isort src/ tests/

# Lint code with ruff
uv run ruff check src/ tests/

# Fix linting issues automatically
uv run ruff check --fix src/ tests/

# Type checking with mypy
uv run mypy src/

# Run all checks at once
make lint
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=tenzir_mcp --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=tenzir_mcp --cov-report=html
open htmlcov/index.html  # View the report

# Run specific test file
uv run pytest tests/test_server.py

# Run tests matching a pattern
uv run pytest -k "test_pipeline"

# Run with verbose output
uv run pytest -v

# Run tests in parallel (faster)
uv run pytest -n auto

# Run only fast tests (skip slow/integration tests)
uv run pytest -m "not slow"
```

### Building the Package

```bash
# Build distributions (wheel and sdist)
uv build

# Check the built files
ls -la dist/

# Verify the wheel contents
unzip -l dist/*.whl
```

### Testing the Built Package

```bash
# Create a test virtual environment
uv venv test-env
source test-env/bin/activate

# Install the built wheel
uv pip install dist/tenzir_mcp-*.whl

# Test it works
tenzir-mcp --help

# Test with uvx
uvx --from dist/tenzir_mcp-*.whl tenzir-mcp --help

# Clean up
deactivate
rm -rf test-env
```

## Making Changes

### Adding Dependencies

1. Add runtime dependencies to `pyproject.toml` under `[project.dependencies]`
2. Add development dependencies under `[project.optional-dependencies.dev]`
3. Update the lock file: `uv lock`

### Updating OCSF Schemas

Download latest OCSF schemas:

```sh
uv run python scripts/download-ocsf-schemas.py
```

Verify the downloaded schemas in `src/tenzir_mcp/data/ocsf/`.

### Adding New MCP Tools

1. Create a new tool in `src/tenzir_mcp/tools/`
2. Import and register it in `src/tenzir_mcp/server.py`
3. Add tests in `tests/test_<tool_name>.py`
4. Update documentation in README.md

## Debugging

### Enable Debug Logging

```bash
# Set debug environment variable
export DEBUG=1
export LOG_LEVEL=DEBUG

# Run with debug output
uv run tenzir-mcp
```

### Using VS Code

1. Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug MCP Server",
      "type": "python",
      "request": "launch",
      "module": "tenzir_mcp.server",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "DEBUG": "1"
      }
    }
  ]
}
```

2. Set breakpoints in the code
3. Press F5 to start debugging

### Common Issues

#### Import errors

```bash
# Ensure src is in PYTHONPATH
export PYTHONPATH=src:$PYTHONPATH
```

#### Missing dependencies

```bash
# Reinstall all dependencies
uv pip install -e ".[dev]" --force-reinstall
```

#### Type checking errors

```bash
# Install type stubs
uv pip install types-requests types-pyyaml
```

## Testing with Claude Desktop

### Local Development Setup

1. Build and install locally:
```bash
uv build
uv tool install --from dist/tenzir_mcp-*.whl tenzir-mcp
```

2. Configure Claude Desktop:
```json
{
  "mcpServers": {
    "tenzir-dev": {
      "command": "/path/to/.local/bin/tenzir-mcp"
    }
  }
}
```

3. Restart Claude Desktop to load changes

### Live Reload Development

For rapid iteration:

1. Use the source directly:
```json
{
  "mcpServers": {
    "tenzir-dev": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/mcp", "tenzir-mcp"]
    }
  }
}
```

2. Make changes to the source
3. Restart Claude Desktop to reload
