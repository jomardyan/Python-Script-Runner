# GitHub Actions Release Workflow

Complete documentation for the automated release pipeline.

## Overview

The release workflow automates the entire release process:

```
Version Bump  →  Prepare Release  →  Publish to GitHub  →  GitHub Actions Workflow
     (local)      (local + tag)        (push tag)          (automated CI/CD)
                                                           ├─ Validate version
                                                           ├─ Run tests
                                                           ├─ Build distributions
                                                           ├─ Publish to PyPI
                                                           ├─ Publish to GitHub Packages
                                                           └─ Create GitHub Release
```

## Workflow File

**Location:** `.github/workflows/publish.yml`

### Triggers

The workflow automatically triggers on:

1. **Git Tag Push** - When you push a tag matching `v*` (e.g., `v6.2.0`)
2. **GitHub Release Creation** - When a release is published on GitHub

### Jobs

#### 1. `validate-version`
- **Purpose:** Verify version consistency across all files
- **Runs on:** Ubuntu latest
- **Outputs:** `version` and `tag_name` for downstream jobs
- **Checks:**
  - Version format validation (semantic versioning)
  - Tag vs source file version matching

#### 2. `test`
- **Purpose:** Run comprehensive tests on multiple Python versions
- **Runs on:** Ubuntu latest
- **Matrix:** Python 3.8, 3.9, 3.10, 3.11, 3.12
- **Steps:**
  - Install dependencies
  - Compile Python files
  - Run pytest if available
  - Validate package imports

#### 3. `build-and-publish`
- **Purpose:** Build distributions and publish to registries
- **Runs on:** Ubuntu latest
- **Permissions:** Write to contents and packages
- **Environment:** `release` (can be protected in Settings)
- **Steps:**
  - Verify version consistency
  - Build wheel and source distributions
  - Verify with twine
  - Publish to PyPI (requires `PYPI_API_TOKEN` secret)
  - Publish to GitHub Packages (auto-uses `GITHUB_TOKEN`)
  - Create GitHub Release with artifacts
  - Publish success summary

## Manual Release Process

### Step 1: Bump Version

```bash
# Preview the bump
bash release.sh bump patch dry-run

# Apply the bump
bash release.sh bump patch
# or
bash release.sh bump minor
# or
bash release.sh bump major
```

This updates:
- `pyproject.toml`
- `runner.py`
- `__init__.py`

And commits the change to git.

### Step 2: Prepare Release

```bash
bash release.sh prepare-release 6.2.0
```

This:
- Updates version in all files (via `version.sh set`)
- Commits version changes
- Creates an annotated git tag `v6.2.0`

### Step 3: Publish Release

```bash
bash release.sh publish 6.2.0
```

This:
- Pushes the tag to GitHub
- Triggers GitHub Actions workflow

### Step 4: Monitor Workflow

GitHub Actions automatically:
1. Validates version in all files
2. Runs tests on Python 3.8-3.12
3. Builds distributions
4. Publishes to PyPI
5. Publishes to GitHub Packages
6. Creates GitHub Release

Monitor at: https://github.com/jomardyan/Python-Script-Runner/actions

## Configuration

### Prerequisites

1. **GitHub Secrets** - Set in repository Settings → Secrets and variables → Actions

   Required secrets:
   - `PYPI_API_TOKEN`: Your PyPI API token (from `~/.pypirc`)
   - `GITHUB_TOKEN`: Auto-provided by GitHub Actions

2. **Version Consistency** - All version sources must match:
   - `pyproject.toml`: `version = "X.Y.Z"`
   - `runner.py`: `__version__ = "X.Y.Z"`
   - `__init__.py`: `__version__ = "X.Y.Z"` (fallback version)
   - Git tag: `v X.Y.Z`

### Adding PyPI API Token

1. Go to: https://github.com/jomardyan/Python-Script-Runner/settings/secrets/actions
2. Click "New repository secret"
3. Name: `PYPI_API_TOKEN`
4. Value: (from your `~/.pypirc` file)

## Version Management Scripts

### `version.sh` - Semantic Versioning

Commands:
```bash
bash version.sh current              # Show current version
bash version.sh bump patch           # Bump patch version
bash version.sh bump minor           # Bump minor version
bash version.sh bump major           # Bump major version
bash version.sh set 6.3.0            # Set specific version
bash version.sh validate             # Validate version format
bash version.sh sync                 # Synchronize versions across files
```

