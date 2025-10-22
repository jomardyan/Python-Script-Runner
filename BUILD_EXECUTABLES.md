# Building and Publishing Compiled Executables

This guide explains how to build and publish Windows EXE and Linux DEB compiled versions of Python Script Runner.

## Overview

The enhanced release script now supports building:

1. **Windows EXE** - Standalone executable (no Python required)
2. **Linux DEB** - Debian/Ubuntu package for easy system-wide installation
3. **Source Bundles** - Python source distributions (tar.gz, zip)
4. **PyPI Package** - Python package distribution

## Prerequisites

### For Windows EXE Building

```bash
# Install PyInstaller (required on the machine that will build the EXE)
pip install pyinstaller

# Or install globally
pip install -r requirements-dev.txt
```

### For Linux DEB Building

```bash
# Ensure dpkg-deb is installed (usually pre-installed on Debian/Ubuntu)
apt-get install dpkg-dev

# Or on Fedora/RHEL:
dnf install dpkg-dev
```

### General Requirements

```bash
# Core dependencies
pip install -r requirements.txt

# Development tools
pip install -r requirements-dev.txt
```

## Building Executables

### Build Windows EXE

```bash
# Build EXE for a specific version
bash release.sh build-exe 6.3.1

# This will:
# 1. Check/install PyInstaller
# 2. Generate runner.spec (if not exists)
# 3. Compile Python code to Windows EXE
# 4. Package with LICENSE, README, config.example.yaml
# 5. Create ZIP archive: dist/windows/python-script-runner-6.3.1-windows.zip
```

**Output:**
```
dist/windows/
├── python-script-runner-6.3.1-windows.zip
│   └── python-script-runner-6.3.1/
│       ├── python-script-runner.exe    # Standalone executable
│       ├── LICENSE
│       ├── README.md
│       └── config.example.yaml
└── dist/
    └── python-script-runner.exe         # Unzipped executable
```

**Installation on Windows:**
```bash
# Extract ZIP
unzip python-script-runner-6.3.1-windows.zip
cd python-script-runner-6.3.1

# Run directly (no Python installation needed!)
python-script-runner.exe script.py

# Or add to PATH for global access
set PATH=%PATH%;C:\path\to\executable\directory
```

### Build Linux DEB Package

```bash
# Build DEB for a specific version
bash release.sh build-deb 6.3.1

# This will:
# 1. Create Debian package structure
# 2. Copy application files to /usr/lib/python-script-runner
# 3. Create wrapper script in /usr/bin/python-script-runner
# 4. Generate control file with metadata
# 5. Create postinst script for dependency installation
# 6. Build DEB package: dist/linux/python-script-runner_6.3.1_all.deb
```

**Output:**
```
dist/linux/
└── python-script-runner_6.3.1_all.deb

# After installation, creates:
/usr/bin/python-script-runner                 # Executable command
/usr/lib/python-script-runner/                # Application files
  ├── runner.py
  ├── requirements.txt
  └── config.example.yaml
/usr/share/doc/python-script-runner/          # Documentation
  ├── copyright (LICENSE)
  └── README.md
```

**Installation on Linux:**
```bash
# Option 1: Direct installation
sudo apt install ./python-script-runner_6.3.1_all.deb

# Option 2: Add to repository and install
sudo dpkg -i python-script-runner_6.3.1_all.deb

# Option 3: Via repository
sudo apt-get install python-script-runner

# Then use globally:
python-script-runner script.py
```

## Complete Release Workflow

### Step 1: Bump Version

```bash
bash release.sh bump patch    # bumps X.Y.Z to X.Y.(Z+1)
bash release.sh bump minor    # bumps X.Y.Z to X.(Y+1).0
bash release.sh bump major    # bumps X.Y.Z to (X+1).0.0
```

### Step 2: Build Compiled Versions

```bash
# Get the new version
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

# Build Windows EXE
bash release.sh build-exe $VERSION

# Build Linux DEB
bash release.sh build-deb $VERSION

# Build source bundles
bash release.sh build-bundles
```

### Step 3: Prepare Release

```bash
bash release.sh prepare-release $VERSION

# This:
# - Updates version in source files
# - Commits to git
# - Creates version tag (v$VERSION)
```

### Step 4: Publish

```bash
bash release.sh publish $VERSION

# This:
# - Pushes tag to GitHub
# - Triggers GitHub Actions workflow
# - Automatically publishes to PyPI and GitHub Packages
```

### Step 5: Create GitHub Release with Assets

The GitHub Actions workflow automatically:

1. Validates the version
2. Runs tests (Python 3.8-3.11)
3. Builds Python distributions
4. Publishes to PyPI
5. Publishes to GitHub Packages
6. **Uploads compiled executables to GitHub Releases**

You can optionally manually upload the compiled files to the release:

```bash
# Upload Windows EXE
gh release upload v$VERSION dist/windows/python-script-runner-$VERSION-windows.zip

# Upload Linux DEB
gh release upload v$VERSION dist/linux/python-script-runner_${VERSION}_all.deb
```

## File Organization in dist/

After a complete build process:

