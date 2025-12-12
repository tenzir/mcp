This patch release updates the server to use FastMCP's built-in logging infrastructure. The custom file-based logging has been removed, eliminating the creation of `tenzir-mcp.log` files in the working directory. Use `FASTMCP_LOG_LEVEL=DEBUG` for verbose output when troubleshooting.

## 🔧 Changes

### Switch to FastMCP logging infrastructure

The server now uses FastMCP's built-in logging infrastructure instead of custom file-based logging. This eliminates the `tenzir-mcp.log` file that was previously created in the current working directory. Use `FASTMCP_LOG_LEVEL=DEBUG` for verbose output when troubleshooting.

*By @mavam and @claude.*
