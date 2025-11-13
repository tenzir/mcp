---
title: Make docs tooling resilient on fresh clones
type: bugfix
authors:
  - mavam
created: 2025-11-11
---

Fixed `make dev` failing on fresh repository clones.

Previously, `make dev` would fail on first use because the documentation database
hadn't been built yet. The tooling (`make build-doc-index` and `make build-doc-db`)
now gracefully handles missing documentation files and creates necessary
directories, making the initial setup experience smoother for new contributors.
