FROM tenzir/tenzir
ENV TENZIR_BINARY=tenzir
COPY uv.lock .
COPY pyproject.toml .
COPY src src
COPY README.md .
COPY LICENSE .
USER root
RUN uv sync --no-dev
RUN uv run python -m tenzir_mcp.bootstrap
RUN uv build
RUN uv pip install --system --break-system-packages dist/*.whl
USER tenzir
ENTRYPOINT ["tenzir-mcp"]
