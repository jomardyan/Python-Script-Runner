# Version & Release Integration Summary

## Overview

Successfully integrated `version.sh` with `release.sh` and enhanced GitHub Actions workflow for automated, consistent version management and publishing.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Release Management Pipeline                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Local Development                 GitHub                        │
│  ─────────────────                ──────                        │
│                                                                   │
│  1. bash release.sh                2. GitHub Actions            │
│     └─ bump patch                     └─ Triggers on tag        │
│        ├─ Uses version.sh              ├─ validate-version     │
│        │  ├─ Semantic versioning       ├─ test (multi-py)      │
│        │  └─ File updates             └─ build-and-publish     │
│        └─ Git commit                    ├─ PyPI upload        │
│                                        ├─ GitHub Packages     │
│  2. bash release.sh                   └─ GitHub Release       │
│     └─ prepare-release X.Y.Z                                  │
│        ├─ Uses version.sh set                                 │
│        ├─ Git tag v X.Y.Z                                    │
│        └─ Ready for publish                                  │
│                                                                   │
│  3. bash release.sh                                            │
│     └─ publish X.Y.Z                                          │
│        ├─ Git push tag                                        │
│        └─ Triggers workflow                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Integration

### 1. `version.sh` - Semantic Versioning Manager

**Purpose:** Manage version numbers across project files

**Files Modified:**
- `pyproject.toml` - Build system version
- `runner.py` - Package version
- `__init__.py` - Fallback version

**Commands:**
```bash
bash version.sh current              # Get current version
bash version.sh bump major/minor/patch  # Bump version
bash version.sh set X.Y.Z            # Set specific version
bash version.sh validate             # Validate format
bash version.sh sync                 # Sync versions across files
```

**Features:**
- Semantic versioning (MAJOR.MINOR.PATCH)
- Atomic file updates
- Validation before changes
- Error handling and rollback support
- Color-coded output

### 2. `release.sh` - Release Orchestration

**Purpose:** Coordinate the complete release process

**Commands:**
```bash
bash release.sh version              # Show version info
bash release.sh bump major/minor/patch  # Bump via version.sh
bash release.sh prepare-release X.Y.Z  # Create git tag
bash release.sh publish X.Y.Z        # Push tag to GitHub
bash release.sh validate             # Pre-release checks
```

**Features:**
- Delegates version management to `version.sh`
- Pre-release validation checks
- Git tag creation and management
- GitHub Actions workflow integration
- Comprehensive error handling

### 3. GitHub Actions Workflow

**File:** `.github/workflows/publish.yml`

**Jobs:**

1. **validate-version**
   - Extracts version from git tag
   - Validates semantic versioning format
   - Verifies consistency with source files

2. **test**
   - Runs on Python 3.8, 3.9, 3.10, 3.11, 3.12
   - Compiles Python files
   - Runs pytest if available
   - Validates package imports

3. **build-and-publish**
   - Builds wheel and sdist distributions
   - Verifies with twine
   - Publishes to PyPI (requires `PYPI_API_TOKEN` secret)
   - Publishes to GitHub Packages (auto `GITHUB_TOKEN`)
   - Creates GitHub Release with artifacts
   - Generates success summary

## Version File Synchronization

All three files must stay synchronized:

```
pyproject.toml
  version = "6.2.0"

runner.py
  __version__ = "6.2.0"

__init__.py
  __version__ = "6.2.0"  (fallback in except block)
```

**Synchronization points:**
- `version.sh bump` - Updates all three
- `version.sh set` - Updates all three
- `version.sh sync` - Aligns files to pyproject.toml
- `release.sh prepare-release` - Uses version.sh set

## Workflow: Complete Release Example

### Scenario: Release v6.3.0

```bash
# Step 1: Bump version (automatic with version.sh)
bash release.sh bump minor
# Updates: pyproject.toml, runner.py, __init__.py
# Commits: "chore: bump version to 6.3.0"

# Step 2: Prepare release
bash release.sh prepare-release 6.3.0
# Verifies version in files
# Creates git tag: v6.3.0
# Output: Ready to publish

# Step 3: Publish to GitHub
bash release.sh publish 6.3.0
# Pushes tag to GitHub
# Triggers GitHub Actions workflow

# Step 4: GitHub Actions automatically:
# ✓ Validates version consistency
# ✓ Runs tests (Python 3.8-3.12)
# ✓ Builds distributions
# ✓ Publishes to PyPI
# ✓ Publishes to GitHub Packages
# ✓ Creates GitHub Release
```

