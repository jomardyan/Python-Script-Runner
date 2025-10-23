# Release Tutorial for Python Script Runner

> Simple step-by-step guide to releasing Python Script Runner v7.0.1+

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Git repository with remote named `origin`
- Python 3.6+ installed
- Write access to the repository
- (Optional) PyInstaller for Windows builds, dpkg-deb for Linux builds

### One-Command Release (Automated)
```bash
# Bump patch version and prepare everything
bash release.sh bump patch        # Step 1: Auto-bump version
bash release.sh prepare-release   # Step 2: Create release tag
bash release.sh publish           # Step 3: Push to GitHub
```

---

## 📋 Detailed Workflow

### Step 1: Check Current Version
```bash
bash release.sh version
```

**Output example:**
```
=== Python Script Runner Version Info ===
Current Version: 7.0.0
Latest Git Tag: v7.0.0
```

---

### Step 2: Run Validation
```bash
bash release.sh validate
```

**What it checks:**
- ✓ Required files exist (runner.py, requirements.txt, LICENSE, README.md)
- ✓ Python 3.6+ installed
- ✓ Code compiles without syntax errors
- ✓ Dependencies can be installed
- ✓ Git repository is clean
- ✓ GitHub connectivity

**Expected output:**
```
=== Pre-Release Validation ===
[Step 1] Checking project structure and dependencies
   ✓ runner.py
   ✓ requirements.txt
   ✓ LICENSE
   ✓ README.md
   ✓ pyproject.toml
✅ All required files present
...
✅ All validation checks passed!
```

---

### Step 3: Bump Version (Semantic Versioning)

#### Option A: Patch Release (7.0.0 → 7.0.1)
```bash
bash release.sh bump patch
```

#### Option B: Minor Release (7.0.0 → 7.1.0)
```bash
bash release.sh bump minor
```

#### Option C: Major Release (7.0.0 → 8.0.0)
```bash
bash release.sh bump major
```

#### Option D: Dry-run (Preview)
```bash
bash release.sh bump patch dry-run
```

**What it does:**
- Updates `__version__` in `runner.py`
- Updates `version` in `pyproject.toml`
- Updates `__version__` in `runners/__init__.py`
- Auto-commits changes with message: `chore: bump version to X.Y.Z`
- Shows next recommended step

**Example output:**
```
=== Automatic Version Bump (patch) ===
✅ Auto-committed changes: Auto-commit: uncommitted changes before version bump (patch)
✅ Version bump successful via version.sh

Next step: bash release.sh prepare-release 7.0.1
```

---

### Step 4: Build Packages (Optional)

#### Build Python Source Bundles
```bash
bash release.sh build-bundles
```

Creates:
- `dist/python3-runner.tar.gz` - Python 3 bundle
- `dist/python3-runner.zip` - Python 3 zip
- `dist/pypy3-runner.tar.gz` - PyPy3 bundle
- `dist/pypy3-runner.zip` - PyPy3 zip

#### Build Windows Executable
```bash
bash release.sh build-exe 7.0.1
```

Creates:
- `dist/windows/python-script-runner-7.0.1-windows.zip`
- Contains: `python-script-runner.exe` (standalone, no Python needed)

**Prerequisites:** PyInstaller
```bash
pip install pyinstaller
```

#### Build Linux DEB Package
```bash
bash release.sh build-deb 7.0.1
```

Creates:
- `dist/linux/python-script-runner_7.0.1_all.deb`

**Prerequisites:** dpkg-deb (usually pre-installed on Linux)

**To install the built DEB:**
```bash
sudo apt install ./dist/linux/python-script-runner_7.0.1_all.deb
```

---

### Step 5: Prepare Release
```bash
bash release.sh prepare-release 7.0.1
```

**What it does:**
- Validates all files are ready
- Auto-commits any remaining changes
- Creates git tag: `v7.0.1`
- Shows next steps

**Example output:**
```
=== Preparing Release v7.0.1 ===
[Step 1] Pre-Release Validation
✅ Git repository detected
✅ All validation checks passed!

[Step 2] Tagging Release
✅ Tag created: v7.0.1

📋 Release Preparation Summary:
   Version: 7.0.1
   Tag: v7.0.1

Next step: bash release.sh publish 7.0.1
```

---

### Step 6: Publish to GitHub
```bash
bash release.sh publish 7.0.1
```

**What it does:**
- Verifies tag `v7.0.1` exists
- Pushes tag to GitHub (`git push origin v7.0.1`)
- Triggers GitHub Actions workflows

**GitHub Actions will automatically:**
- Run tests on Python 3.8-3.12
- Build distribution packages (wheel + sdist)
- Publish to PyPI
- Publish to GitHub Packages
- Create GitHub Release with assets

