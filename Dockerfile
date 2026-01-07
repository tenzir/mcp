# Build stage: install dependencies for docs bootstrap
FROM node:22-slim AS docs-builder
RUN npm install -g pnpm@10
WORKDIR /build
# Install git, python, and build tools for node-gyp (tree-sitter-tql)
RUN apt-get update && apt-get install -y git python3 build-essential && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/tenzir/docs.git docs && \
    cd docs && \
    pnpm install --frozen-lockfile && \
    pnpm generate:excalidraw:placeholders || true && \
    LLMS_TXT=true pnpm build

# Python build stage
FROM python:3.12-slim AS python-builder
WORKDIR /build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY uv.lock pyproject.toml ./
COPY src src
COPY README.md LICENSE ./
# Copy built docs from docs-builder (bootstrap will skip download, just index)
COPY --from=docs-builder /build/docs/dist ./src/tenzir_mcp/data/docs
RUN uv sync --no-dev
# Bootstrap: docs already exist so only indexing runs, plus OCSF download
RUN uv run python -m tenzir_mcp.bootstrap
RUN uv build

# Final stage
FROM tenzir/tenzir
ENV TENZIR_BINARY=tenzir
COPY --from=python-builder /build/dist/*.whl /tmp/
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends python3-pip && \
    pip install --break-system-packages /tmp/*.whl && \
    rm -rf /var/lib/apt/lists/* /tmp/*.whl
USER tenzir
ENTRYPOINT ["tenzir-mcp"]
