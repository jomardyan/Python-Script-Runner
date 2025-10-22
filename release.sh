#!/bin/bash
# Release management script for Python Script Runner
# Automates versioning, tagging, and release preparation
# Integrates with version.sh for semantic versioning and GitHub Actions CI/CD

set -euo pipefail

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    print_error "Script failed at line $line_number with exit code $exit_code"
    exit "$exit_code"
}

# Script directory and integration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_SCRIPT="${SCRIPT_DIR}/version.sh"
GITHUB_WORKFLOWS_DIR="${SCRIPT_DIR}/.github/workflows"

# Configuration
VERSION_FILE="pyproject.toml"
RUNNER_FILE="runner.py"
INIT_FILE="__init__.py"
PACKAGE_VERSION="${RELEASE_VERSION:-}"

# Validate required files exist
check_files_exist() {
    local files=("$@")
    for file in "${files[@]}"; do
        if [ ! -f "$file" ]; then
            print_error "Required file not found: $file"
            exit 1
        fi
    done
}

# Validate command exists
check_command_exists() {
    if ! command -v "$1" &> /dev/null; then
        print_error "Required command not found: $1"
        exit 1
    fi
}

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Auto-commit any uncommitted changes
auto_commit_changes() {
    local commit_message="${1:-Auto-commit uncommitted changes before release}"
    
    # Check if there are any uncommitted changes
    if git diff-index --quiet HEAD -- 2>/dev/null; then
        print_success "No uncommitted changes to commit"
        return 0
    fi
    
    print_header "Auto-committing Uncommitted Changes"
    
    # Check if we're in a git repository
    if ! git rev-parse --is-inside-work-tree &> /dev/null; then
        print_warning "Not in a git repository, skipping auto-commit"
        return 0
    fi
    
    # Get list of changed files
    echo "Uncommitted changes detected:"
    git status -s
    echo ""
    
    # Stash current changes, commit them
    print_warning "Automatically staging and committing changes..."
    
    # Add all changes
    git add -A
    
    # Check if there's anything staged
    if git diff-index --quiet --cached HEAD -- 2>/dev/null; then
        print_warning "No changes to commit after staging"
        return 0
    fi
    
    # Configure git if needed (for CI/CD environments)
    if ! git config user.email &> /dev/null; then
        git config user.email "automation@localhost"
        git config user.name "Automation Script"
    fi
    
    # Commit the changes
    if git commit -m "$commit_message" 2>&1; then
        print_success "Auto-committed changes: $commit_message"
        echo "Committed files:"
        git log -1 --name-status --pretty=format:""
        return 0
    else
        print_error "Failed to auto-commit changes"
        git reset HEAD .
        return 1
    fi
}

