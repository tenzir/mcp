# Release Process

## Overview

When you create a release, the following artifacts are automatically published:

- **PyPI Package**: `tenzir-mcp` available via `pip install` / `uvx`
- **Docker Images**: Multi-platform (linux/amd64, linux/arm64) images pushed to:
  - GitHub Container Registry: `ghcr.io/tenzir/mcp`
  - Docker Hub: `docker.io/tenzir/mcp`
  - Tagged as: `latest`, `v0.1.0`, `0.1`, `0` (semantic versioning)

## Steps to Cut a Release

### Automated (Recommended)

```bash
# Interactive release process
./scripts/release.sh

# Preview mode (no changes made)
./scripts/release.sh --dry-run
```

The interactive flow:

1. **Select release type** - Choose patch, minor, or major with preview of new version
2. **Review changes** - See all commits and changes since last release
3. **Confirm** - Simple yes/no to proceed
4. **Automatic execution** - Updates version, commits, tags, pushes
5. **Browser redirect** - Opens GitHub release page with pre-filled information

You just need to add the detailed release description and click "Publish release".

### Manual Steps

1. **Update Version**
   - Edit version in `pyproject.toml`
   - Edit version in `src/tenzir_mcp/__init__.py`

2. **Commit and Push**

   ```bash
   git add -A
   git commit -m "Release v0.2.0"
   git push origin main
   ```

3. **Create Tag**

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

4. **Create GitHub Release**
   - Go to [Releases](https://github.com/tenzir/mcp/releases) → "Create Release"
   - Select the tag (e.g., `v0.2.0`)
   - Title: `v0.2.0`
   - Write release notes describing changes
   - Click "Publish release"

   **Automated Actions:**
   - PyPI package published via trusted publishing
   - Docker images pushed to `ghcr.io/tenzir/mcp` and `docker.io/tenzir/mcp`
   - Installation verification runs

5. **Verify Release**

   ```bash
   # Test PyPI package (wait ~5 minutes)
   uvx tenzir-mcp@latest --version

   # Check Docker images
   docker pull ghcr.io/tenzir/mcp:latest
   ```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking API changes
- **MINOR**: New features (backwards-compatible)
- **PATCH**: Bug fixes (backwards-compatible)

## Pre-release Checklist

- [ ] Tests passing: `make test`
- [ ] All checks passing: `make check`
- [ ] Version bumped in both files

## If Something Goes Wrong

### Yank a Bad Release

```bash
# Via PyPI web interface, or:
pip install twine
twine yank tenzir-mcp==0.2.0
```

Then fix the issue and release a patch version (e.g., 0.2.1).
