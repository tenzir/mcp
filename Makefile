.PHONY: help install install-dev test test-cov lint format type-check clean build

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package with uv
	uv pip install -e .

install-dev:  ## Install with development dependencies
	uv pip install -e ".[dev]"

test:  ## Run tests
	uv run pytest

test-cov:  ## Run tests with coverage
	uv run pytest --cov=tenzir_mcp --cov-report=term-missing --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-watch:  ## Run tests in watch mode
	uv run pytest-watch

lint:  ## Run linting checks
	uv run ruff check src/ tests/

format:  ## Format code with black and isort
	uv run black src/ tests/
	uv run isort src/ tests/

format-check:  ## Check code formatting
	uv run black --check src/ tests/
	uv run isort --check-only src/ tests/

type-check:  ## Run type checking with mypy
	uv run mypy src/

check: format-check lint type-check test  ## Run all checks

fix:  ## Auto-fix formatting and linting issues
	uv run black src/ tests/
	uv run isort src/ tests/
	uv run ruff check --fix src/ tests/

clean:  ## Clean all build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
	rm -rf .coverage htmlcov/ coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean  ## Build distribution packages
	uv build
	@echo "Built packages:"
	@ls -la dist/

publish: check build  ## Publish to PyPI (run checks first)
	@echo "Publishing to PyPI..."
	uv publish

dev:  ## Run development server
	uv run tenzir-mcp

dev-module:  ## Run as Python module
	uv run python -m tenzir_mcp.server

verify-install:  ## Verify package installation with uv tool run
	uv tool run tenzir-mcp --help

update-schemas:  ## Update OCSF schemas
	uv run python scripts/download-ocsf-schemas.py

update-docs:  ## Update Tenzir documentation
	uv run python scripts/download-docs.py

check-tenzir:  ## Check if Tenzir is available
	tenzir --version || echo "Tenzir not found in PATH"

# Docker commands
docker-up:  ## Start Tenzir using Docker Compose
	docker-compose up -d

docker-down:  ## Stop Tenzir Docker containers
	docker-compose down

docker-dev:  ## Start Tenzir development container
	docker-compose --profile dev up -d

docker-logs:  ## Show Tenzir container logs
	docker-compose logs -f tenzir

docker-status:  ## Check Docker container status
	docker-compose ps

check-tenzir-docker:  ## Check if Tenzir is available in Docker
	docker exec tenzir-server tenzir version || echo "Tenzir Docker container not running"

dev-docker:  ## Run development server with Docker configuration
	cp .env.docker .env && uv run tenzir-mcp

dev-local:  ## Run development server with local configuration
	cp .env.local .env && uv run tenzir-mcp