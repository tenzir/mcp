---
title: Default to uvx tenzir for pipeline execution
type: change
pr: 14
authors:
  - mavam
  - claude
created: 2026-01-06T20:23:22.587204Z
---

Pipeline execution now uses `uvx tenzir` by default, removing the requirement to have Tenzir installed in your PATH. Set the `TENZIR_BINARY` environment variable to override the command for environments where Tenzir is already available, such as the Docker image.
