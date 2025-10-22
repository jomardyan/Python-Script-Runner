# Release Guide

This document describes how to release a new version of Python Script Runner.

## Prerequisites

- [ ] All tests passing locally: `python -m pytest`
- [ ] All changes committed and pushed
- [ ] Changelog updated with release notes
- [ ] Version numbers updated in:
  - `pyproject.toml` (version field)
  - `runner.py` (__version__)
  - `__init__.py` (__version__ in __all__ export)

## Release Process

### Option 1: Using GitHub Releases (Recommended - Automated)

This is the **easiest** method. The GitHub Actions workflow will automatically:
- Build the distributions
- Run tests
- Publish to PyPI
- Publish to GitHub Packages
- Create release assets

#### Steps:

1. **Update version numbers:**
   ```bash
   # Edit these files and bump version (e.g., 6.1.0 → 6.2.0)
   # - pyproject.toml
   # - runner.py
   # - __init__.py
   
   # Verify version is consistent
   grep -n "version = " pyproject.toml
   grep -n "__version__ = " runner.py
   grep -n "__version__ = " __init__.py
   ```

2. **Commit version bump:**
   ```bash
   git add pyproject.toml runner.py __init__.py
   git commit -m "chore: bump version to 6.2.0"
   git push origin main
   ```

3. **Create a Git tag:**
   ```bash
   git tag -a v6.2.0 -m "Release version 6.2.0"
   git push origin v6.2.0
   ```

4. **Create GitHub Release:**
   - Go to: https://github.com/jomardyan/Python-Script-Runner/releases
   - Click "Draft a new release"
   - Tag version: Select `v6.2.0` from the dropdown
   - Release title: `Python Script Runner v6.2.0`
   - Description: Add release notes (new features, bug fixes, etc.)
   - Click "Publish release"

5. **Watch the workflow:**
   - Go to: https://github.com/jomardyan/Python-Script-Runner/actions
   - Monitor the "Publish Package" workflow
   - It will automatically publish to both PyPI and GitHub Packages

### Option 2: Manual Local Publishing

If you need to publish locally:

1. **Build the distributions:**
   ```bash
   python -m build
   ```

2. **Verify the build:**
   ```bash
   twine check dist/*
   ```

3. **Upload to PyPI:**
   ```bash
   twine upload dist/* -r pypi
   ```

4. **Upload to GitHub Packages:**
   ```bash
   # First, set your GitHub token
   export GITHUB_TOKEN=your_token_here
   
   # Upload
   twine upload dist/* \
     -r github \
     -u "username" \
     -p "$GITHUB_TOKEN"
   ```

## Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., `6.1.0`)
  - **MAJOR**: Breaking changes (rarely)
  - **MINOR**: New features (backward compatible)
  - **PATCH**: Bug fixes

Examples:
- `6.1.0` → `6.2.0` (new feature)
- `6.1.0` → `6.1.1` (bug fix)
- `6.1.0` → `7.0.0` (breaking change)

## Checklist

Before releasing:

```bash
# 1. Make sure everything is committed
git status

# 2. Run tests
python -m pytest -v

# 3. Check version consistency
grep -rn "__version__" . --include="*.py" | grep -E "(pyproject|runner|__init__)"

# 4. Check if there are any uncommitted changes
git diff

# 5. Verify git history
git log --oneline -10
```

## Publishing Results

After a successful release, you can verify it's published:

### PyPI
- Check: https://pypi.org/project/python-script-runner/
- Install: `pip install python-script-runner`

### GitHub Packages
- Check: https://github.com/jomardyan/Python-Script-Runner/packages
- Install: `pip install --extra-index-url https://python.pkg.github.com/jomardyan python-script-runner`

## Troubleshooting

### GitHub Actions workflow fails

1. **Check logs:** Go to Actions tab and click the failed workflow
2. **Common issues:**
   - `PYPI_API_TOKEN` not set (add to repo secrets)
   - Version mismatch between files
   - Test failures
   - Build failures

### Version already exists on PyPI

```bash
# If you accidentally uploaded the same version:
# 1. Delete the version on PyPI (via web interface)
# 2. Wait a few minutes
# 3. Upload with correct version
```

### Package not appearing in GitHub Packages

```bash
# GitHub Packages may take a few minutes to index
# Check at: https://github.com/jomardyan/Python-Script-Runner/packages
```

## Additional Resources

- [PyPI Help](https://pypi.org/help/)
- [GitHub Packages - Python Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-python-registry)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Semantic Versioning](https://semver.org/)

---

**Next Release:** Plan for v6.2.0 with new features!
