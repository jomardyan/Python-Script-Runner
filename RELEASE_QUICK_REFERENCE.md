# release.sh Quick Reference

> **TL;DR Guide** - Copy/paste commands for common release scenarios

## ⚡ 30-Second Release

```bash
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
# Done! GitHub Actions handles the rest
```

## 🎯 Common Commands

### Check Status
```bash
bash release.sh version        # What's the current version?
bash release.sh validate       # Ready to release?
```

### Bump Version (Pick One)
```bash
bash release.sh bump patch     # 7.0.0 → 7.0.1 (bug fixes)
bash release.sh bump minor     # 7.0.0 → 7.1.0 (new features)
bash release.sh bump major     # 7.0.0 → 8.0.0 (breaking)
```

### Build Packages
```bash
bash release.sh build-bundles  # Python source (tar.gz + zip)
bash release.sh build-exe 7.0.1       # Windows EXE
bash release.sh build-deb 7.0.1       # Linux DEB
```

### Release
```bash
bash release.sh prepare-release 7.0.1 # Create tag
bash release.sh publish 7.0.1         # Push to GitHub
```

---

## 🚀 Full Release Workflow

```bash
# Step 1: Validate everything is ready
bash release.sh validate

# Step 2: Bump version (auto-commits changes)
bash release.sh bump patch
# Script outputs: "Next step: bash release.sh prepare-release 7.0.1"

# Step 3: Optional - build standalone packages
bash release.sh build-exe 7.0.1
bash release.sh build-deb 7.0.1

# Step 4: Create release tag
bash release.sh prepare-release 7.0.1

# Step 5: Push to GitHub (triggers CI/CD)
bash release.sh publish 7.0.1

# Step 6: Watch GitHub Actions
# https://github.com/jomardyan/Python-Script-Runner/actions
```

---

## 🧪 Test Release (Dry-Run)

```bash
bash release.sh bump patch dry-run    # Preview what would happen
# Don't worry, this doesn't change anything!
```

---

## 🔍 Troubleshooting

### Error: "Not a git repository"
```bash
git init
git remote add origin https://github.com/jomardyan/Python-Script-Runner.git
```

### Error: "Uncommitted changes detected"
```bash
# Option 1: Commit them yourself
git add -A
git commit -m "Your changes"

# Option 2: Let the script auto-commit (it will)
bash release.sh bump patch  # Auto-commits changes!
```

### Error: "Failed to install dependencies"
```bash
pip install -r requirements.txt
bash release.sh validate  # Retry
```

### Error: "No git remote 'origin' configured"
```bash
git remote add origin https://github.com/your/repo.git
```

---

## 📦 What Gets Built

### `build-bundles`
- ✓ `dist/python3-runner.tar.gz` (4 MB)
- ✓ `dist/python3-runner.zip` (4 MB)
- ✓ `dist/pypy3-runner.tar.gz` (5 MB)
- ✓ `dist/pypy3-runner.zip` (5 MB)
- ✓ `dist/SHA256SUMS.txt`

### `build-exe 7.0.1`
- ✓ `dist/windows/python-script-runner-7.0.1-windows.zip` (50 MB)
  - Contains: `python-script-runner.exe` (standalone)

### `build-deb 7.0.1`
- ✓ `dist/linux/python-script-runner_7.0.1_all.deb` (2 MB)
  - Install: `sudo apt install ./python-script-runner_7.0.1_all.deb`

---

## 🎬 Real Examples

### Example 1: Patch Release (Bug Fix)
```bash
# Fixing a bug? Use patch
bash release.sh bump patch
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

### Example 2: Minor Release (New Feature)
```bash
# Adding a feature? Use minor
bash release.sh bump minor
bash release.sh prepare-release 7.1.0
bash release.sh publish 7.1.0
```

### Example 3: Major Release (Breaking Change)
```bash
# Breaking changes? Use major
bash release.sh bump major
bash release.sh prepare-release 8.0.0
bash release.sh publish 8.0.0
```

### Example 4: Custom Builds
```bash
# Want standalone EXE or DEB?
bash release.sh build-bundles
bash release.sh build-exe 7.0.1
bash release.sh build-deb 7.0.1

# Then release as usual:
bash release.sh prepare-release 7.0.1
bash release.sh publish 7.0.1
```

---

## ⏱️ How Long Does It Take?

| Task | Time |
|------|------|
| Validate | 5 sec |
| Bump version | 2 sec |
| Build bundles | 10 sec |
| Build EXE | 30 sec |
| Build DEB | 5 sec |
| Prepare release | 2 sec |
| Publish | 3 sec |
| **Total (with all builds)** | **~60 sec** |

*Then GitHub Actions runs automatically (5-15 min):*
- Tests on Python 3.8-3.12
- Builds distributions
- Publishes to PyPI
- Creates GitHub Release

---

## 🆘 Get Help

```bash
bash release.sh help           # Show full help
cat RELEASE_TUTORIAL.md        # Detailed guide
cat RELEASE_ENHANCEMENTS.md    # Feature overview
```

---

**Happy releasing! 🎉**
