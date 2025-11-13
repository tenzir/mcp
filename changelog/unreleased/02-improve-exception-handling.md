---
title: Improve exception handling in MCP tools
type: bugfix
authors:
  - mavam
created: 2025-11-13
---

The `run_test` and `package_add_changelog` MCP tools now catch `SystemExit` and
other exceptions to keep the server responsive when external libraries fail
early.
