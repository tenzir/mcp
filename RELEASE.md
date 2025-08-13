# Release Process

## Prerequisites

1. **PyPI Account**: Create at https://pypi.org/account/register/
2. **GitHub Repository**: Ensure code is pushed to GitHub
3. **PyPI API Token**: Generate token for PyPI

## Production Release

### Option 1: Manual Release with UV

1. **Update Version** in `pyproject.toml` and `src/tenzir_mcp/__init__.py`

2. **Update CHANGELOG.md**
   - Move items from "Unreleased" to the new version section
   - Add release date

3. **Commit Changes**
   ```bash
   git add -A
   git commit -m "Release v0.1.0"
   ```

4. **Build Package**
   ```bash
   uv build
   ```

5. **Upload to PyPI**
   ```bash
   export UV_PUBLISH_TOKEN=pypi-xxxxx  # Your real PyPI token
   uv publish
   ```

6. **Create Git Tag**
   ```bash
   git tag v0.1.0
   git push origin main
   git push origin v0.1.0
   ```

### Option 2: GitHub Release (Recommended)

1. **Set up Trusted Publishing** on PyPI:
   - Go to https://pypi.org/manage/account/publishing/
   - Add a new publisher:
     - PyPI Project Name: `tenzir-mcp`
     - Owner: `tenzir`
     - Repository: `mcp`
     - Workflow: `publish.yml`
     - Environment: `pypi`

2. **Set up GitHub Environment**:
   - Go to Settings → Environments in your GitHub repo
   - Create `pypi` environment with:
     - Protection rules (optional)
     - Reviewers (optional)

3. **Update Version and Changelog**
   ```bash
   # Update version in pyproject.toml and __init__.py
   # Update CHANGELOG.md
   git add -A
   git commit -m "Release v0.1.0"
   git push origin main
   ```

4. **Create a Release**
   ```bash
   # Tag the version
   git tag v0.1.0
   git push origin v0.1.0
   ```
   
   Then on GitHub:
   - Go to Releases → Create Release
   - Choose the tag `v0.1.0`
   - Title: `v0.1.0`
   - Description: Copy from CHANGELOG.md
   - Click "Publish release"
   
   GitHub Actions will automatically:
   - Build the package
   - Run tests
   - Publish to PyPI

## Version Bumping

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions  
- **PATCH** version for backwards-compatible bug fixes

Before each release:

1. Update version in:
   - `pyproject.toml`
   - `src/tenzir_mcp/__init__.py`

2. Update CHANGELOG.md:
   ```markdown
   ## [0.2.0] - 2024-01-15
   
   ### Added
   - New feature X
   
   ### Fixed
   - Bug Y
   ```

3. Commit:
   ```bash
   git commit -am "Bump version to 0.2.0"
   ```

4. Tag:
   ```bash
   git tag v0.2.0
   ```

5. Push:
   ```bash
   git push && git push --tags
   ```

## Post-Release Verification

```bash
# Wait a few minutes for PyPI to update, then:

# Install from PyPI
uvx --from tenzir-mcp tenzir-mcp --version

# Verify it's the correct version
python -c "import tenzir_mcp; print(tenzir_mcp.__version__)"

# Check PyPI page
open https://pypi.org/project/tenzir-mcp/
```

## Troubleshooting

### Build Issues

```bash
# Clean all build artifacts
rm -rf dist/ build/ *.egg-info src/*.egg-info

# Rebuild
uv build
```

### Upload Issues

```bash
# Check your token is correct
echo $UV_PUBLISH_TOKEN

# Try verbose mode
uv publish --verbose
```

### Installation Issues

```bash
# Clear pip cache
uv cache clean

# Try installing with --force-reinstall
uv pip install --force-reinstall tenzir-mcp
```

## Rollback Procedure

If a release has critical issues:

1. **Yank the Release on PyPI** (doesn't delete, just marks as "don't use"):
   ```bash
   # Via PyPI web interface, or:
   pip install twine
   twine yank tenzir-mcp==0.1.0
   ```

2. **Fix the Issue**

3. **Release a Patch Version**:
   ```bash
   # Bump to 0.1.1
   # Follow normal release process
   ```

## Release Schedule

- **Patch releases**: As needed for bug fixes
- **Minor releases**: Monthly or when significant features are ready
- **Major releases**: When breaking changes are necessary

## Checklist

### Pre-release Checklist
- [ ] All tests passing: `uv run pytest`
- [ ] Code formatted: `uv run black src/ tests/`
- [ ] Imports sorted: `uv run isort src/ tests/`
- [ ] Linting clean: `uv run ruff check src/ tests/`
- [ ] Type checking passes: `uv run mypy src/`
- [ ] CHANGELOG.md updated
- [ ] Version bumped in pyproject.toml
- [ ] Version bumped in __init__.py
- [ ] Documentation updated if needed

### Release Checklist
- [ ] Package builds: `uv build`
- [ ] TestPyPI upload works
- [ ] TestPyPI installation works
- [ ] Git tag created
- [ ] GitHub Release created
- [ ] PyPI upload successful
- [ ] PyPI installation works
- [ ] Announcement made (if applicable)

### Post-release Checklist  
- [ ] Verify package on PyPI
- [ ] Test installation with uvx
- [ ] Update any external documentation
- [ ] Close related GitHub issues
- [ ] Plan next release milestones