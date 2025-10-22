#!/bin/bash

################################################################################
# PyPI Package Publishing Script
# 
# This script automates the process of building and publishing your package
# to PyPI. It includes testing on TestPyPI before production release.
#
# Usage: ./publish_to_pypi.sh [--test-only] [--no-check] [--help]
#
# Author: Python Script Runner Team
# License: MIT
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
BUILD_DIR="$SCRIPT_DIR/build"
EGG_INFO_DIR="$SCRIPT_DIR"/*.egg-info

# Flags
TEST_ONLY=false
SKIP_CHECK=false

################################################################################
# Utility Functions
################################################################################

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║ $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

usage() {
    cat << EOF
${BLUE}PyPI Publishing Script${NC}

${GREEN}Usage:${NC}
    $0 [OPTIONS]

${GREEN}Options:${NC}
    -h, --help          Show this help message
    -t, --test-only     Only test on TestPyPI, don't publish to production
    -nc, --no-check     Skip verification checks
    -d, --dry-run       Perform a dry-run (show what would be uploaded)

${GREEN}Examples:${NC}
    # Full release: test + production
    $0

    # Test only
    $0 --test-only

    # Dry run to see what would be uploaded
    $0 --dry-run

${GREEN}Requirements:${NC}
    - Python 3.6+
    - build, twine, wheel packages
    - PyPI and TestPyPI accounts with tokens

${GREEN}Setup First:${NC}
    1. pip install build twine wheel
    2. Create PyPI account: https://pypi.org/account/register/
    3. Create API token: https://pypi.org/manage/account/#api-tokens
    4. Configure ~/.pypirc with your token

EOF
}

################################################################################
# Argument Parsing
################################################################################

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -t|--test-only)
                TEST_ONLY=true
                shift
                ;;
            -nc|--no-check)
                SKIP_CHECK=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

################################################################################
# Validation Functions
################################################################################

check_prerequisites() {
    print_info "Checking prerequisites..."
    
    local missing_tools=()
    
    # Check Python
    if ! command -v python >/dev/null 2>&1; then
        missing_tools+=("python")
    fi
    
    # Check pip
    if ! python -m pip --version >/dev/null 2>&1; then
        missing_tools+=("pip")
    fi
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        exit 1
    fi
    
    # Check build tools
    local packages=("build" "twine" "wheel")
    local missing_packages=()
    
    for package in "${packages[@]}"; do
        if ! python -c "import $(echo $package | tr '-' '_')" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "Missing packages: ${missing_packages[*]}"
        print_info "Installing missing packages..."
        pip install "${missing_packages[@]}"
    fi
    
    print_success "Prerequisites check passed"
}

verify_project_structure() {
    print_info "Verifying project structure..."
    
    if [ ! -f "$SCRIPT_DIR/pyproject.toml" ]; then
        print_error "pyproject.toml not found"
        exit 1
    fi
    
    if [ ! -f "$SCRIPT_DIR/README.md" ]; then
        print_error "README.md not found"
        exit 1
    fi
    
    if [ ! -f "$SCRIPT_DIR/LICENSE" ]; then
        print_error "LICENSE file not found"
        exit 1
    fi
    
    print_success "Project structure verified"
}

check_git_status() {
    if [ "$SKIP_CHECK" = true ]; then
        return 0
    fi
    
    print_info "Checking git status..."
    
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_warning "Not a git repository"
        return 0
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        print_warning "Uncommitted changes detected"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Aborted"
            exit 1
        fi
    fi
    
    print_success "Git status OK"
}

################################################################################
# Build Functions
################################################################################

clean_build() {
    print_info "Cleaning previous builds..."
    
    rm -rf "$BUILD_DIR" "$DIST_DIR" $EGG_INFO_DIR 2>/dev/null || true
    
    print_success "Build directory cleaned"
}

build_package() {
    print_info "Building package..."
    
    python -m build
    
    if [ ! -d "$DIST_DIR" ] || [ -z "$(ls -A $DIST_DIR)" ]; then
        print_error "Build failed - no distributions created"
        exit 1
    fi
    
    print_success "Package built successfully"
    
    # Show build artifacts
    echo ""
    print_info "Build artifacts:"
    ls -lh "$DIST_DIR"
    echo ""
}

check_distribution() {
    print_info "Checking distribution..."
    
    twine check "$DIST_DIR"/*
    
    print_success "Distribution check passed"
}

################################################################################
# Upload Functions
################################################################################

upload_to_testpypi() {
    print_header "Testing on TestPyPI"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry-run mode: showing what would be uploaded to TestPyPI"
        twine upload --repository testpypi --dry-run "$DIST_DIR"/*
    else
        print_info "Uploading to TestPyPI..."
        twine upload --repository testpypi "$DIST_DIR"/*
    fi
    
    print_success "TestPyPI upload complete"
    
    # Extract version
    local version=$(python -c "import sys; sys.path.insert(0, '.'); import runner; print(runner.__version__)" 2>/dev/null || echo "X.Y.Z")
    
    echo ""
    print_info "Test your installation with:"
    echo "  pip install --index-url https://test.pypi.org/simple/ --force-reinstall python-script-runner"
    echo ""
    print_info "Or verify on PyPI test repository:"
    echo "  https://test.pypi.org/project/python-script-runner/"
    echo ""
}

upload_to_pypi() {
    print_header "Publishing to PyPI"
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry-run mode: showing what would be uploaded to PyPI"
        twine upload --dry-run "$DIST_DIR"/*
    else
        print_warning "About to publish to production PyPI!"
        print_info "Once published, this version cannot be deleted or modified."
        read -p "Continue with production release? (y/n) " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_error "Publication cancelled"
            exit 1
        fi
        
        print_info "Uploading to PyPI..."
        twine upload "$DIST_DIR"/*
    fi
    
    print_success "PyPI upload complete"
    
    # Extract version
    local version=$(python -c "import sys; sys.path.insert(0, '.'); import runner; print(runner.__version__)" 2>/dev/null || echo "X.Y.Z")
    
    echo ""
    print_success "🎉 Package published to PyPI!"
    echo ""
    print_info "Install your package with:"
    echo "  pip install python-script-runner"
    echo ""
    print_info "View on PyPI:"
    echo "  https://pypi.org/project/python-script-runner/"
    echo ""
}

test_installation() {
    print_header "Testing Installation"
    
    if [ "$DRY_RUN" = true ]; then
        print_warning "Skipping installation test in dry-run mode"
        return 0
    fi
    
    print_info "Installing from test repository..."
    
    # Use timeout to prevent hanging
    timeout 120 pip install --index-url https://test.pypi.org/simple/ --force-reinstall python-script-runner 2>&1 | tail -20 || {
        print_warning "Installation test may have timed out or failed"
        print_info "You can test manually after publishing"
        return 0
    }
    
    print_info "Verifying import..."
    if python -c "import runner; print(f'✓ runner version: {runner.__version__}')" 2>/dev/null; then
        print_success "Installation test passed"
    else
        print_warning "Could not import runner - may need manual verification"
    fi
}

################################################################################
# Display Functions
################################################################################

display_summary() {
    local version=$(python -c "import sys; sys.path.insert(0, '.'); import runner; print(runner.__version__)" 2>/dev/null || grep "^version = " "$SCRIPT_DIR/pyproject.toml" | sed 's/.*"\(.*\)".*/\1/')
    
    print_header "Release Summary"
    
    echo "Package Name:        python-script-runner"
    echo "Version:             $version"
    echo "Build Location:      $DIST_DIR"
    echo "Python Version:      $(python --version)"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        echo "Mode:                🧪 DRY-RUN (no actual uploads)"
    elif [ "$TEST_ONLY" = true ]; then
        echo "Mode:                🧪 TEST-ONLY (TestPyPI only)"
    else
        echo "Mode:                🚀 FULL RELEASE (TestPyPI → PyPI)"
    fi
    
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    parse_arguments "$@"
    
    print_header "PyPI Publishing Script"
    
    # Run checks
    check_prerequisites
    verify_project_structure
    check_git_status
    
    # Build
    clean_build
    build_package
    check_distribution
    
    # Display summary
    display_summary
    
    # Upload
    upload_to_testpypi
    
    if [ "$TEST_ONLY" != true ] && [ "$DRY_RUN" != true ]; then
        echo ""
        read -p "Proceed with production release? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            upload_to_pypi
        else
            print_warning "Production release cancelled"
        fi
    fi
    
    echo ""
    print_success "Publishing workflow complete!"
}

# Run main function
main "$@"
exit $?