## Key Features

### Version Management
- ✅ Semantic versioning with validation
- ✅ Automatic version bumping (major/minor/patch)
- ✅ Multi-file synchronization
- ✅ Dry-run previews
- ✅ Atomic updates (all-or-nothing)

### Release Automation
- ✅ Pre-release validation
- ✅ Git tag management
- ✅ Workflow integration
- ✅ Multi-environment publishing (PyPI + GitHub Packages)
- ✅ Multi-Python testing (3.8-3.12)

### Workflow Safety
- ✅ Version validation before build
- ✅ Test matrix prevents broken releases
- ✅ Concurrency control (no parallel releases)
- ✅ Environment protection (configurable)
- ✅ Secrets encryption and masking

## Security

**GitHub Actions Secrets:**
- `PYPI_API_TOKEN` - PyPI authentication (manual setup required)
- `GITHUB_TOKEN` - Auto-provided for GitHub Packages

**Features:**
- Secrets encrypted at rest (AES-GCM)
- Auto-masked in logs
- Per-workflow scoped access
- Only available during execution

**Setup:**
```
1. Go to: https://github.com/jomardyan/Python-Script-Runner/settings/secrets/actions
2. Add PYPI_API_TOKEN from ~/.pypirc
3. Workflow auto-uses GITHUB_TOKEN
```

## Documentation Files

- **`.github/workflows/publish.yml`** - GitHub Actions workflow definition
- **`.github/RELEASE_WORKFLOW.md`** - Detailed workflow documentation
- **`version.sh`** - Semantic versioning manager
- **`release.sh`** - Release orchestration (updated)
- **`RELEASING.md`** - Release process guide
- **`.github/AUTOMATION_SETUP.md`** - Setup instructions
- **`.github/SECRETS_SECURITY.md`** - Security details

## Version History

### 6.2.0
- Initial GitHub Actions automation setup
- PyPI and GitHub Packages publishing
- Dual-registry support

### Current (Enhanced)
- ✨ `version.sh` and `release.sh` integration
- ✨ Enhanced GitHub Actions workflow (validate-version job)
- ✨ Multi-Python testing (3.8-3.12 matrix)
- ✨ Comprehensive version consistency checks
- ✨ Improved error handling and reporting
- ✨ Better documentation and integration points

## Next Release: Step-by-Step

To make your next release (e.g., v6.3.0):

```bash
# 1. Bump version
bash release.sh bump minor

# 2. Prepare release
bash release.sh prepare-release 6.3.0

# 3. Publish to GitHub (triggers workflow)
bash release.sh publish 6.3.0

# 4. Monitor workflow at:
# https://github.com/jomardyan/Python-Script-Runner/actions
```

## Troubleshooting

### Version Mismatch
```bash
# Check version consistency
bash version.sh validate
bash version.sh sync
```

### Workflow Fails at Publishing
- Check `PYPI_API_TOKEN` in GitHub Secrets
- Verify token is valid and not expired
- Review workflow logs at GitHub Actions

### Tag Already Exists
```bash
# Delete and recreate
git tag -d vX.Y.Z
git push origin --delete vX.Y.Z
bash release.sh prepare-release X.Y.Z
bash release.sh publish X.Y.Z
```

## Integration Points Summary

| Component | Purpose | Integrates With |
|-----------|---------|-----------------|
| `version.sh` | Version management | `release.sh`, all source files |
| `release.sh` | Release orchestration | `version.sh`, git, GitHub |
| `publish.yml` | CI/CD workflow | GitHub Actions, PyPI, GitHub Packages |
| GitHub Secrets | Credentials | `PYPI_API_TOKEN`, `GITHUB_TOKEN` |
| Git tags | Release markers | GitHub Actions trigger |

## Success Criteria

After release v6.3.0:

- ✅ Git tag `v6.3.0` created and pushed
- ✅ GitHub Actions workflow executed successfully
- ✅ Tests passed on Python 3.8-3.12
- ✅ Package published to PyPI
- ✅ Package published to GitHub Packages
- ✅ GitHub Release created with artifacts
- ✅ Can install: `pip install python-script-runner==6.3.0`