**Expected output:**
```
=== Publishing Release v7.0.1 ===
✅ Tag pushed successfully

📋 GitHub Actions Workflow:
   The following steps will run automatically:
   ✓ Validate version in tag and source files
   ✓ Run tests on Python 3.8-3.12
   ✓ Build distributions (wheel + sdist)
   ✓ Publish to PyPI
   ✓ Publish to GitHub Packages
   ✓ Create GitHub Release with assets

🔗 Watch progress:
   https://github.com/jomardyan/Python-Script-Runner/actions

📦 Release URLs (once published):
   PyPI: https://pypi.org/project/python-script-runner/7.0.1/
   GitHub: https://github.com/jomardyan/Python-Script-Runner/releases/tag/v7.0.1
```

---

## 🔧 Advanced Scenarios

### Scenario 1: I Made Changes Before Release

**Problem:** You have uncommitted changes

**Solution:** The script handles this automatically!
```bash
bash release.sh bump patch
```

The script will:
1. Detect uncommitted changes
2. Stage them (`git add -A`)
3. Commit with message: `Auto-commit: uncommitted changes before version bump`
4. Continue with version bump

### Scenario 2: I Want to Skip Package Building

**Problem:** You only want to release to PyPI, not build EXE/DEB

**Solution:** Skip the build steps
```bash
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

GitHub Actions will handle building and publishing automatically.

### Scenario 3: Testing the Release Workflow

**Problem:** You want to test without pushing to GitHub

**Solution:** Use dry-run and local validation
```bash
bash release.sh bump patch dry-run        # Preview changes
bash release.sh validate                  # Check everything
# Manual testing...
bash release.sh bump patch                # Actually bump
```

### Scenario 4: Recovering from Release Mistakes

**Problem:** You pushed a release by accident

**Solution:** Use git to undo
```bash
# Undo the push (requires force push)
git push origin --delete v7.0.1           # Delete remote tag
git tag -d v7.0.1                         # Delete local tag

# Or create a new patch release
bash release.sh bump patch                # Creates v7.0.2
```

---

## 📊 Complete Release Timeline Example

```bash
# Monday 9:00 AM - Start release
bash release.sh version
bash release.sh validate

# Monday 9:15 AM - Bump version
bash release.sh bump patch
# Creates commit: "chore: bump version to 7.0.1"

# Monday 9:30 AM - Optional: Build standalone executables
bash release.sh build-exe 7.0.1
bash release.sh build-deb 7.0.1

# Monday 10:00 AM - Tag and release
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
# Creates tag: v7.0.1
# Pushes to GitHub

# Monday 10:05 AM - GitHub Actions runs (automatic)
# ✓ Tests pass on Python 3.8-3.12
# ✓ PyPI publish completes
# ✓ GitHub Packages publish completes

# Monday 10:15 AM - Release complete!
# PyPI: https://pypi.org/project/python-script-runner/7.0.1/
# GitHub: https://github.com/jomardyan/Python-Script-Runner/releases/tag/v7.0.1
```

---

## ⚠️ Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Running release commands out of order | May skip validation | Run `validate` before `prepare-release` |
| Not committing changes before bump | Version files out of sync | Script auto-commits, but verify with `git status` |
| Missing prerequisites (PyInstaller, dpkg-deb) | Build fails | Install optional dependencies first |
| No GitHub remote configured | Publish fails | Run `git remote add origin <url>` |
| Offline during publish | Tag not pushed | Run `publish` again when online |

---

## 🆘 Troubleshooting

### Error: "Not a git repository"
```bash
# Solution: Initialize git in directory
git init
git remote add origin https://github.com/jomardyan/Python-Script-Runner.git
```

### Error: "Uncommitted changes detected"
```bash
# Solution: Commit or stash changes
git add -A
git commit -m "Your message"
# Then retry release.sh
```

### Error: "Failed to install dependencies"
```bash
# Solution: Install dependencies manually
pip install -r requirements.txt
# Then retry
```

### Error: "Tag v7.0.1 already exists"
```bash
# Solution: Use a different version or delete old tag
git tag -d v7.0.1
git push origin --delete v7.0.1
# Then retry with correct version
```

### GitHub Actions Not Running
1. Check: https://github.com/jomardyan/Python-Script-Runner/actions
2. Look for workflow status
3. If failed, check logs for error details
4. Common cause: Missing `PyPI_API_TOKEN` in GitHub Secrets

---

## 📝 Summary

| Command | Purpose | Auto-commits? |
|---------|---------|---------------|
| `bash release.sh version` | Show current version | No |
| `bash release.sh validate` | Pre-release checks | No |
| `bash release.sh bump patch` | Bump to next patch | Yes |
| `bash release.sh build-bundles` | Build source packages | No |
| `bash release.sh build-exe VER` | Build Windows EXE | No |
| `bash release.sh build-deb VER` | Build Linux DEB | No |
| `bash release.sh prepare-release VER` | Create release tag | Yes |
| `bash release.sh publish VER` | Push to GitHub | No |

---

## 🎯 Next Steps

1. **For patch releases:** `bash release.sh bump patch`
2. **For minor releases:** `bash release.sh bump minor`
3. **For major releases:** `bash release.sh bump major`
4. **Then always:** `bash release.sh prepare-release && bash release.sh publish`

**Happy releasing! 🎉**
