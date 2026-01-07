---
title: Add smart Tenzir binary detection
type: change
pr: 14
authors:
  - mavam
  - claude
created: 2026-01-06T20:23:22.587204Z
---

Pipeline execution now auto-detects the Tenzir binary: it first checks the `TENZIR_BINARY` environment variable, then looks for a local `tenzir` installation, and finally falls back to `uvx tenzir` if uv is available. This removes the requirement to have Tenzir pre-installed while still respecting existing installations.
