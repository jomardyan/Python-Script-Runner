# Release Management - Complete Guide

> Everything you need to know about releasing Python Script Runner v7.0.1+

## 📚 Documentation Structure

This release system includes multiple guides at different detail levels:

| Guide | Best For | Time | Format |
|-------|----------|------|--------|
| **RELEASE_QUICK_REFERENCE.md** | Copy-paste commands | 2 min | Cheat sheet |
| **RELEASE_TUTORIAL.md** | Learning the process | 10 min | Step-by-step |
| **RELEASE_ENHANCEMENTS.md** | Understanding features | 5 min | Overview |
| **README.md** (this file) | Complete reference | 15 min | Full guide |

---

## 🎯 Choose Your Path

### 👤 I'm in a hurry
→ Read: **RELEASE_QUICK_REFERENCE.md**
```bash
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

### 📖 I want to understand the process
→ Read: **RELEASE_TUTORIAL.md**
- Detailed step-by-step walkthrough
- Screenshots of expected output
- Common scenarios and solutions
- Timeline examples

### 🔧 I want to know what's new
→ Read: **RELEASE_ENHANCEMENTS.md**
- New features in v7
- Improvements from v6
- Performance characteristics
- Configuration options

### 🏗️ I need complete technical reference
→ Read: This file (README.md)
- Full architecture
- All command options
- Error handling
- Integration details

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           release.sh (Main Orchestrator)                │
└─────────────────────────────────────────────────────────┘
            ↓                                    ↓
    ┌──────────────────┐              ┌─────────────────────┐
    │   version.sh     │              │  GitHub Actions CI  │
    │                  │              │                     │
    │ • Semantic ver.  │              │ • Run tests         │
    │ • Tag mgmt       │              │ • Build wheels      │
    │ • File sync      │              │ • Publish PyPI      │
    └──────────────────┘              │ • Create Release    │
            ↓                         └─────────────────────┘
    ┌──────────────────┐
    │   Git (local)    │
    │                  │
    │ • Commits        │
    │ • Tags           │
    │ • Working tree   │
    └──────────────────┘
```

### Components

**release.sh** - Main command-line interface
- User-facing orchestrator
- Validates prerequisites
- Manages workflow

**version.sh** - Semantic versioning engine
- Bumps versions (major/minor/patch)
- Updates all version files atomically
- Manages git tags

**GitHub Actions** - CI/CD pipeline
- Triggered by git tag push (v*)
- Runs tests on multiple Python versions
- Builds and publishes to PyPI
- Creates GitHub Release

---

## 📋 Complete Command Reference

### `bash release.sh help`
Shows inline help with examples.

### `bash release.sh version`
Shows current version and latest git tag.

```bash
$ bash release.sh version
=== Python Script Runner Version Info ===
Current Version: 7.0.0
Latest Git Tag: v7.0.0
```

### `bash release.sh validate`
Runs comprehensive pre-release checks.

Checks:
- ✓ Required files exist
- ✓ Python 3.6+ installed
- ✓ Code compiles
- ✓ Dependencies installable
- ✓ Git repository clean
- ✓ GitHub reachable

### `bash release.sh bump <type> [dry-run]`
Bumps version semantically.

**Type options:**
- `patch` - 7.0.0 → 7.0.1 (bug fixes)
- `minor` - 7.0.0 → 7.1.0 (new features)
- `major` - 7.0.0 → 8.0.0 (breaking changes)

**With dry-run:**
- Preview changes without applying
- Useful for testing

**Auto-commits:**
- Detects uncommitted changes
- Stages all changes
- Commits with descriptive message

### `bash release.sh build-bundles`
Creates source distributions.

Creates:
- `dist/python3-runner.tar.gz` (1.5 MB)
- `dist/python3-runner.zip` (1.5 MB)
- `dist/pypy3-runner.tar.gz` (1.8 MB)
- `dist/pypy3-runner.zip` (1.8 MB)
- `dist/SHA256SUMS.txt` (checksums)

Each bundle includes:
- runner.py
- requirements.txt
- LICENSE
- README.md
- INSTALL.sh (installation script)

### `bash release.sh build-exe VERSION`
Builds Windows standalone executable.

**Requires:** PyInstaller
```bash
pip install pyinstaller
```

Creates:
- `dist/windows/python-script-runner-7.0.1-windows.zip` (50 MB)

Contains:
- `python-script-runner.exe` (standalone, no Python needed)

### `bash release.sh build-deb VERSION`
Builds Linux DEB package.