show_help() {
    cat << EOF
Python Script Runner - Release Management

INTEGRATED TOOLS:
  • version.sh    - Semantic versioning (bump, set, validate, sync)
  • release.sh    - Release orchestration (workflow integration)
  • GitHub Actions - Automated testing and publishing

Features:
  • Automatic uncommitted changes detection and commit before release
  • Semantic versioning with major/minor/patch bumping
  • Cross-platform executable building (Windows EXE, Linux DEB)
  • GitHub Actions CI/CD workflow integration

Usage: bash release.sh [command] [options]

Commands:
  version              Show current version and latest git tag
  bump (major|minor|patch) [dry-run]
                      Bump version using version.sh (auto-updates files)
                      ⚠️  Auto-commits any uncommitted changes before bumping
  validate            Run pre-release validation checks
  build-bundles       Build Python source bundles (tar.gz, zip)
  build-exe VER       Build Windows EXE executable using PyInstaller
  build-deb VER       Build Linux DEB package
  prepare-release VER Prepare release: update files, create git tag
                      ⚠️  Auto-commits any uncommitted changes before preparing
  publish VER         Push tag to GitHub (triggers GitHub Actions workflow)
  help                Show this help message

Workflow:
  1. bash release.sh bump patch              # Auto-bump version (auto-commits)
  2. bash release.sh build-exe X.Y.Z         # Build Windows executable
  3. bash release.sh build-deb X.Y.Z         # Build Linux DEB package
  4. bash release.sh prepare-release X.Y.Z   # Create and tag release (auto-commits)
  5. bash release.sh publish X.Y.Z           # Push tag to GitHub
  6. GitHub Actions will auto-build and publish to PyPI & GitHub Packages

Options:
  X.Y.Z             Version in semantic versioning format
  dry-run           Preview changes without applying them

Examples:
  bash release.sh version                    # Show current version
  bash release.sh bump patch                 # Bump to next patch (auto-commits changes)
  bash release.sh bump minor dry-run         # Preview minor bump
  bash release.sh validate                   # Run validation checks
  bash release.sh build-bundles              # Build source bundles
  bash release.sh build-exe 6.3.0            # Build Windows EXE
  bash release.sh build-deb 6.3.0            # Build Linux DEB
  bash release.sh prepare-release 6.3.0      # Prepare v6.3.0 release
  bash release.sh publish 6.3.0              # Trigger GitHub Actions

Integration Points:
  • version.sh is used for version management
  • PyInstaller for Windows EXE compilation
  • dpkg-deb for Linux DEB packaging
  • GitHub Actions triggers on tag push (v*)
  • PyPI_API_TOKEN secret required in GitHub Secrets
  • GITHUB_TOKEN auto-provided for GitHub Packages

See RELEASING.md for detailed guide and troubleshooting.

EOF
}

get_version() {
    local version
    
    if [ -f "$VERSION_FILE" ]; then
        version=$(grep '^version = ' "$VERSION_FILE" 2>/dev/null | sed 's/version = "\(.*\)"/\1/' || echo "")
        if [ -n "$version" ]; then
            echo "$version"
            return 0
        fi
    fi
    
    if [ -n "$PACKAGE_VERSION" ]; then
        echo "$PACKAGE_VERSION"
        return 0
    fi
    
    print_error "Unable to determine version"
    return 1
}

