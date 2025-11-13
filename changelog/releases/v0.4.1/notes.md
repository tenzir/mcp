## 🐞 Bug fixes

### Improve exception handling in MCP tools

The `run_test` and `package_add_changelog` MCP tools now catch `SystemExit` and other exceptions to keep the server responsive when external libraries fail early.

*By @mavam.*

### Make docs tooling resilient on fresh clones

Fixed `make dev` failing on fresh repository clones.

Previously, `make dev` would fail on first use because the documentation database hadn't been built yet. The tooling (`make build-doc-index` and `make build-doc-db`) now gracefully handles missing documentation files and creates necessary directories, making the initial setup experience smoother for new contributors.

*By @mavam.*
