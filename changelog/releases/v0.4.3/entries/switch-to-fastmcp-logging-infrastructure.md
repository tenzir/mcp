---
title: Switch to FastMCP logging infrastructure
type: change
authors:
- mavam
- claude
created: 2025-12-12T12:21:07.734038Z
---

The server now uses FastMCP's built-in logging infrastructure instead of custom file-based logging. This eliminates the `tenzir-mcp.log` file that was previously created in the current working directory. Use `FASTMCP_LOG_LEVEL=DEBUG` for verbose output when troubleshooting.
