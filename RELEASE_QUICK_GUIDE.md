# Release Script Quick Reference

## Quick Start

```bash
# ⭐ EASIEST - Fully automatic (recommended)
bash release.sh auto-release patch      # One command does everything!
bash release.sh auto-release minor      # For minor releases
bash release.sh auto-release major      # For major releases

# OR Manual step-by-step
bash release.sh bump patch              # 1. Bump version
bash release.sh validate                # 2. Validate
bash release.sh build-bundles           # 3. Build bundles
bash release.sh prepare-release X.Y.Z   # 4. Create tag
bash release.sh publish X.Y.Z           # 5. Push to GitHub
```

## Essential Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `auto-release` ⭐ | **Automatic release** (one command!) | `bash release.sh auto-release patch` |
| `status` | Show current state | `bash release.sh status` |
| `validate` | Check if ready to release | `bash release.sh validate` |
| `clean` | Remove build artifacts | `bash release.sh clean` |
| `bump` | Increment version | `bash release.sh bump patch` |
| `full-release` | Complete workflow | `bash release.sh full-release 1.2.3` |

## Environment Variables

```bash
# CI/CD mode
INTERACTIVE=false bash release.sh full-release 1.2.3

# Debug mode
DEBUG=true bash release.sh validate

# Skip tests
SKIP_TESTS=true bash release.sh validate

# Sequential builds
PARALLEL_BUILDS=false bash release.sh build-bundles
```

## Common Workflows

### Patch Release (Bug Fix)

```bash
bash release.sh bump patch
bash release.sh full-release $(grep 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
```

### Minor Release (New Feature)

```bash
bash release.sh bump minor
bash release.sh full-release $(grep 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
```

### Major Release (Breaking Change)

```bash
bash release.sh bump major
bash release.sh full-release $(grep 'version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
```

### Preview Version Bump

```bash
bash release.sh bump minor dry-run
```

### Build Only (No Release)

```bash
bash release.sh build-bundles
bash release.sh build-exe 1.2.3
bash release.sh build-deb 1.2.3
```

## Troubleshooting

### Check Logs

```bash
tail -f /tmp/release-*.log
```

### Failed Release

```bash
# Clean and retry
bash release.sh clean
bash release.sh validate
bash release.sh full-release 1.2.3
```

### Rollback Changes

When prompted after error, type `y` to rollback.

### Skip Interactive Prompts

```bash
INTERACTIVE=false bash release.sh command
```

## Status Codes

| Symbol | Meaning |
|--------|---------|
| ✅ | Success |
| ❌ | Error |
| ⚠️ | Warning |
| ℹ️ | Information |
| ▶ | Step in progress |

## Best Practices

1. ✅ Always run `status` before releasing
2. ✅ Run `validate` to catch issues early
3. ✅ Use `dry-run` to preview changes
4. ✅ Check logs if something fails
5. ✅ Clean between major releases
6. ❌ Don't skip validation in production
7. ❌ Don't ignore warnings

## Emergency Procedures

### Undo Last Commit

```bash
git reset --hard HEAD~1
```

### Delete Last Tag

```bash
git tag -d vX.Y.Z
git push origin :refs/tags/vX.Y.Z
```

### Force Clean

```bash
bash release.sh clean
git clean -fdx
```

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

## Performance Tips

- Use `PARALLEL_BUILDS=true` for faster bundle builds (default)
- Set `SKIP_TESTS=true` if tests are slow (use cautiously)
- Use `full-release` command to avoid repeated validation

## CI/CD Integration

### GitHub Actions

```yaml
- name: Release
  env:
    INTERACTIVE: false
    SKIP_TESTS: false
  run: bash release.sh full-release ${{ github.ref_name }}
```

### GitLab CI

```yaml
release:
  script:
    - export INTERACTIVE=false
    - bash release.sh full-release $CI_COMMIT_TAG
```

## Version Numbers

Format: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Examples:
- `1.0.0` → `1.0.1` (patch)
- `1.0.1` → `1.1.0` (minor)
- `1.1.0` → `2.0.0` (major)