validate_version() {
    local version=$1
    if [[ ! $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        print_error "Invalid version format: $version"
        echo "Expected format: MAJOR.MINOR.PATCH (e.g., 3.0.1)"
        exit 1
    fi
}

cmd_version() {
    print_header "Python Script Runner Version Info"
    
    local version
    if [ -f "pyproject.toml" ]; then
        version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' 2>/dev/null) || version="unknown"
        if [ -z "$version" ]; then
            version="unknown"
        fi
        echo "Current Version: $version"
    else
        if [ -n "$PACKAGE_VERSION" ]; then
            echo "Current Version: $PACKAGE_VERSION"
        else
            echo "Current Version: unknown"
        fi
    fi
    
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local git_tag
        if git_tag=$(git describe --tags --abbrev=0 2>/dev/null); then
            echo "Latest Git Tag: $git_tag"
        else
            echo "Latest Git Tag: None"
        fi
    else
        echo "Latest Git Tag: Not a git repository"
    fi
}

cmd_bump() {
    local bump_type=$1
    local dry_run=${2:-}
    
    if [ -z "$bump_type" ]; then
        print_error "Bump type required (major|minor|patch)"
        exit 1
    fi
    
    if [ "$bump_type" != "major" ] && [ "$bump_type" != "minor" ] && [ "$bump_type" != "patch" ]; then
        print_error "Invalid bump type: $bump_type"
        exit 1
    fi
    
    print_header "Automatic Version Bump ($bump_type)"
    
    # Auto-commit any uncommitted changes before bumping (only for actual bump, not dry-run)
    if [ "$dry_run" != "dry-run" ]; then
        auto_commit_changes "Auto-commit: uncommitted changes before version bump ($bump_type)"
    fi
    
    # Check if version.sh exists
    if [ ! -f "$VERSION_SCRIPT" ]; then
        print_error "version.sh not found at $VERSION_SCRIPT"
        exit 1
    fi
    
    # Validate before bump
    if [ "$dry_run" != "dry-run" ]; then
        print_warning "Running pre-bump validation..."
        cmd_validate || exit 1
    fi
    
    # Use version.sh to bump version
    print_warning "Delegating to version.sh for version bump..."
    if [ "$dry_run" = "dry-run" ]; then
        if bash "$VERSION_SCRIPT" bump "$bump_type" dry-run > /dev/null 2>&1; then
            print_success "Dry-run completed successfully"
            bash "$VERSION_SCRIPT" bump "$bump_type" dry-run
        else
            print_error "Dry-run failed"
            exit 1
        fi
    else
        if bash "$VERSION_SCRIPT" bump "$bump_type" > /dev/null 2>&1; then
            print_success "Version bump successful via version.sh"
        else
            print_error "Version bump failed"
            exit 1
        fi
        
        # Get new version
        local new_version
        new_version=$(bash "$VERSION_SCRIPT" current) || { print_error "Failed to get version"; exit 1; }
        
        # Stage all version files
        print_warning "Staging version files..."
        for file in "$VERSION_FILE" "$RUNNER_FILE" "$INIT_FILE"; do
            if [ -f "$file" ]; then
                git add "$file" || { print_error "Failed to stage $file"; exit 1; }
            fi
        done
        
        # Commit changes
        print_warning "Committing version bump..."
        if git commit -m "chore: bump version to $new_version" > /dev/null 2>&1; then
            print_success "Committed version bump to git"
        else
            print_warning "No version changes to commit"
        fi
        
        echo ""
        echo "Next step: bash release.sh prepare-release $new_version"
    fi
}

cmd_validate() {
    print_header "Pre-Release Validation"
    
    # Check required files
    print_warning "Checking for required files..."
    local required_files=("runner.py" "requirements.txt" "LICENSE" "README.md")
    check_files_exist "${required_files[@]}" || exit 1
    print_success "All required files present"
    
    # Check Python compilation
    print_warning "Checking code quality..."
    if ! python3 -m py_compile runner.py test_script.py 2>/dev/null; then
        print_error "Python compilation failed"
        exit 1
    fi
    print_success "Compilation successful"
    
    # Check dependencies
    print_warning "Checking dependencies..."
    if ! python3 -m pip install -q -r requirements.txt 2>/dev/null; then
        print_error "Failed to install dependencies"
        exit 1
    fi
    print_success "Core dependencies OK"
    
    # Check for development artifacts
    print_warning "Checking for development artifacts..."
    if [ -f "PRODUCTION_CHECKLIST.md" ] || [ -f "RELEASE_NOTES.md" ]; then
        print_error "Development files still present - run cleanup first"
        exit 1
    fi
    print_success "No development artifacts found"
    
    # Check git status
    print_warning "Checking git status..."
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not a git repository"
        exit 1
    fi
    
    if [ -n "$(git status --porcelain)" ]; then
        print_error "Uncommitted changes detected:"
        git status --porcelain
        exit 1
    fi
    print_success "Git working directory clean"
    
    print_success "All validation checks passed!"
}

cmd_build_bundles() {
    print_header "Building Release Bundles"
    
    # Check required files exist
    if ! check_files_exist "runner.py" "requirements.txt" "LICENSE" "README.md"; then
        print_error "Missing required files for bundle build"
        exit 1
    fi
    
    # Create dist directory
    if ! mkdir -p dist; then
        print_error "Failed to create dist directory"
        exit 1
    fi
    
    if [ ! -d "dist" ]; then
        print_error "dist directory does not exist or is not accessible"
        exit 1
    fi
    
    # Build Python3 bundle
    print_warning "Building Python 3 bundle..."
    mkdir -p dist/python3-runner || { print_error "Failed to create dist/python3-runner"; exit 1; }
    
    cp runner.py dist/python3-runner/ || { print_error "Failed to copy runner.py"; exit 1; }
    cp requirements.txt dist/python3-runner/ || { print_error "Failed to copy requirements.txt"; exit 1; }
    cp LICENSE dist/python3-runner/ || { print_error "Failed to copy LICENSE"; exit 1; }
    cp README.md dist/python3-runner/ || { print_error "Failed to copy README.md"; exit 1; }
    cp config.example.yaml dist/python3-runner/ 2>/dev/null || true
    
    cat > dist/python3-runner/INSTALL.sh << 'INSTALL_SCRIPT' || { print_error "Failed to create INSTALL.sh"; exit 1; }
#!/bin/bash
set -e
echo "Installing Python Script Runner (Python 3)..."
python3 -m pip install -r requirements.txt
chmod +x runner.py
echo "✅ Installation complete!"
echo "Usage: python3 runner.py <script.py> [options]"
INSTALL_SCRIPT
    chmod +x dist/python3-runner/INSTALL.sh || { print_error "Failed to make INSTALL.sh executable"; exit 1; }
    
    cd dist || { print_error "Failed to enter dist directory"; exit 1; }
    
    if ! tar -czf python3-runner.tar.gz python3-runner/ 2>/dev/null; then
        cd .. > /dev/null 2>&1 || true
        print_error "Failed to create python3-runner.tar.gz"
        exit 1
    fi
    
    if ! zip -q -r python3-runner.zip python3-runner/ 2>/dev/null; then
        cd .. > /dev/null 2>&1 || true
        print_error "Failed to create python3-runner.zip"
        exit 1
    fi
    
    cd .. || { print_error "Failed to exit dist directory"; exit 1; }
    
    print_success "Python 3 bundle created"
    ls -lh dist/python3-runner.* || print_warning "Could not list python3 bundles"
    
    # Build PyPy3 bundle
    print_warning "Building PyPy3 bundle..."
    mkdir -p dist/pypy3-runner || { print_error "Failed to create dist/pypy3-runner"; exit 1; }
    
    cp runner.py dist/pypy3-runner/ || { print_error "Failed to copy runner.py to pypy3"; exit 1; }
    cp requirements.txt dist/pypy3-runner/ || { print_error "Failed to copy requirements.txt to pypy3"; exit 1; }
    cp LICENSE dist/pypy3-runner/ || { print_error "Failed to copy LICENSE to pypy3"; exit 1; }
    cp README.md dist/pypy3-runner/ || { print_error "Failed to copy README.md to pypy3"; exit 1; }
    cp config.example.yaml dist/pypy3-runner/ 2>/dev/null || true
    cp requirements-pypy3.txt dist/pypy3-runner/ 2>/dev/null || true
    
    cat > dist/pypy3-runner/INSTALL.sh << 'INSTALL_SCRIPT' || { print_error "Failed to create pypy3 INSTALL.sh"; exit 1; }
#!/bin/bash
set -e
echo "Installing Python Script Runner (PyPy3)..."
if ! command -v pypy3 &> /dev/null; then
    echo "PyPy3 not found. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y pypy3 pypy3-dev
    elif command -v brew &> /dev/null; then
        brew install pypy3
    else
        echo "Please install PyPy3 manually"
        exit 1
    fi
fi
pypy3 -m pip install -r requirements.txt
pypy3 -m pip install -r requirements-pypy3.txt 2>/dev/null || true
chmod +x runner.py
echo "✅ Installation complete!"
echo "Usage: pypy3 runner.py <script.py> [options]"
INSTALL_SCRIPT
    chmod +x dist/pypy3-runner/INSTALL.sh || { print_error "Failed to make pypy3 INSTALL.sh executable"; exit 1; }
    
    cd dist || { print_error "Failed to enter dist directory"; exit 1; }
    
    if ! tar -czf pypy3-runner.tar.gz pypy3-runner/ 2>/dev/null; then
        cd .. > /dev/null 2>&1 || true
        print_error "Failed to create pypy3-runner.tar.gz"
        exit 1
    fi
    
    if ! zip -q -r pypy3-runner.zip pypy3-runner/ 2>/dev/null; then
        cd .. > /dev/null 2>&1 || true
        print_error "Failed to create pypy3-runner.zip"
        exit 1
    fi
    
    cd .. || { print_error "Failed to exit dist directory"; exit 1; }
    
    print_success "PyPy3 bundle created"
    ls -lh dist/pypy3-runner.* || print_warning "Could not list pypy3 bundles"
    
    # Create checksums
    print_warning "Creating checksums..."
    cd dist || { print_error "Failed to enter dist"; exit 1; }
    
    if ! sha256sum python3-runner.* pypy3-runner.* > SHA256SUMS.txt 2>/dev/null; then
        cd .. > /dev/null 2>&1 || true
        print_error "Failed to create checksums"
        exit 1
    fi
    
    cd .. || { print_error "Failed to exit dist"; exit 1; }
    print_success "Checksums created"
}

cmd_build_exe() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "Version required"
        echo "Usage: bash release.sh build-exe VERSION"
        exit 1
    fi
    
    validate_version "$version" || exit 1
    
    print_header "Building Windows EXE Executable v$version"
    
    # Check required commands
    if ! command -v pip &> /dev/null; then
        print_error "pip command not found"
        exit 1
    fi
    
    # Install PyInstaller if not present
    print_warning "Checking PyInstaller installation..."
    if ! python3 -c "import PyInstaller" 2>/dev/null; then
        print_warning "PyInstaller not found, installing..."
        if ! pip install -q pyinstaller; then
            print_error "Failed to install PyInstaller"
            exit 1
        fi
        print_success "PyInstaller installed"
    else
        print_success "PyInstaller already installed"
    fi
    
    # Create build directory
    if ! mkdir -p dist/windows 2>/dev/null; then
        print_error "Failed to create dist/windows directory"
        exit 1
    fi
    
    # Create PyInstaller spec file if it doesn't exist
    if [ ! -f "runner.spec" ]; then
        print_warning "Creating PyInstaller spec file..."
        cat > runner.spec << 'SPEC_FILE'
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

a = Analysis(
    ['runner.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('psutil'),
    hiddenimports=['psutil', 'yaml', 'requests'] + collect_submodules('yaml'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='python-script-runner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
SPEC_FILE
        print_success "Spec file created"
    fi
    
    # Build EXE using PyInstaller
    print_warning "Building Windows executable with PyInstaller..."
    local pyinstaller_output
    if ! pyinstaller_output=$(pyinstaller runner.spec --distpath dist/windows/dist --workpath dist/windows/build 2>&1); then
        print_error "Failed to build Windows executable"
        echo "PyInstaller error: $pyinstaller_output"
        exit 1
    fi
    
    # Show non-warning output
    if echo "$pyinstaller_output" | grep -v "WARNING" > /dev/null 2>&1; then
        echo "$pyinstaller_output" | grep -v "WARNING" || true
    fi
    
    # Check if EXE was created
    if [ ! -f "dist/windows/dist/python-script-runner.exe" ]; then
        print_error "Windows executable not found at expected location"
        exit 1
    fi
    
    print_success "Windows executable built successfully"
    
    # Copy necessary files
    print_warning "Packaging Windows executable..."
    mkdir -p "dist/windows/python-script-runner-$version" || { print_error "Failed to create packaging directory"; exit 1; }
    
    cp "dist/windows/dist/python-script-runner.exe" "dist/windows/python-script-runner-$version/" || { print_error "Failed to copy executable"; exit 1; }
    cp LICENSE "dist/windows/python-script-runner-$version/" || { print_error "Failed to copy LICENSE"; exit 1; }
    cp README.md "dist/windows/python-script-runner-$version/" || { print_error "Failed to copy README"; exit 1; }
    cp config.example.yaml "dist/windows/python-script-runner-$version/" 2>/dev/null || true
    
    # Create Windows ZIP
    cd dist/windows || { print_error "Failed to enter dist/windows"; exit 1; }
    zip -q -r "python-script-runner-$version-windows.zip" "python-script-runner-$version/" || { print_error "Failed to create Windows ZIP"; exit 1; }
    cd - > /dev/null || { print_error "Failed to exit dist/windows"; exit 1; }
    
    print_success "Windows EXE packaged successfully"
    ls -lh "dist/windows/python-script-runner-$version-windows.zip" || print_warning "Could not list Windows package"
    
    echo ""
    echo "📦 Windows Executable Details:"
    echo "   File: dist/windows/python-script-runner-$version-windows.zip"
    echo "   Contains: python-script-runner.exe (standalone, no Python required)"
    echo ""
}

cmd_build_deb() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "Version required"
        echo "Usage: bash release.sh build-deb VERSION"
        exit 1
    fi
    
    validate_version "$version" || exit 1
    
    print_header "Building Linux DEB Package v$version"
    
    # Check required commands
    if ! command -v dpkg-deb &> /dev/null; then
        print_error "dpkg-deb command not found (required for building DEB packages)"
        exit 1
    fi
    
    # Create DEB package structure
    print_warning "Creating DEB package structure..."
    local pkg_dir="dist/linux/python-script-runner-$version"
    local debian_dir="$pkg_dir/DEBIAN"
    
    mkdir -p "$debian_dir" || { print_error "Failed to create DEBIAN directory"; exit 1; }
    mkdir -p "$pkg_dir/usr/bin" || { print_error "Failed to create usr/bin directory"; exit 1; }
    mkdir -p "$pkg_dir/usr/lib/python-script-runner" || { print_error "Failed to create lib directory"; exit 1; }
    mkdir -p "$pkg_dir/usr/share/doc/python-script-runner" || { print_error "Failed to create doc directory"; exit 1; }
    
    # Copy application files
    print_warning "Copying application files..."
    cp runner.py "$pkg_dir/usr/lib/python-script-runner/" || { print_error "Failed to copy runner.py"; exit 1; }
    cp requirements.txt "$pkg_dir/usr/lib/python-script-runner/" || { print_error "Failed to copy requirements.txt"; exit 1; }
    cp LICENSE "$pkg_dir/usr/share/doc/python-script-runner/copyright" || { print_error "Failed to copy LICENSE"; exit 1; }
    cp README.md "$pkg_dir/usr/share/doc/python-script-runner/" || { print_error "Failed to copy README"; exit 1; }
    cp config.example.yaml "$pkg_dir/usr/lib/python-script-runner/" 2>/dev/null || true
    
    # Create wrapper script for /usr/bin
    cat > "$pkg_dir/usr/bin/python-script-runner" << 'WRAPPER_SCRIPT'
#!/bin/bash
# Wrapper script for Python Script Runner
set -e

# Get script directory
SCRIPT_DIR="/usr/lib/python-script-runner"

# Check if requirements are installed
check_requirements() {
    python3 -c "import psutil, yaml, requests" 2>/dev/null || {
        echo "Missing required Python dependencies. Installing..."
        python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" || {
            echo "Failed to install dependencies. Please run: sudo apt-get install python3-psutil python3-yaml python3-requests"
            exit 1
        }
    }
}

check_requirements

# Run the runner
exec python3 "$SCRIPT_DIR/runner.py" "$@"
WRAPPER_SCRIPT
    chmod +x "$pkg_dir/usr/bin/python-script-runner" || { print_error "Failed to make wrapper script executable"; exit 1; }
    
    # Calculate installed size
    local installed_size=$(du -s "$pkg_dir/usr" | awk '{print $1}')
    
    # Create DEBIAN/control file
    print_warning "Creating DEBIAN control file..."
    cat > "$debian_dir/control" << CONTROL_FILE
Package: python-script-runner
Version: $version
Architecture: all
Maintainer: Python Script Runner Contributors <dev@example.com>
Homepage: https://github.com/jomardyan/Python-Script-Runner
Installed-Size: $installed_size
Depends: python3 (>= 3.6), python3-pip, python3-psutil, python3-yaml, python3-requests
Description: Production-grade Python script execution engine
 Python Script Runner provides real-time monitoring, alerting, analytics,
 and enterprise integrations for Python script execution.
 .
 Features:
  - Real-time CPU and memory monitoring
  - Multi-channel alerting (Email, Slack, webhooks)
  - Historical analytics with trend analysis
  - CI/CD integration with performance gates
  - Web dashboard for metrics visualization
  - Enterprise integrations (Datadog, Prometheus, New Relic)
CONTROL_FILE
    
    # Create DEBIAN/postinst script
    print_warning "Creating DEBIAN postinst script..."
    cat > "$debian_dir/postinst" << 'POSTINST_SCRIPT'
#!/bin/bash
set -e

echo "Installing Python dependencies for python-script-runner..."
python3 -m pip install -q psutil pyyaml requests 2>/dev/null || true

echo "python-script-runner installed successfully!"
echo "Run with: python-script-runner <script.py> [options]"
POSTINST_SCRIPT
    chmod +x "$debian_dir/postinst" || { print_error "Failed to make postinst executable"; exit 1; }
    
    # Create DEBIAN/prerm script for cleanup
    cat > "$debian_dir/prerm" << 'PRERM_SCRIPT'
#!/bin/bash
set -e

# Optional: cleanup procedure before removal
exit 0
PRERM_SCRIPT
    chmod +x "$debian_dir/prerm" || { print_error "Failed to make prerm executable"; exit 1; }
    
    # Build DEB package
    print_warning "Building DEB package..."
    local deb_output
    if ! deb_output=$(dpkg-deb --build "$pkg_dir" "dist/linux/python-script-runner_${version}_all.deb" 2>&1); then
        print_error "Failed to build DEB package"
        echo "dpkg-deb error: $deb_output"
        exit 1
    fi
    
    # Verify DEB package
    if [ ! -f "dist/linux/python-script-runner_${version}_all.deb" ]; then
        print_error "DEB package not found at expected location"
        exit 1
    fi
    
    print_success "Linux DEB package built successfully"
    ls -lh "dist/linux/python-script-runner_${version}_all.deb" || print_warning "Could not list DEB package"
    
    # Verify DEB contents
    print_warning "Verifying DEB package contents..."
    dpkg-deb -c "dist/linux/python-script-runner_${version}_all.deb" > /dev/null || { print_error "Failed to verify DEB package"; exit 1; }
    
    echo ""
    echo "📦 Linux DEB Package Details:"
    echo "   File: dist/linux/python-script-runner_${version}_all.deb"
    echo "   Install with: sudo apt install ./python-script-runner_${version}_all.deb"
    echo "   Or add to repository and: sudo apt-get install python-script-runner"
    echo ""
}

cmd_prepare_release() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "Version required"
        echo "Usage: bash release.sh prepare-release VERSION"
        exit 1
    fi
    
    validate_version "$version" || exit 1
    
    print_header "Preparing Release v$version"
    
    # Auto-commit any uncommitted changes before preparation
    auto_commit_changes "Auto-commit: uncommitted changes before release v$version"
    
    cmd_validate || exit 1
    
    # Check if version.sh exists
    if [ ! -f "$VERSION_SCRIPT" ]; then
        print_error "version.sh not found at $VERSION_SCRIPT"
        exit 1
    fi
    
    # Update version in code files using version.sh
    print_warning "Updating version in code files via version.sh..."
    if ! bash "$VERSION_SCRIPT" set "$version" > /dev/null 2>&1; then
        print_error "Failed to update version"
        exit 1
    fi
    
    # Stage all version files
    print_warning "Staging version files..."
    for file in "$VERSION_FILE" "$RUNNER_FILE" "$INIT_FILE"; do
        if [ -f "$file" ]; then
            git add "$file" 2>/dev/null || true
        fi
    done
    
    # Commit version changes if there are changes
    if [ -n "$(git status --porcelain)" ]; then
        print_warning "Committing version changes..."
        if ! git commit -m "chore: prepare release v$version" 2>/dev/null; then
            print_error "Failed to commit version changes"
            exit 1
        fi
        print_success "Version changes committed"
    else
        print_warning "No version changes detected"
    fi
    
    # Create git tag
    print_warning "Creating git tag v$version..."
    if ! git tag -a "v$version" -m "Release version $version" 2>/dev/null; then
        print_error "Failed to create git tag (tag may already exist)"
        exit 1
    fi
    print_success "Tag created: v$version"
    
    echo ""
    echo "📋 Release Preparation Summary:"
    echo "   Version: $version"
    echo "   Tag: v$version"
    echo ""
    print_warning "Next step: bash release.sh publish $version"
    echo ""
    print_success "Release preparation complete!"
}

cmd_publish() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "Version required"
        echo "Usage: bash release.sh publish VERSION"
        exit 1
    fi
    
    validate_version "$version" || exit 1
    
    print_header "Publishing Release v$version"
    
    # Check git availability
    if ! command -v git &> /dev/null; then
        print_error "git command not found"
        exit 1
    fi
    
    # Check if tag exists
    if ! git rev-parse "v$version" >/dev/null 2>&1; then
        print_error "Tag v$version does not exist"
        echo "Create it first with: bash release.sh prepare-release $version"
        exit 1
    fi
    
    # Check if tag is already pushed
    print_warning "Checking if tag is already published..."
    local remote_exists
    if remote_exists=$(git rev-parse "origin/refs/tags/v$version" 2>&1); then
        print_warning "Tag v$version already exists on remote - skipping push"
    else
        print_warning "Pushing tag to GitHub..."
        local push_output
        if ! push_output=$(git push origin "v$version" 2>&1); then
            print_error "Failed to push tag to GitHub"
            echo "Git error: $push_output"
            echo "Make sure you have push permissions and a remote named 'origin'"
            exit 1
        fi
        print_success "Tag pushed successfully"
    fi
    
    print_success "Release pushed to GitHub!"
    echo ""
    echo "📋 GitHub Actions Workflow:"
    echo "   The following steps will run automatically:"
    echo "   ✓ Validate version in tag and source files"
    echo "   ✓ Run tests on Python 3.8-3.12"
    echo "   ✓ Build distributions (wheel + sdist)"
    echo "   ✓ Publish to PyPI"
    echo "   ✓ Publish to GitHub Packages"
    echo "   ✓ Create GitHub Release with assets"
    echo ""
    echo "🔗 Watch progress:"
    echo "   https://github.com/jomardyan/Python-Script-Runner/actions"
    echo ""
    echo "📦 Release URLs (once published):"
    echo "   PyPI: https://pypi.org/project/python-script-runner/$version/"
    echo "   GitHub: https://github.com/jomardyan/Python-Script-Runner/releases/tag/v$version"
    echo ""
    print_success "Release published successfully!"
}

# Main
case "${1:-help}" in
    version)
        cmd_version
        ;;
    bump)
        cmd_bump "$2" "${3:-}"
        ;;
    validate)
        cmd_validate
        ;;
    build-bundles)
        cmd_build_bundles
        ;;
    build-exe)
        cmd_build_exe "$2"
        ;;
    build-deb)
        cmd_build_deb "$2"
        ;;
    prepare-release)
        cmd_prepare_release "$2"
        ;;
    publish)
        cmd_publish "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
