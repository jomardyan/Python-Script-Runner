# Release Management Guide

This document combines all release-related documentation for Python Script Runner.

## 📚 Contents

- [Quick Reference](#quick-reference)
- [Quick Start](#quick-start)
- [Automatic Release (Recommended)](#automatic-release-recommended)
- [Manual Release Workflow](#manual-release-workflow)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)

---

## Quick Reference

### One-Command Release (Fully Automatic)

```bash
# EASIEST WAY - One command does everything!
bash release.sh auto-release patch            # Automatic patch release (7.0.1 → 7.0.2)
bash release.sh auto-release minor            # Automatic minor release (7.0.1 → 7.1.0)
bash release.sh auto-release major            # Automatic major release (7.0.1 → 8.0.0)
```

### Common Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `auto-release` ⭐ | **Automatic release** (one command!) | `bash release.sh auto-release patch` |
| `status` | Show current state | `bash release.sh status` |
| `validate` | Check if ready to release | `bash release.sh validate` |
| `clean` | Remove build artifacts | `bash release.sh clean` |
| `bump` | Increment version | `bash release.sh bump patch` |
| `full-release` | Complete workflow | `bash release.sh full-release 1.2.3` |

---

## Quick Start

### Prerequisites

- Git repository with remote named `origin`
- Python 3.6+ installed
- Write access to the repository
- (Optional) PyInstaller for Windows builds, dpkg-deb for Linux builds

### Get Current Version

```bash
# Get the current version automatically
VERSION=$(grep '^version = ' pyproject.toml | head -1 | sed 's/version = "\(.*\)"/\1/')
echo "Current version: $VERSION"

# Or use the version command
bash release.sh version
```

### 30-Second Release

```bash
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
# Done! GitHub Actions handles the rest
```

---

## Automatic Release (Recommended)

### ⚡ One-Command Release

```bash
# EASIEST WAY - Fully automatic (recommended)
bash release.sh auto-release patch      # One command does everything!
bash release.sh auto-release minor      # For minor releases
bash release.sh auto-release major      # For major releases
```

### What It Does

The `auto-release` command automatically performs these steps:

1. **Cleans** previous build artifacts
2. **Auto-commits** any uncommitted changes
3. **Bumps** version (major/minor/patch)
4. **Commits** version changes
5. **Builds** release bundles (optional, non-fatal)
6. **Creates** git tag
7. **Pushes** commits to main branch
8. **Pushes** tag to GitHub (triggers CI/CD)

### Workflow Diagram

```
┌─────────────────────────────────────────────────────┐
│  bash release.sh auto-release patch                 │
└────────────────┬────────────────────────────────────┘
                 │
    ┌────────────▼───────────┐
    │ 1. Clean artifacts     │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 2. Auto-commit changes │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 3. Bump version        │
    │    7.0.1 → 7.0.2      │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 4. Commit bump         │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 5. Build bundles       │
    │    (optional)          │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 6. Create tag v7.0.2   │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 7. Push to main        │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 8. Push tag to GitHub  │
    └────────────┬───────────┘
                 │
    ┌────────────▼───────────┐
    │ 🎉 Release Complete!   │
    │                        │
    │ GitHub Actions runs:   │
    │ • Tests                │
    │ • Build & Publish      │
    │ • Create Release       │
    └────────────────────────┘
```

### Example Output

```bash
$ bash release.sh auto-release

=== Fully Automatic Release (patch) ===

ℹ️  🚀 Starting automated release workflow...
   Bump type: patch
   Mode: Fully automatic (no prompts)

▶ Step 1/6: Cleaning previous builds
✅ Cleaned 3 item(s)

▶ Step 2/6: Auto-committing uncommitted changes
ℹ️  No uncommitted changes

▶ Step 3/6: Bumping version (patch)
ℹ️  Current version: 7.0.1
✅ Version bumped: 7.0.1 → 7.0.2
✅ Version bump committed

▶ Step 4/6: Building release bundles
✅ Bundles built successfully

▶ Step 5/6: Preparing release v7.0.2
ℹ️  Version files updated
✅ Tag created: v7.0.2

▶ Step 6/6: Publishing to GitHub
✅ Commits pushed to main
✅ Tag pushed to GitHub

✅ 🎉 Automated Release Complete!

📋 Release Summary:
   Old Version: 7.0.1
   New Version: 7.0.2
   Git Tag: v7.0.2
   Branch: main

📦 GitHub Actions will now:
   ✓ Run tests on Python 3.8-3.12
   ✓ Build distributions (wheel + sdist)
   ✓ Publish to PyPI
   ✓ Publish to GitHub Packages
   ✓ Create GitHub Release with assets

🔗 Monitor progress:
   https://github.com/jomardyan/Python-Script-Runner/actions

📦 Release URLs (once published):
   PyPI: https://pypi.org/project/python-script-runner/7.0.2/
   GitHub: https://github.com/jomardyan/Python-Script-Runner/releases/tag/v7.0.2
```

### Features

#### ✅ Zero Interaction
- No prompts or confirmations
- Perfect for CI/CD pipelines
- Fully automated from start to finish

#### ✅ Safe & Robust
- Auto-commits uncommitted changes (won't lose work)
- Handles existing tags (deletes and recreates)
- Continues on non-fatal errors (e.g., bundle build failures)
- Full error logging

#### ✅ Fast
- Parallel bundle building
- Minimal validation overhead
- Optimized workflow

#### ✅ Transparent
- Shows detailed progress
- Logs all operations
- Clear success/error messages

---

## Manual Release Workflow

### Step 1: Check Current Version

```bash
bash release.sh version
```

### Step 2: Run Validation

```bash
bash release.sh validate
```

### Step 3: Bump Version

#### Patch Release (Bug Fix)
```bash
bash release.sh bump patch     # 7.0.0 → 7.0.1
```

#### Minor Release (New Feature)
```bash
bash release.sh bump minor     # 7.0.0 → 7.1.0
```

#### Major Release (Breaking Change)
```bash
bash release.sh bump major     # 7.0.0 → 8.0.0
```

#### Preview Changes (Dry-run)
```bash
bash release.sh bump patch dry-run
```

### Step 4: Build Packages (Optional)

#### Build Python Source Bundles
```bash
bash release.sh build-bundles
```

#### Build Windows Executable
```bash
bash release.sh build-exe 7.0.1
```

#### Build Linux DEB Package
```bash
bash release.sh build-deb 7.0.1
```

### Step 5: Prepare Release

```bash
bash release.sh prepare-release 7.0.1
```

### Step 6: Publish to GitHub

```bash
bash release.sh publish 7.0.1
```

GitHub Actions will automatically:
- Run tests on Python 3.8-3.12
- Build distribution packages (wheel + sdist)
- Publish to PyPI
- Publish to GitHub Packages
- Create GitHub Release with assets

---

## Advanced Features

### Environment Variables

```bash
# Enable debug logging
DEBUG=true bash release.sh auto-release

# Skip parallel builds (slower but more stable)
PARALLEL_BUILDS=false bash release.sh auto-release

# Custom log file
LOG_FILE=/var/log/release.log bash release.sh auto-release

# Skip tests (faster, use cautiously)
SKIP_TESTS=true bash release.sh auto-release
```

### CI/CD Integration

#### GitHub Actions

```yaml
name: Auto Release
on:
  workflow_dispatch:
    inputs:
      release_type:
        description: 'Release type'
        required: true
        type: choice
        options:
          - patch
          - minor
          - major

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
          
      - name: Configure Git
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          
      - name: Auto Release
        run: bash release.sh auto-release ${{ inputs.release_type }}
```

#### GitLab CI

```yaml
release:
  stage: deploy
  only:
    - main
  when: manual
  variables:
    RELEASE_TYPE: "patch"
  script:
    - git config user.name "GitLab CI"
    - git config user.email "ci@gitlab.com"
    - bash release.sh auto-release $RELEASE_TYPE
```

#### Jenkins

```groovy
pipeline {
    agent any
    parameters {
        choice(name: 'RELEASE_TYPE', choices: ['patch', 'minor', 'major'], description: 'Release type')
    }
    stages {
        stage('Release') {
            steps {
                sh '''
                    git config user.name "Jenkins"
                    git config user.email "jenkins@example.com"
                    bash release.sh auto-release ${RELEASE_TYPE}
                '''
            }
        }
    }
}
```

### Error Handling

#### Non-Fatal Errors
These errors are logged but don't stop the release:
- Bundle build failures
- Clean operation failures
- Version file update warnings

#### Fatal Errors
These errors stop the release:
- Invalid bump type
- Git tag creation failure
- Git push failure
- Version bump failure

#### Recovery

If the auto-release fails:

```bash
# Check the log
tail -100 /tmp/release-*.log | grep ERROR

# Check current status
bash release.sh status

# Clean and retry
bash release.sh clean
bash release.sh auto-release patch
```

---

## Troubleshooting

### Error: "Not a git repository"

**Cause**: Not in a git repository

**Solution**:
```bash
git init
git remote add origin https://github.com/your/repo.git
```

### Error: "Uncommitted changes detected"

**Cause**: Uncommitted changes in working directory

**Solution**:
```bash
# Option 1: Commit them yourself
git add -A
git commit -m "Your changes"

# Option 2: Let the script auto-commit (it will)
bash release.sh bump patch
```

### Error: "Version bump failed"

**Cause**: version.sh script issues

**Solution**:
```bash
# Test version script
bash version.sh bump patch dry-run

# Check current version
bash version.sh current
```

### Error: "Git push failed"

**Cause**: No push permissions or network issues

**Solution**:
```bash
# Check git remote
git remote -v

# Test connection
git fetch origin

# Check credentials
git config user.name
git config user.email
```

### Error: "Tag already exists"

**Cause**: Tag was created before

**Solution**: Auto-release handles this automatically (deletes and recreates)

If manual cleanup needed:
```bash
# Delete local and remote tag
git tag -d v7.0.2
git push origin :refs/tags/v7.0.2

# Then retry
bash release.sh auto-release patch
```

### GitHub Actions Not Running

1. Check: https://github.com/jomardyan/Python-Script-Runner/actions
2. Look for workflow status
3. If failed, check logs for error details
4. Common cause: Missing `PyPI_API_TOKEN` in GitHub Secrets

---

## Best Practices

### 1. Test Before Release

```bash
# Check status first
bash release.sh status

# Validate codebase
bash release.sh validate

# Then release
bash release.sh auto-release patch
```

### 2. Use in CI/CD

Make releases consistent and reproducible:

```bash
# In your CI/CD pipeline
if [ "$CI" = "true" ]; then
    bash release.sh auto-release ${RELEASE_TYPE:-patch}
fi
```

### 3. Monitor Logs

Always check logs after release:

```bash
# View latest log
ls -t /tmp/release-*.log | head -1 | xargs cat
```

### 4. Version Strategy

- **Patch**: Bug fixes, no new features (7.0.1 → 7.0.2)
- **Minor**: New features, backward compatible (7.0.2 → 7.1.0)
- **Major**: Breaking changes (7.1.0 → 8.0.0)

---

## Performance Tips

- Use `PARALLEL_BUILDS=true` for faster bundle builds (default)
- Set `SKIP_TESTS=true` if tests are slow (use cautiously)
- Use `full-release` command to avoid repeated validation

---

## FAQs

**Q: Can I use auto-release locally?**
A: Yes! It works anywhere - local dev machine, CI/CD, servers.

**Q: What if I have uncommitted changes?**
A: They're automatically committed before the release.

**Q: Can I cancel mid-release?**
A: Press Ctrl+C. Rollback will be offered (if interactive mode was on).

**Q: Does it run tests?**
A: No, for speed. Run `validate` before if needed. GitHub Actions runs tests.

**Q: What about changelog?**
A: Not automated yet. Update manually or use tools like `conventional-changelog`.

**Q: Can I customize the workflow?**
A: Yes! Edit `cmd_auto_release()` in `release.sh`.

---

## Getting Help

```bash
bash release.sh help
```

## Log Files

Location: `/tmp/release-YYYYMMDD-HHMMSS.log`

View latest:
```bash
ls -lt /tmp/release-*.log | head -1 | awk '{print $NF}' | xargs tail -100
```

---

**Happy releasing! 🎉**
