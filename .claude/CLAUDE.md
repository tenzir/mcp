# Repository Architecture

This document describes the architecture of `tenzir-mcp`, an MCP server for Tenzir.

## Core Concepts

The server exposes Tenzir functionality through the Model Context Protocol, enabling AI assistants to execute pipelines, query documentation, work with OCSF schemas, and manage packages.

**Request Flow:**

1. **Server** initializes FastMCP and registers all tools
2. **Tools** handle MCP requests organized by category
3. **Execution** runs TQL pipelines through Tenzir
4. **Documentation** searches embedded docs with cross-references
5. **OCSF** queries schema definitions for security data modeling

## Package Layout

- `src/tenzir_mcp/` contains the core package with server, tools, and embedded data
- `src/tenzir_mcp/tools/` organizes MCP tools by category (execution, documentation, ocsf, packaging, coding)
- `src/tenzir_mcp/data/` holds embedded resources (OCSF schemas, documentation, indexes)
- `src/tenzir_mcp/prompts/` contains system prompts for AI agents

## Tool Categories

**Execution** runs TQL pipelines and tests through Tenzir. Uses `uvx tenzir` by default, configurable via `TENZIR_BINARY` env var.

**Documentation** provides search and retrieval over embedded Tenzir docs with cross-reference support.

**OCSF** queries Open Cybersecurity Schema Framework definitions, event classes, objects, and profiles.

**Packaging** creates and manages Tenzir packages with operators, pipelines, contexts, and tests.

**Coding** generates TQL parsers and OCSF mapping packages.

## Documentation

Primary documentation lives at <https://docs.tenzir.com/reference/mcp-server>.
