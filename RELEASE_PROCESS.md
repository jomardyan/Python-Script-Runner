# Release Process

This document describes how to create and publish releases for Python Script Runner.

## Overview

The release process is automated using GitHub Actions. Two distributions are automatically built and published:

1. **Python 3 Distribution** - Optimized for CPython 3.6+
2. **PyPy3 Distribution** - High-performance variant (27.3x faster for CPU-bound work)

Each distribution includes:
- Main application (`runner.py`)
- Production dependencies only (`requirements.txt`)
- Configuration template (`config.example.yaml`)
- Automated installer (`INSTALL.sh`)
- Complete documentation (`README.md`)
- License and checksums

## Release Workflow

### Step 1: Validate Code

Before releasing, run validation checks:

```bash
bash release.sh validate
```

This will:
- ✅ Compile Python code
- ✅ Verify dependencies install cleanly
- ✅ Check all required files are present
- ✅ Ensure no development artifacts remain
- ✅ Verify git working directory is clean

### Step 2: Prepare Release

Create a git tag for the release:

```bash
bash release.sh prepare-release 3.0.1
```

This will:
- Run all validation checks again
- Create an annotated git tag `v3.0.1`
- Display next steps

### Step 3: Publish Release

Push the tag to GitHub to trigger the automated build:

```bash
bash release.sh publish 3.0.1
```

This will:
- Push the tag to GitHub
- Trigger the GitHub Actions workflow
- Build both Python 3 and PyPy3 distributions
- Create a GitHub Release with all artifacts

### Step 4: Monitor Build

Watch the build progress on GitHub:
https://github.com/jomardyan/Python-Script-Runner/actions

The workflow will:
1. Test on both Python 3 and PyPy3
2. Build Python 3 bundle (tar.gz + zip)
3. Build PyPy3 bundle (tar.gz + zip)
4. Create GitHub Release with all files
5. Generate SHA256 checksums

## Release Structure

### GitHub Artifacts

Each release contains:
- `python3-runner-vX.Y.Z.tar.gz` - Python 3 Linux/macOS bundle
- `python3-runner-vX.Y.Z.zip` - Python 3 cross-platform bundle
- `pypy3-runner-vX.Y.Z.tar.gz` - PyPy3 Linux/macOS bundle
- `pypy3-runner-vX.Y.Z.zip` - PyPy3 cross-platform bundle
- `SHA256SUMS.txt` - File integrity checksums
- `RELEASE_NOTES.md` - Release documentation

### Bundle Contents

```
python3-runner/
├── runner.py              # Main application
├── requirements.txt       # Production dependencies
├── LICENSE                # MIT License
├── README.md              # Full documentation
├── config.example.yaml    # Configuration template
├── INSTALL.sh             # Linux/macOS installer
└── BUNDLE_README.md       # Quick start guide

pypy3-runner/
├── runner.py              # Main application
├── requirements.txt       # Production dependencies
├── requirements-pypy3.txt # PyPy3 optimizations
├── LICENSE                # MIT License
├── README.md              # Full documentation
├── config.example.yaml    # Configuration template
├── INSTALL.sh             # Linux/macOS installer (includes PyPy3 setup)
└── BUNDLE_README.md       # Quick start guide
```

## Version Numbering

Use semantic versioning: `MAJOR.MINOR.PATCH`

- `MAJOR`: Breaking changes or major feature release
- `MINOR`: New features, backwards compatible
- `PATCH`: Bug fixes and patches

Example: `3.0.1` = Major version 3, minor version 0, patch level 1

## Installation from Release

### Python 3

```bash
# Extract
tar xzf python3-runner-v3.0.1.tar.gz
cd python3-runner

# Install
bash INSTALL.sh

# Run
python3 runner.py your_script.py --help
```

### PyPy3

```bash
# Extract
tar xzf pypy3-runner-v3.0.1.tar.gz
cd pypy3-runner

# Install (auto-detects and installs PyPy3 if needed)
bash INSTALL.sh

# Run
pypy3 runner.py your_script.py --help
```

## Verification

Verify downloaded files using SHA256:

```bash
sha256sum -c SHA256SUMS.txt
```

## Troubleshooting

### Tag Already Exists

If you see "tag already exists", either:
1. Use a different version number
2. Delete the tag: `git tag -d v3.0.1 && git push origin :v3.0.1`

### Validation Fails

Run: `bash release.sh validate` to see specific issues

Common issues:
- Uncommitted changes: `git status`
- Missing files: Check all required files are present
- Dependency issues: `pip install -r requirements.txt`

### Build Fails on GitHub Actions

Check the workflow logs at: https://github.com/jomardyan/Python-Script-Runner/actions

Common issues:
- Python version mismatch: Verify `python-version` in workflow
- Missing secrets: Ensure `GITHUB_TOKEN` has write permissions
- Dependency conflicts: Test locally with `pip install -r requirements.txt`

## Local Bundle Testing

To build and test bundles locally:

```bash
bash release.sh validate           # Pre-flight checks
bash release.sh build-bundles      # Build tar.gz and zip files
```

This creates bundles in the `dist/` directory without creating a git tag.

## Cleanup After Release

Remove local build artifacts:

```bash
rm -rf dist/
```

## CI/CD Integration

The workflow is defined in `.github/workflows/release.yml`

Triggers: When a git tag matching `v*.*.*` is pushed

Jobs:
1. `test` - Test on Python 3 and PyPy3
2. `build-python3` - Build Python 3 distribution
3. `build-pypy3` - Build PyPy3 distribution
4. `create-release` - Create GitHub Release with artifacts

## Development Workflow

During development:
1. Make changes and commit
2. Run tests: `pytest test_script.py`
3. Code quality: `flake8 runner.py`
4. When ready to release, follow the release process above

## Rollback

If a release has issues:
1. Delete the release on GitHub UI
2. Delete the tag: `git tag -d vX.Y.Z && git push origin :vX.Y.Z`
3. Fix issues locally
4. Create new release with corrected code

## Support

For issues with the release process:
- Check GitHub Actions logs
- Verify git configuration: `git config --list`
- Ensure you have write access to the repository
