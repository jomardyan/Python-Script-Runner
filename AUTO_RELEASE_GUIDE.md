# Automatic Release Guide

## 🚀 One-Command Release

The `auto-release` command performs a **complete automated release** from start to finish with zero interaction required.

### Quick Start

```bash
# Patch release (7.0.1 → 7.0.2)
bash release.sh auto-release

# Or explicitly:
bash release.sh auto-release patch

# Minor release (7.0.2 → 7.1.0)
bash release.sh auto-release minor

# Major release (7.1.0 → 8.0.0)
bash release.sh auto-release major
```

## What It Does

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

## Features

### ✅ Zero Interaction
- No prompts or confirmations
- Perfect for CI/CD pipelines
- Fully automated from start to finish

### ✅ Safe & Robust
- Auto-commits uncommitted changes (won't lose work)
- Handles existing tags (deletes and recreates)
- Continues on non-fatal errors (e.g., bundle build failures)
- Full error logging

### ✅ Fast
- Parallel bundle building
- Minimal validation overhead
- Optimized workflow

### ✅ Transparent
- Shows detailed progress
- Logs all operations
- Clear success/error messages

## Usage Examples

### Example 1: Simple Patch Release

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

### Example 2: Minor Release

```bash
$ bash release.sh auto-release minor

=== Fully Automatic Release (minor) ===
...
✅ Version bumped: 7.0.2 → 7.1.0
...
```

### Example 3: Major Release

```bash
$ bash release.sh auto-release major

=== Fully Automatic Release (major) ===
...
✅ Version bumped: 7.1.0 → 8.0.0
...
```

## CI/CD Integration

### GitHub Actions

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
          fetch-depth: 0  # Full history for version tracking
          
      - name: Configure Git
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          
      - name: Auto Release
        run: bash release.sh auto-release ${{ inputs.release_type }}
```

### GitLab CI

```yaml
release:
  stage: deploy
  only:
    - main
  when: manual
  variables:
    RELEASE_TYPE: "patch"  # Can override
  script:
    - git config user.name "GitLab CI"
    - git config user.email "ci@gitlab.com"
    - bash release.sh auto-release $RELEASE_TYPE
```

### Jenkins

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

## Environment Variables

The auto-release command respects these environment variables:

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

## Error Handling

### Non-Fatal Errors
These errors are logged but don't stop the release:
- Bundle build failures
- Clean operation failures
- Version file update warnings

### Fatal Errors
These errors stop the release:
- Invalid bump type
- Git tag creation failure
- Git push failure
- Version bump failure

### Recovery

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

## Comparison with Manual Release

| Aspect | Manual Release | Auto Release |
|--------|---------------|-------------|
| Commands | 5+ commands | 1 command |
| Time | ~5-10 minutes | ~30-60 seconds |
| Prompts | Multiple confirmations | Zero |
| Error prone | Yes (typos, forgotten steps) | No (automated) |
| CI/CD friendly | Requires scripting | Native support |
| Rollback | Manual | Automatic (on errors) |
| Logging | Limited | Comprehensive |

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

## Troubleshooting

### "Version bump failed"

**Cause**: version.sh script issues

**Solution**:
```bash
# Test version script
bash version.sh bump patch dry-run

# Check current version
bash version.sh current
```

### "Git push failed"

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

### "Tag already exists"

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

### "Bundle build failed (non-fatal)"

**Cause**: Missing build dependencies

**Solution**: This is non-fatal. Bundles are optional. GitHub Actions will build them.

To fix locally:
```bash
# Install dependencies
pip install -r requirements-build.txt

# Retry
bash release.sh auto-release patch
```

## Advanced Usage

### Scheduled Releases

```bash
# Cron job for weekly patch releases
0 0 * * 0 cd /path/to/repo && bash release.sh auto-release patch
```

### Conditional Releases

```bash
# Only release if tests pass
if bash release.sh validate; then
    bash release.sh auto-release patch
else
    echo "Validation failed, skipping release"
fi
```

### Multi-Branch Releases

```bash
# Release to different branches
git checkout develop
bash release.sh auto-release patch  # Creates v7.0.2-dev

git checkout main
bash release.sh auto-release patch  # Creates v7.0.2
```

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

## See Also

- [RELEASE_ENHANCEMENTS.md](RELEASE_ENHANCEMENTS.md) - Full feature documentation
- [RELEASE_QUICK_GUIDE.md](RELEASE_QUICK_GUIDE.md) - Quick reference
- [RELEASE_TUTORIAL.md](RELEASE_TUTORIAL.md) - Step-by-step manual guide

## Summary

```bash
# That's it! One command to rule them all:
bash release.sh auto-release patch

# Or with custom type:
bash release.sh auto-release minor  # For new features
bash release.sh auto-release major  # For breaking changes
```

**Happy automatic releasing! 🚀**