```
dist/
├── windows/
│   ├── python-script-runner-6.3.1-windows.zip
│   ├── dist/
│   ├── build/
│   └── python-script-runner-6.3.1/
├── linux/
│   └── python-script-runner_6.3.1_all.deb
├── python3-runner.tar.gz
├── python3-runner.zip
├── pypy3-runner.tar.gz
├── pypy3-runner.zip
└── SHA256SUMS.txt
```

## PyInstaller Spec Configuration (runner.spec)

The `runner.spec` file configures how PyInstaller builds the executable:

```python
# Key settings:
- name='python-script-runner'    # Output executable name
- onefile=True                    # Create single .exe (not folder)
- console=True                    # Console application
- strip=False                     # Keep debug info
- upx=True                        # Use UPX compression
- hiddenimports=[...]             # Explicitly include dependencies
```

To customize the build:

1. Edit `runner.spec`
2. Run: `pyinstaller runner.spec`

## Distribution Channels

### 1. PyPI (Python Package Index)

```bash
# Automatic via GitHub Actions on version tag
pip install python-script-runner
```

### 2. GitHub Packages

```bash
# Automatic via GitHub Actions on version tag
pip install --extra-index-url https://python.pkg.github.com/jomardyan python-script-runner
```

### 3. GitHub Releases

```bash
# Manual or automatic upload of:
# - python-script-runner-X.Y.Z-windows.zip
# - python-script-runner_X.Y.Z_all.deb
# - Source distributions
# - SHA256 checksums
```

### 4. System Package Managers

**Future: Upload to:**
- Debian/Ubuntu: `software.opensuse.org` (OBS)
- Fedora/RHEL: `copr.fedorainfracloud.org`
- Homebrew: `homebrew-core` or `homebrew-cask`
- Scoop (Windows): `main-bucket`

Example for Homebrew:

```bash
# Create formulae/python-script-runner.rb
class PythonScriptRunner < Formula
  desc "Production-grade Python script execution engine"
  homepage "https://github.com/jomardyan/Python-Script-Runner"
  url "https://github.com/jomardyan/Python-Script-Runner/releases/download/v6.3.1/python-script-runner-6.3.1-macos.tar.gz"
  sha256 "..."
  depends_on "python@3.9"
end
```

## Troubleshooting

### Windows EXE Issues

**Problem:** "PyInstaller not found"
```bash
pip install pyinstaller
```

**Problem:** "Failed to build Windows executable"
- Check `runner.spec` syntax
- Verify all dependencies are installed
- Try on Windows or with appropriate cross-compilation setup

**Problem:** EXE won't start
- Check that all hidden imports are in `runner.spec`
- Add missing dependencies to `hiddenimports`

### Linux DEB Issues

**Problem:** "dpkg-deb command not found"
```bash
# Debian/Ubuntu
sudo apt-get install dpkg-dev

# Fedora/RHEL
sudo dnf install dpkg-dev
```

**Problem:** "Failed to build DEB package"
- Ensure directory structure is correct
- Check DEBIAN/control file syntax
- Verify all required fields are present

**Problem:** DEB installation fails
- Check dependencies: `dpkg --info python-script-runner_X.Y.Z_all.deb`
- Install dependencies manually: `python3-pip python3-psutil python3-yaml python3-requests`

## Performance and Size

### Windows EXE

- **Size:** ~50-80 MB (includes Python runtime)
- **Startup Time:** ~2-3 seconds (first time compilation cache)
- **Advantages:** No Python installation required, portable
- **Disadvantages:** Larger file size, antivirus false positives possible

### Linux DEB

- **Size:** ~5-10 MB (without dependencies)
- **Startup Time:** <100ms (pure Python)
- **Advantages:** Small size, integrates with system package management
- **Disadvantages:** Requires Python 3.6+ installed

## Security Considerations

### Windows EXE

- Consider code-signing the executable for distribution
- Test thoroughly on target Windows versions (7, 10, 11)
- Be aware of UAC (User Account Control) prompts
- Monitor for false positive antivirus detections

### Linux DEB

- Sign DEB package with GPG key
- Host on Debian repository with proper permissions
- Include changelog (debian/changelog)
- Test on target distributions (Ubuntu 18.04, 20.04, 22.04, etc.)

## Cleanup

```bash
# Remove build artifacts
rm -rf dist/windows/build dist/windows/dist dist/windows/*.egg-info
rm -rf build/ *.egg-info/

# Keep packaged versions
ls -lh dist/windows/python-script-runner-*.zip
ls -lh dist/linux/python-script-runner_*.deb
```

## Advanced: GitHub Actions Integration

The CI/CD pipeline automatically:

1. Builds on tag push (v*)
2. Creates matrix builds for multiple platforms
3. Uploads artifacts to GitHub Releases
4. Publishes to PyPI and GitHub Packages

See `.github/workflows/` for workflow files.

## References

- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [Debian Package Format](https://debian-handbook.info/browse/stable/index-pt-BR.html)
- [GitHub Releases API](https://docs.github.com/en/rest/releases)
- [Python Packaging Guide](https://packaging.python.org/)
