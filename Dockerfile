FROM tenzir/tenzir
COPY uv.lock .
COPY pyproject.toml .
COPY scripts scripts
COPY src src
COPY README.md .
COPY LICENSE .
USER root
RUN uv build
USER tenzir
ENTRYPOINT ["tenzir-mcp"]