### `release.sh` - Release Orchestration

Commands:
```bash
bash release.sh version              # Show version info
bash release.sh bump patch           # Bump version (uses version.sh)
bash release.sh validate             # Pre-release checks
bash release.sh prepare-release 6.3.0  # Prepare and tag release
bash release.sh publish 6.3.0        # Publish tag to GitHub
bash release.sh help                 # Show help
```

## Workflow Details

### Job Ordering

```
validate-version
    ↓
    ├─→ test (parallel, matrix: Python 3.8-3.12)
    │
    └─→ build-and-publish (only after validation & tests pass)
```

### Concurrency

- **Group:** `publish-${{ github.ref }}`
- **Cancel-in-progress:** false (prevents canceling active releases)

### Permissions

```yaml
permissions:
  contents: write      # Create releases
  packages: write      # Publish to GitHub Packages
```

### Environment

- **Name:** `release`
- **Can be protected** in Settings → Environments

## Troubleshooting

### Workflow Fails at PyPI Step

**Error:** `401 Unauthorized` or similar

**Solution:**
1. Check `PYPI_API_TOKEN` is set in GitHub Secrets
2. Token must be valid and not expired
3. Verify in `~/.pypirc`: `password = pypi-AgEI...`

### Version Mismatch Error

**Error:** `Version mismatch: pyproject.toml has X.Y.Z, tag has A.B.C`

**Solution:**
1. Use `bash version.sh sync` to synchronize versions
2. Ensure tag matches version in `pyproject.toml`
3. Run `bash version.sh validate` locally before pushing

### Tag Already Exists

**Error:** `Tag vX.Y.Z already exists`

**Solution:**
```bash
# Delete old tag
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z

# Create new tag
bash release.sh prepare-release X.Y.Z
bash release.sh publish X.Y.Z
```

### Tests Fail in Workflow

**Error:** `Tests failed on Python 3.X`

**Solution:**
1. Check test output in workflow logs
2. Run tests locally: `python -m pytest tests/`
3. Fix issues and commit
4. Version bump and retry

## Success Indicators

After successful release:

1. ✅ Workflow completes with "publish-success"
2. ✅ Package appears on PyPI: https://pypi.org/project/python-script-runner/
3. ✅ Package appears in GitHub Packages
4. ✅ GitHub Release created with build artifacts
5. ✅ Can install: `pip install python-script-runner==X.Y.Z`

## Release URLs

After publishing version 6.2.0:

- **PyPI:** https://pypi.org/project/python-script-runner/6.2.0/
- **GitHub Packages:** https://github.com/jomardyan/Python-Script-Runner/packages
- **GitHub Release:** https://github.com/jomardyan/Python-Script-Runner/releases/tag/v6.2.0

## Quick Reference

```bash
# Typical release flow
bash release.sh bump patch              # Bump version
bash release.sh validate                # Verify everything
bash release.sh prepare-release 6.2.1   # Create tag
bash release.sh publish 6.2.1           # Push and trigger workflow

# Or do it all at once (recommended)
# 1. Manual bump: bash release.sh bump patch
# 2. Manual prepare: bash release.sh prepare-release <version>
# 3. Automatic publish: bash release.sh publish <version>
# 4. Automatic workflow: GitHub Actions does the rest!
```

## Integration with `version.sh`

`release.sh` uses `version.sh` for:
- Version bumping (major/minor/patch)
- Version setting
- Version validation
- Version synchronization

To bump manually:
```bash
bash version.sh bump patch
bash version.sh sync
```

Then prepare release:
```bash
bash release.sh prepare-release $(bash version.sh current)
```

## Security

- **Secrets:** Encrypted at rest, masked in logs
- **PYPI_API_TOKEN:** Only available during workflow execution
- **GITHUB_TOKEN:** Auto-provided by GitHub, limited scope per job
- **Access:** Only workflows in default branch can publish

## Related Documentation

- [RELEASING.md](../../RELEASING.md) - Release process guide
- [.github/AUTOMATION_SETUP.md](AUTOMATION_SETUP.md) - GitHub Actions setup
- [.github/SECRETS_SECURITY.md](SECRETS_SECURITY.md) - Security details

