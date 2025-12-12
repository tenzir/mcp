---
title: Fix CI/CD workflows with reusable components
type: bugfix
authors:
- mavam
- claude
components:
- ci
created: 2025-12-12T13:12:03.733058Z
---

Fix broken `publish.yml` workflow that referenced removed scripts (`scripts/download-docs.py`, etc.) consolidated into the bootstrap module in commit 923ff37.

**Changes:**

- Extract OCSF schema build logic into reusable composite action (`.github/actions/build-ocsf/`)
- Add `bootstrap-data` composite action for shared data setup
- Add reusable workflows: `tests.yml` (test suite), `build.yml` (package build)
- Rename `test.yml` → `ci.yml` for clarity
- Rename `publish.yml` → `release.yml` and restructure to run tests before publishing to PyPI
- Add proper version verification after PyPI publish

This refactoring eliminates workflow duplication and ensures the release process properly validates before publishing.