**Requires:** dpkg-deb (usually pre-installed)

Creates:
- `dist/linux/python-script-runner_7.0.1_all.deb` (2 MB)

Install with:
```bash
sudo apt install ./python-script-runner_7.0.1_all.deb
```

### `bash release.sh prepare-release VERSION`
Prepares release and creates git tag.

Steps:
1. Validates everything
2. Auto-commits any changes
3. Creates git tag (v7.0.1)

### `bash release.sh publish VERSION`
Publishes tag to GitHub.

Steps:
1. Verifies tag exists locally
2. Pushes to GitHub (`git push origin v7.0.1`)
3. Triggers GitHub Actions

---

## 🔄 Standard Release Workflow

### Workflow A: Simple Release (Recommended for most cases)

```bash
# 1. Check readiness
bash release.sh validate

# 2. Bump version (auto-commits)
bash release.sh bump patch
# Script outputs next command...

# 3. Create release tag
bash release.sh prepare-release 7.0.1

# 4. Publish to GitHub
bash release.sh publish 7.0.1

# GitHub Actions now:
# - Tests on Python 3.8-3.12
# - Builds distributions
# - Publishes to PyPI
# - Creates GitHub Release
```

### Workflow B: Full Release (with built artifacts)

```bash
# 1. Validate
bash release.sh validate

# 2. Bump version
bash release.sh bump patch

# 3. Build all packages
bash release.sh build-bundles
bash release.sh build-exe 7.0.1
bash release.sh build-deb 7.0.1

# 4. Prepare and publish
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1

# Now you have:
# - Source bundles (tar.gz, zip)
# - Windows EXE (standalone)
# - Linux DEB (installable)
# Plus: PyPI wheel and GitHub Release (automatic)
```

### Workflow C: Testing Before Release

```bash
# Preview version bump
bash release.sh bump patch dry-run

# Validate everything
bash release.sh validate

# Only then proceed with actual release
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

---

## ⚙️ Environment Setup

### Prerequisites
```bash
# Essential
git --version           # Must be installed
python3 --version      # Must be 3.6+
pip --version          # Python package manager

# For building Windows EXE
pip install pyinstaller

# For building Linux DEB (pre-installed on Linux)
dpkg-deb --version
```

### Git Setup
```bash
# Configure git user (if not already done)
git config user.name "Your Name"
git config user.email "your.email@example.com"

# Add GitHub remote (if not present)
git remote add origin https://github.com/jomardyan/Python-Script-Runner.git
```

### GitHub Setup
```bash
# Required Secrets in GitHub Repository Settings:
# Settings → Secrets → Actions

PyPI_API_TOKEN     # For publishing to PyPI
GITHUB_TOKEN       # Auto-provided by GitHub
```

---

## 🐛 Troubleshooting

### Issue: "Not a git repository"
```bash
# Error: Git repository not found
# Solution:
git init
git remote add origin <your-repo-url>
```

### Issue: "Uncommitted changes detected"
```bash
# Error: Working directory not clean
# Solution: Script auto-commits changes (recommended)
bash release.sh bump patch  # Will auto-commit!

# OR manually commit first:
git add -A
git commit -m "Your message"
```

### Issue: "Failed to install dependencies"
```bash
# Error: pip install failed
# Solution: Install manually first
python3 -m pip install --upgrade pip
pip install -r requirements.txt
bash release.sh validate
```

### Issue: "Tag vX.Y.Z already exists"
```bash
# Error: Version was already released
# Solution: Create a new patch release
bash release.sh bump patch
bash release.sh prepare-release X.Y.Z+1
```

### Issue: "Cannot reach github.com"
```bash
# Error: Offline mode
# Solution: Work offline, publish later
bash release.sh prepare-release 7.0.1  # Works offline
# When back online:
bash release.sh publish 7.0.1
```

### Issue: "PyInstaller not found"
```bash
# Error: Building Windows EXE failed
# Solution: Install PyInstaller
pip install pyinstaller
bash release.sh build-exe 7.0.1
```

### Issue: "dpkg-deb not found"
```bash
# Error: Building Linux DEB failed
# Solution: Install dpkg (only needed on Linux)
sudo apt-get install dpkg

# Or just skip DEB builds (not critical)
bash release.sh build-bundles  # Alternative: source-only
```

---

## 🔒 Safety & Best Practices

### Before Every Release

```bash
# 1. Validate
bash release.sh validate

# 2. Test locally
python -m pytest tests/

# 3. Check dependencies
pip list | grep -E "psutil|pyyaml|requests"

