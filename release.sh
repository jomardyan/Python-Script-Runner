#!/bin/bash
# Release management script for Python Script Runner
# Automates versioning, tagging, and release preparation

set -euo pipefail

# Error handling
trap 'handle_error $? $LINENO' ERR

handle_error() {
    local exit_code=$1
    local line_number=$2
    print_error "Script failed at line $line_number with exit code $exit_code"
    exit "$exit_code"
}

VERSION_FILE=".version"
PACKAGE_VERSION="3.0.0"

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

show_help() {
    cat << EOF
Python Script Runner - Release Management

Usage: bash release.sh [command] [options]

Commands:
  version              Show current version
  bump (major|minor|patch) [dry-run]  Bump version automatically
  validate             Validate code and dependencies
  build-bundles        Build release bundles locally
  prepare-release VER  Prepare release (creates git tag)
  publish VER          Create and push release tag
  help                 Show this help message

Examples:
  bash release.sh version                     # Show current version
  bash release.sh bump patch                  # Bump to next patch version
  bash release.sh bump patch dry-run          # Preview bump
  bash release.sh validate                    # Run pre-release checks
  bash release.sh prepare-release 3.0.1       # Tag version 3.0.1
  bash release.sh publish 3.0.1               # Create GitHub release

EOF
}

get_version() {
    if [ -f "$VERSION_FILE" ]; then
        cat "$VERSION_FILE"
    else
        echo "$PACKAGE_VERSION"
    fi
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
    
    if check_files_exist "pyproject.toml" 2>/dev/null; then
        local version
        version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' 2>/dev/null) || version="unknown"
        echo "Current Version: $version"
    else
        echo "Current Version: $PACKAGE_VERSION"
    fi
    
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local git_tag
        git_tag=$(git describe --tags --abbrev=0 2>/dev/null || echo 'None')
        echo "Latest Git Tag: $git_tag"
    fi
}

cmd_bump() {
    local bump_type=$1
    local dry_run=$2
    
    if [ -z "$bump_type" ]; then
        print_error "Bump type required (major|minor|patch)"
        exit 1
    fi
    
    if [ "$bump_type" != "major" ] && [ "$bump_type" != "minor" ] && [ "$bump_type" != "patch" ]; then
        print_error "Invalid bump type: $bump_type"
        exit 1
    fi
    
    print_header "Automatic Version Bump ($bump_type)"
    
    # Check if version.sh exists and is executable
    if [ ! -f "version.sh" ]; then
        print_error "version.sh not found"
        exit 1
    fi
    
    if [ "$dry_run" = "dry-run" ]; then
        if bash version.sh bump "$bump_type" dry-run 2>/dev/null; then
            print_success "Dry-run completed successfully"
        else
            print_error "Dry-run failed"
            exit 1
        fi
    else
        cmd_validate || exit 1
        
        if bash version.sh bump "$bump_type" 2>/dev/null; then
            print_success "Version bump successful"
        else
            print_error "Version bump failed"
            exit 1
        fi
        
        local new_version
        if [ -f "pyproject.toml" ]; then
            new_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/' 2>/dev/null) || new_version="unknown"
        else
            print_error "pyproject.toml not found"
            exit 1
        fi
        
        print_warning "Staging files..."
        if [ -f "pyproject.toml" ]; then
            git add pyproject.toml || { print_error "Failed to stage pyproject.toml"; exit 1; }
        fi
        if [ -f "runner.py" ]; then
            git add runner.py || { print_error "Failed to stage runner.py"; exit 1; }
        fi
        
        print_warning "Committing..."
        if git commit -m "Bump version to $new_version" 2>/dev/null; then
            print_success "Committed version bump to git"
        else
            print_warning "No version changes to commit"
        fi
        
        echo ""
        echo "Next: bash release.sh prepare-release $new_version"
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
    check_files_exist "runner.py" "requirements.txt" "LICENSE" "README.md" || exit 1
    
    if ! mkdir -p dist 2>/dev/null; then
        print_error "Failed to create dist directory"
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
    tar -czf python3-runner.tar.gz python3-runner/ || { print_error "Failed to create tar.gz"; exit 1; }
    zip -q -r python3-runner.zip python3-runner/ || { print_error "Failed to create zip"; exit 1; }
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
    tar -czf pypy3-runner.tar.gz pypy3-runner/ || { print_error "Failed to create pypy3 tar.gz"; exit 1; }
    zip -q -r pypy3-runner.zip pypy3-runner/ || { print_error "Failed to create pypy3 zip"; exit 1; }
    cd .. || { print_error "Failed to exit dist directory"; exit 1; }
    
    print_success "PyPy3 bundle created"
    ls -lh dist/pypy3-runner.* || print_warning "Could not list pypy3 bundles"
    
    # Create checksums
    print_warning "Creating checksums..."
    cd dist || { print_error "Failed to enter dist"; exit 1; }
    sha256sum python3-runner.* pypy3-runner.* > SHA256SUMS.txt || { print_error "Failed to create checksums"; exit 1; }
    cd .. || { print_error "Failed to exit dist"; exit 1; }
    print_success "Checksums created"
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
    
    cmd_validate || exit 1
    
    # Check if version.sh exists
    if [ ! -f "version.sh" ]; then
        print_error "version.sh not found"
        exit 1
    fi
    
    # Update version in code files
    print_warning "Updating version in code files..."
    if ! bash version.sh set "$version" > /dev/null 2>&1; then
        print_error "Failed to update version"
        exit 1
    fi
    
    # Commit version changes
    print_warning "Committing version changes..."
    if git add pyproject.toml runner.py 2>/dev/null; then
        if ! git commit -m "Bump version to $version" 2>/dev/null; then
            print_warning "No version changes to commit"
        fi
    else
        print_error "Failed to stage version files"
        exit 1
    fi
    
    # Create git tag
    print_warning "Creating git tag v$version..."
    if ! git tag -a "v$version" -m "Release version $version" 2>/dev/null; then
        print_error "Failed to create git tag"
        exit 1
    fi
    print_success "Tag created: v$version"
    
    echo ""
    print_warning "Next steps:"
    echo "1. Review the changes: git show v$version"
    echo "2. Push to GitHub: bash release.sh publish $version"
    echo "3. GitHub Actions will automatically build and create the release"
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
    
    print_warning "Pushing tag to GitHub..."
    if ! git push origin "v$version" 2>&1; then
        print_error "Failed to push tag to GitHub"
        echo "Make sure you have push permissions and a remote named 'origin'"
        exit 1
    fi
    
    print_success "Release pushed to GitHub!"
    echo ""
    echo "GitHub Actions workflow will:"
    echo "✓ Run tests on Python 3 and PyPy3"
    echo "✓ Build Python 3 distribution bundle"
    echo "✓ Build PyPy3 distribution bundle"
    echo "✓ Create GitHub Release with all artifacts"
    echo ""
    echo "Watch progress at: https://github.com/jomardyan/Python-Script-Runner/actions"
}

# Main
case "${1:-help}" in
    version)
        cmd_version
        ;;
    bump)
        cmd_bump "$2" "$3"
        ;;
    validate)
        cmd_validate
        ;;
    build-bundles)
        cmd_build_bundles
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
