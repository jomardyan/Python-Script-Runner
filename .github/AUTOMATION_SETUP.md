# GitHub Actions & GitHub Packages Setup Guide

## Overview

This repository is configured to automatically publish to both PyPI and GitHub Packages using GitHub Actions when you create a release.

## Automatic Setup

The workflow file `.github/workflows/publish.yml` handles:

✅ Building distributions (wheel + tarball)
✅ Running tests before publishing
✅ Publishing to PyPI (main registry)
✅ Publishing to GitHub Packages (backup + org control)
✅ Creating GitHub release assets
✅ Detailed publishing logs

## What You Need

### 1. PyPI API Token (Already Configured)

Your PyPI token is already set up. It's stored in GitHub Secrets.

**Location:** Settings → Secrets and variables → Actions
**Secret Name:** `PYPI_API_TOKEN`

### 2. GitHub Token (Automatic)

GitHub Actions automatically provides a `GITHUB_TOKEN` with package publishing permissions. No manual setup needed!

## How to Make a Release

### Simple 3-Step Process:

#### Step 1: Update Version Numbers

Edit these three files and increment the version:

```bash
# Example: 6.1.0 → 6.2.0

# File 1: pyproject.toml
version = "6.2.0"

# File 2: runner.py
__version__ = "6.2.0"

# File 3: __init__.py
__version__ = "6.2.0"
```

#### Step 2: Commit & Push

```bash
git add pyproject.toml runner.py __init__.py
git commit -m "chore: bump version to 6.2.0"
git push origin main
```

#### Step 3: Create Release Tag & GitHub Release

```bash
# Create annotated tag
git tag -a v6.2.0 -m "Release version 6.2.0"
git push origin v6.2.0
```

Then go to: https://github.com/jomardyan/Python-Script-Runner/releases

- Click "Draft a new release"
- Select tag `v6.2.0` from dropdown
- Add release title: `Python Script Runner v6.2.0`
- Add release notes (features, fixes, etc.)
- Click "Publish release"

**That's it!** 🎉

The GitHub Actions workflow will automatically:
- Build the package
- Publish to PyPI
- Publish to GitHub Packages
- Attach build artifacts to the GitHub release

## Check Publishing Status

### In GitHub Actions:

1. Go to: https://github.com/jomardyan/Python-Script-Runner/actions
2. Click the "Publish Package" workflow
3. Watch the automated build and publish process

### Verify It Worked:

```bash
# Check PyPI
pip index versions python-script-runner

# Check GitHub Packages (requires auth)
pip install --extra-index-url https://python.pkg.github.com/jomardyan python-script-runner
```

## Workflow Triggers

The publish workflow runs when:

✅ You create a GitHub Release
✅ You push a tag matching `v*` pattern (e.g., `v6.2.0`)

## Current Releases

### PyPI
- **URL:** https://pypi.org/project/python-script-runner/
- **Install:** `pip install python-script-runner`

### GitHub Packages
- **URL:** https://github.com/jomardyan/Python-Script-Runner/packages
- **Install:** `pip install --extra-index-url https://python.pkg.github.com/jomardyan python-script-runner`

## Version History

| Version | Date | Status |
|---------|------|--------|
| 6.1.0 | Oct 22, 2025 | ✅ Published |
| 6.0.1 | Oct 22, 2025 | ✅ Published |
| 6.0.0 | Oct 22, 2025 | ✅ Published |

Next: v6.2.0 (upcoming)

## Troubleshooting

### Workflow fails

Check the Actions tab logs for error details.

Common issues:
- Version numbers not updated consistently
- PyPI token expired
- Tests failing
- Build errors

### Package not showing up

- PyPI: Can take 5-10 minutes to appear
- GitHub Packages: Usually instant

### Need to delete a release?

```bash
# Delete local tag
git tag -d v6.1.0

# Delete remote tag
git push origin --delete v6.1.0

# Delete GitHub release (via web interface)
```

## Secrets Configuration

If you need to add/update secrets:

1. Go to: https://github.com/jomardyan/Python-Script-Runner/settings/secrets/actions
2. Click "New repository secret"
3. Add secret name and value
4. Click "Add secret"

Current secrets:
- `PYPI_API_TOKEN` - PyPI authentication token ✅

## Next Steps

1. Create v6.2.0 release when ready with new features
2. Monitor workflow execution in Actions tab
3. Verify packages on both PyPI and GitHub Packages
4. Users can install from either registry

---

**All automated! No more manual uploads needed!** 🚀