# 4. Review changes
git log --oneline -5

# 5. Then proceed
bash release.sh bump patch
```

### Commit Messages

Recommended format:
```
chore: bump version to 7.0.1
chore: prepare release v7.0.1
```

The script auto-generates these, but you can customize if needed.

### Version Numbering (Semantic Versioning)

```
MAJOR.MINOR.PATCH
  ↓      ↓       ↓
  7      0       1

Major: Breaking changes (8.0.0)
Minor: New features, backward compatible (7.1.0)
Patch: Bug fixes (7.0.1)
```

---

## 📊 Version File Locations

The release system updates these files automatically:

| File | Line | Example |
|------|------|---------|
| `runner.py` | 18 | `__version__ = "7.0.1"` |
| `pyproject.toml` | 7 | `version = "7.0.1"` |
| `runners/__init__.py` | 13 | `__version__ = "7.0.1"` |
| `__init__.py` | 43 | `__version__ = "7.0.1"` |

All updated atomically by `version.sh` → `release.sh` → `bump` command.

---

## 📈 Release Metrics

### Time Estimates
- Validate: ~5 seconds
- Bump: ~2 seconds
- Build bundles: ~10 seconds
- Build EXE: ~30 seconds
- Build DEB: ~5 seconds
- Prepare: ~2 seconds
- Publish: ~3 seconds
- **Total (minimal):** ~15 seconds
- **Total (with builds):** ~60 seconds

### File Sizes
- runner.py: ~250 KB
- Python 3 bundle: ~1.5 MB
- PyPy3 bundle: ~1.8 MB
- Windows EXE: ~50 MB
- Linux DEB: ~2 MB
- Source wheel: ~200 KB

### CI/CD Pipeline (GitHub Actions)
- Tests: ~5 minutes
- Build distributions: ~2 minutes
- Publish PyPI: ~1 minute
- Create Release: ~30 seconds
- **Total:** ~10 minutes (automatic)

---

## 🎯 When to Use Each Release Type

| Scenario | Type | Example |
|----------|------|---------|
| Bug fix, performance improvement | patch | 7.0.0 → 7.0.1 |
| New feature, backward compatible | minor | 7.0.0 → 7.1.0 |
| Breaking API changes, major update | major | 7.0.0 → 8.0.0 |

---

## 🔗 Integration Examples

### GitHub Actions Workflow Trigger
```yaml
# .github/workflows/release.yml
on:
  push:
    tags:
      - 'v*'  # Triggers on v7.0.1, v8.0.0, etc.
```

### CI/CD Environment Variables
```bash
# GitHub Actions provides automatically:
GITHUB_REF="refs/tags/v7.0.1"
GITHUB_TOKEN="<auto-provided>"
```

### PyPI Publishing
```bash
# Requires GitHub Secret:
PyPI_API_TOKEN="pypi-..."

# Used by GitHub Actions to publish:
twine upload dist/*
```

---

## 📞 Support & Resources

### Getting Help
```bash
# Inline help
bash release.sh help

# Quick reference
cat RELEASE_QUICK_REFERENCE.md

# Tutorial
cat RELEASE_TUTORIAL.md

# Feature overview
cat RELEASE_ENHANCEMENTS.md
```

### Related Files
- `.github/workflows/release.yml` - CI/CD automation
- `version.sh` - Version management
- `setup.py` - Package configuration
- `pyproject.toml` - Project metadata

### External Resources
- [Semantic Versioning](https://semver.org/)
- [PyPI Documentation](https://pypi.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

## ✅ Release Checklist

Before publishing a release:

- [ ] Run `bash release.sh validate` - all checks pass
- [ ] Review `git log` for significant changes
- [ ] Update CHANGELOG.md (if maintaining one)
- [ ] Run test suite: `python -m pytest tests/`
- [ ] Check Python version compatibility
- [ ] Run `bash release.sh bump <type>`
- [ ] Review bumped version files
- [ ] Build packages: `bash release.sh build-bundles`
- [ ] Test built packages locally
- [ ] Run `bash release.sh prepare-release X.Y.Z`
- [ ] Review git tag created
- [ ] Run `bash release.sh publish X.Y.Z`
- [ ] Monitor GitHub Actions workflow
- [ ] Verify PyPI package published
- [ ] Create GitHub Release notes (can be manual)

---

## 🎉 You're Ready!

You now have everything you need to confidently release Python Script Runner.

**Quick Start:**
```bash
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

**Happy releasing!** 🚀
