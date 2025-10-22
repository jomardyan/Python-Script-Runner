# Automated Versioning in GitHub Actions

## Overview

The release workflow now includes fully integrated automatic versioning:

- **Automatic version detection** from git tags
- **Semantic version bumping** (major, minor, patch)
- **Automatic code file updates** (pyproject.toml, runner.py)
- **GitHub Actions dispatch** for one-click releases
- **Version tracking in release notes**

## Workflow Triggers

### 1. Manual Workflow Dispatch (Recommended)

One-click automatic release from GitHub UI:

**Steps:**
1. Go to GitHub → Actions → Release
2. Click "Run workflow"
3. Select bump type: `patch`, `minor`, or `major`
4. Click "Run workflow"

**What happens automatically:**
- Version is bumped in `pyproject.toml` and `runner.py`
- Changes are committed to main
- Git tag is created and pushed
- Full build and release runs
- Both Python 3 and PyPy3 distributions are built
- GitHub Release is created with artifacts

### 2. Direct Git Tag Push

Push a version tag directly:

```bash
git tag -a v3.0.1 -m "Release version 3.0.1"
git push origin v3.0.1
```

Workflow will:
- Run tests on Python 3 and PyPy3
- Build distributions
- Create GitHub Release
- Extract version from `runner.py` for release notes

### 3. Using Local Release Script

Manage versions locally:

```bash
# Show current version
bash version.sh current

# Preview version bump
bash version.sh bump patch dry-run

# Bump version locally
bash version.sh bump patch

# Commit and prepare for release
bash release.sh prepare-release 3.0.1

# Push to GitHub (triggers workflow)
bash release.sh publish 3.0.1
```

## Version File Management

### Single Source of Truth

Version is defined in **pyproject.toml** and automatically synced:

```toml
[project]
version = "3.0.0"
```

### Automatic Sync

The script keeps both files in sync:
- `pyproject.toml` - Primary version source
- `runner.py` - Code-level version (`__version__ = "3.0.0"`)

Check sync status:
```bash
bash version.sh sync
```

## Release Process

### Quick Release (One-Click)

1. **GitHub UI:**
   - Actions → Release → Run workflow
   - Select version bump type
   - Done! ✅

2. **GitHub CLI:**
   ```bash
   gh workflow run release.yml -f bump_type=patch
   ```

### Standard Release (Manual Control)

```bash
# 1. Validate code
bash release.sh validate

# 2. Bump version
bash version.sh bump patch

# 3. Commit changes
git add pyproject.toml runner.py
git commit -m "Bump version to 3.0.1"

# 4. Push tag
bash release.sh prepare-release 3.0.1
bash release.sh publish 3.0.1
```

## Release Notes Generation

Release notes are automatically generated and include:

```
Version: v3.0.1
Code Version: 3.0.1
Build Date: 2025-10-22 15:30:00 UTC

Distributions:
- python3-runner-v3.0.1.tar.gz
- python3-runner-v3.0.1.zip
- pypy3-runner-v3.0.1.tar.gz
- pypy3-runner-v3.0.1.zip
- SHA256SUMS.txt
```

Version information comes from:
- Git tag: Extracted from push trigger
- runner.py: Read from `__version__` variable
- pyproject.toml: Read from `[project] version` field

## Workflow Structure

```
Release Workflow (on: push tags matching v*.*.*)
├── auto-version (if: workflow_dispatch)
│   ├── Bump version in pyproject.toml
│   ├── Bump version in runner.py
│   ├── Commit to main
│   └── Create and push tag → triggers full workflow
│
├── test (matrix: Python 3.11, PyPy 3.10)
│   ├── Install dependencies
│   ├── Compile code
│   └── Run tests
│
├── build-python3
│   ├── Create Python 3 bundle
│   ├── Build tar.gz and zip
│   └── Upload artifacts
│
├── build-pypy3
│   ├── Create PyPy3 bundle
│   ├── Build tar.gz and zip
│   └── Upload artifacts
│
└── create-release
    ├── Extract version from tag
    ├── Download all artifacts
    ├── Generate SHA256 checksums
    ├── Generate release notes
    └── Create GitHub Release with all files
```

## Version Bumping Logic

### Semantic Versioning (MAJOR.MINOR.PATCH)

**Patch** (e.g., 3.0.0 → 3.0.1)
- Bug fixes
- Minor improvements
- No API changes

**Minor** (e.g., 3.0.0 → 3.1.0)
- New features
- Backwards compatible
- Enhanced capabilities

**Major** (e.g., 3.0.0 → 4.0.0)
- Breaking changes
- New architecture
- API changes

## GitHub Permissions

The workflow requires:
- `contents: write` - To create releases and tags
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions

## Troubleshooting

### Version Not Updated

Check version sync:
```bash
bash version.sh sync
```

### Tag Already Exists

Delete and recreate:
```bash
git tag -d v3.0.1
git push origin :v3.0.1
bash release.sh prepare-release 3.0.1
```

### Workflow Didn't Trigger

1. Verify tag format: `v*.*.*` (e.g., `v3.0.1`)
2. Check GitHub Actions logs
3. Ensure tag is pushed: `git push origin v3.0.1`

### Automatic Version Bump Failed

1. Ensure commit permissions
2. Check git config: `git config --list`
3. Verify version script: `bash version.sh validate`

## Environment Variables

Available in workflow:
- `GITHUB_REF_NAME` - Tag name (e.g., v3.0.1)
- `GITHUB_REF` - Full ref (refs/tags/v3.0.1)
- `GITHUB_EVENT_NAME` - Trigger type (workflow_dispatch, push)

## Continuous Integration Best Practices

1. **Always validate before release:**
   ```bash
   bash release.sh validate
   ```

2. **Use meaningful version numbers:**
   - Follow semver strictly
   - Align with feature releases

3. **Keep git clean:**
   - No uncommitted changes before tagging
   - Commit version changes separately

4. **Monitor release workflow:**
   - Check GitHub Actions logs
   - Verify artifacts are built correctly

5. **Document changes:**
   - Include release notes in commit message
   - Update CHANGELOG if applicable

## Integration with Other Tools

### GitHub CLI
```bash
# Trigger workflow
gh workflow run release.yml -f bump_type=minor

# Check workflow status
gh run list --workflow=release.yml
```

### Command Line
```bash
# Full automated release
bash version.sh bump patch && \
  git add pyproject.toml runner.py && \
  git commit -m "Bump version" && \
  bash release.sh prepare-release $(bash version.sh current) && \
  bash release.sh publish $(bash version.sh current)
```

## Version History Tracking

To view all releases:
```bash
git tag -l 'v*' --sort=-version:refname
```

To see version changes:
```bash
git log --oneline pyproject.toml runner.py | grep -i version
```
