.PHONY: help install install-dev test test-cov lint format type-check clean build upload

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=src/tenzir_mcp --cov-report=term-missing --cov-report=html

lint:  ## Run linting
	ruff check src/ tests/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

type-check:  ## Run type checking
	mypy src/

quality-check: lint type-check  ## Run all quality checks

fix:  ## Fix formatting and linting issues
	black src/ tests/
	isort src/ tests/
	ruff check --fix src/ tests/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build the package
	python -m build

upload:  ## Upload to PyPI (requires build first)
	python -m twine upload dist/*

dev-setup: install-dev  ## Complete development setup
	pre-commit install || echo "pre-commit not available"

run-server:  ## Run the MCP server
	python -m tenzir_mcp.server

check-tenzir:  ## Check if Tenzir is available
	tenzir --version || echo "Tenzir not found in PATH"