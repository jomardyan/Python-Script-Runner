#!/bin/bash
# Release management script for Python Script Runner
# Automates versioning, tagging, and release preparation
# Integrates with version.sh for semantic versioning and GitHub Actions CI/CD

set -euo pipefail

# Configuration
DEBUG_MODE="${DEBUG:-false}"
INTERACTIVE_MODE="${INTERACTIVE:-true}"
SKIP_TESTS="${SKIP_TESTS:-false}"
PARALLEL_BUILDS="${PARALLEL_BUILDS:-true}"
LOG_FILE="${LOG_FILE:-/tmp/release-$(date +%Y%m%d-%H%M%S).log}"

# Global error tracking
ERROR_COUNT=0
WARNING_COUNT=0
SUCCESS_COUNT=0

# Initialize log file
echo "Release script started at $(date)" > "$LOG_FILE"
echo "Command: $0 $*" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Error handling with better diagnostics and rollback
trap 'handle_error $? $LINENO $BASH_COMMAND' ERR
trap 'handle_interrupt' INT TERM

STATE_FILE="/tmp/release-state-$$.json"
ROLLBACK_ACTIONS=()

handle_error() {
    local exit_code=$1
    local line_number=$2
    local command="${3:-unknown}"
    ERROR_COUNT=$((ERROR_COUNT + 1))
    
    log_error "Script failed at line $line_number with exit code $exit_code"
    log_error "Failed command: $command"
    print_error "Script failed at line $line_number with exit code $exit_code"
    print_error "Failed command: $command"
    print_error "Check log file: $LOG_FILE"
    
    # Offer rollback if in interactive mode
    if [ "$INTERACTIVE_MODE" = "true" ] && [ ${#ROLLBACK_ACTIONS[@]} -gt 0 ]; then
        echo ""
        print_warning "Rollback available. Do you want to rollback changes? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            perform_rollback
        fi
    fi
    
    print_error "Use 'bash release.sh help' for usage information"
    cleanup_on_exit
    exit "$exit_code"
}

handle_interrupt() {
    echo ""
    print_warning "\nInterrupted by user"
    log_warning "Script interrupted by user"
    
    if [ "$INTERACTIVE_MODE" = "true" ]; then
        print_warning "Do you want to rollback changes? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            perform_rollback
        fi
    fi
    
    cleanup_on_exit
    exit 130
}

perform_rollback() {
    print_header "Rolling Back Changes"
    log_info "Starting rollback"
    
    local rollback_count=0
    # Execute rollback actions in reverse order
    for ((i=${#ROLLBACK_ACTIONS[@]}-1; i>=0; i--)); do
        local action="${ROLLBACK_ACTIONS[$i]}"
        print_warning "Rollback: $action"
        log_info "Executing rollback: $action"
        
        if eval "$action" >> "$LOG_FILE" 2>&1; then
            ((rollback_count++))
        else
            print_error "Rollback action failed: $action"
            log_error "Rollback action failed: $action"
        fi
    done
    
    print_success "Rolled back $rollback_count action(s)"
    log_info "Completed rollback: $rollback_count actions"
}

register_rollback() {
    local action="$1"
    ROLLBACK_ACTIONS+=("$action")
    log_debug "Registered rollback: $action"
}

cleanup_on_exit() {
    # Clean up temporary files
    [ -f "$STATE_FILE" ] && rm -f "$STATE_FILE"
    log_info "Cleanup completed"
}

# Increment counters for progress tracking
increment_success() {
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
}

increment_warning() {
    WARNING_COUNT=$((WARNING_COUNT + 1))
}

increment_error() {
    ERROR_COUNT=$((ERROR_COUNT + 1))
}

# Print summary statistics
print_summary() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Success: $SUCCESS_COUNT${NC}"
    if [ $WARNING_COUNT -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warnings: $WARNING_COUNT${NC}"
    fi
    if [ $ERROR_COUNT -gt 0 ]; then
        echo -e "${RED}❌ Errors: $ERROR_COUNT${NC}"
    fi
    echo -e "${BLUE}════════════════════════════════════════${NC}"
    echo ""
}

# Script directory and integration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERSION_SCRIPT="${SCRIPT_DIR}/version.sh"
GITHUB_WORKFLOWS_DIR="${SCRIPT_DIR}/.github/workflows"

# Configuration
VERSION_FILE="pyproject.toml"
RUNNER_FILE="runner.py"
INIT_FILE="__init__.py"
RUNNERS_INIT="runners/__init__.py"
SETUP_FILE="setup.py"
PACKAGE_VERSION="${RELEASE_VERSION:-}"

# Known version file locations
VERSION_FILES=(
    "pyproject.toml"
    "runner.py"
    "__init__.py"
    "runners/__init__.py"
)

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
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log_debug() {
    [ "$DEBUG_MODE" = "true" ] && echo "[DEBUG $(date +%H:%M:%S)] $*" >> "$LOG_FILE"
}

log_info() {
    echo "[INFO $(date +%H:%M:%S)] $*" >> "$LOG_FILE"
}

log_warning() {
    echo "[WARNING $(date +%H:%M:%S)] $*" >> "$LOG_FILE"
}

log_error() {
    echo "[ERROR $(date +%H:%M:%S)] $*" >> "$LOG_FILE"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
    log_info "=== $1 ==="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    log_info "SUCCESS: $1"
    increment_success
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    log_error "$1"
    increment_error
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    log_warning "$1"
    increment_warning
}

print_info() {
    echo -e "${CYAN}ℹ️  $1${NC}"
    log_info "$1"
}

print_step() {
    echo -e "${MAGENTA}▶ $1${NC}"
    log_info "STEP: $1"
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
  status              Show comprehensive release status
  bump (major|minor|patch) [dry-run]
                      Bump version using version.sh (auto-updates files)
                      ⚠️  Auto-commits any uncommitted changes before bumping
  validate            Run pre-release validation checks
  verify-versions     Verify version consistency across all files
  clean               Remove build artifacts and temporary files
  auto-release [type] 🚀 FULLY AUTOMATIC RELEASE - Does everything!
                      Bumps version, builds, tags, and publishes automatically
                      No prompts, no interaction required (CI/CD friendly)
                      Types: major|minor|patch (default: patch)
                      Example: bash release.sh auto-release patch
  build-bundles       Build Python source bundles (tar.gz, zip)
  build-exe VER       Build Windows EXE executable using PyInstaller
  build-deb VER       Build Linux DEB package
  prepare-release VER Prepare release: update files, create git tag
                      ⚠️  Auto-commits any uncommitted changes before preparing
  publish VER         Push tag to GitHub (triggers GitHub Actions workflow)
  full-release VER    Execute complete release workflow (all steps)
  help                Show this help message

Environment Variables:
  DEBUG=true          Enable debug logging
  INTERACTIVE=false   Disable interactive prompts
  SKIP_TESTS=true     Skip test execution during validation
  PARALLEL_BUILDS=false  Disable parallel bundle building
  LOG_FILE=path       Custom log file location

Workflow:
  # ONE-COMMAND AUTOMATIC RELEASE (Recommended):
  bash release.sh auto-release patch         # Does everything automatically!
  
  # OR Manual step-by-step:
  1. bash release.sh bump patch              # Auto-bump version (auto-commits)
  2. bash release.sh build-exe X.Y.Z         # Build Windows executable (optional)
  3. bash release.sh build-deb X.Y.Z         # Build Linux DEB package (optional)
  4. bash release.sh prepare-release X.Y.Z   # Create and tag release (auto-commits)
  5. bash release.sh publish X.Y.Z           # Push tag to GitHub
  6. GitHub Actions will auto-build and publish to PyPI & GitHub Packages

Options:
  X.Y.Z             Version in semantic versioning format
  dry-run           Preview changes without applying them

Examples:
  # Automatic Release (Easiest!):
  bash release.sh auto-release               # Auto patch release (7.0.1 → 7.0.2)
  bash release.sh auto-release minor         # Auto minor release (7.0.2 → 7.1.0)
  bash release.sh auto-release major         # Auto major release (7.1.0 → 8.0.0)
  
  # Manual Commands:
  bash release.sh version                    # Show current version
  bash release.sh status                     # Show comprehensive status
  bash release.sh bump patch                 # Bump to next patch (auto-commits changes)
  bash release.sh bump minor dry-run         # Preview minor bump
  bash release.sh validate                   # Run validation checks
  bash release.sh clean                      # Clean build artifacts
  bash release.sh build-bundles              # Build source bundles
  bash release.sh build-exe 7.0.1            # Build Windows EXE
  bash release.sh build-deb 7.0.1            # Build Linux DEB
  bash release.sh prepare-release 7.0.1      # Prepare v7.0.1 release
  bash release.sh publish 7.0.1              # Trigger GitHub Actions

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
        version=$(grep '^version = ' "$VERSION_FILE" 2>/dev/null | head -1 | sed 's/version = "\(.*\)"/\1/' || echo "")
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

# Update version in all known locations
update_all_versions() {
    local new_version="$1"
    local updated_count=0
    local failed_count=0
    
    print_step "Updating version to $new_version in all files..."
    log_info "Starting automatic version update to $new_version"
    
    # Update pyproject.toml
    if [ -f "pyproject.toml" ]; then
        if sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml 2>/dev/null; then
            rm -f pyproject.toml.bak
            print_info "  ✓ Updated pyproject.toml"
            ((updated_count++))
        else
            print_warning "  ✗ Failed to update pyproject.toml"
            ((failed_count++))
        fi
    fi
    
    # Update runner.py
    if [ -f "runner.py" ]; then
        if sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" runner.py 2>/dev/null; then
            rm -f runner.py.bak
            print_info "  ✓ Updated runner.py"
            ((updated_count++))
        else
            print_warning "  ✗ Failed to update runner.py"
            ((failed_count++))
        fi
    fi
    
    # Update __init__.py (root)
    if [ -f "__init__.py" ]; then
        if sed -i.bak "s/__version__ = \".*\"/__version__ = \"$new_version\"/" __init__.py 2>/dev/null; then
            rm -f __init__.py.bak
            print_info "  ✓ Updated __init__.py"
            ((updated_count++))
        else
            print_warning "  ✗ Failed to update __init__.py"
            ((failed_count++))
        fi
    fi
    
    # Update runners/__init__.py
    if [ -f "runners/__init__.py" ]; then
        if sed -i.bak "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" runners/__init__.py 2>/dev/null; then
            rm -f runners/__init__.py.bak
            print_info "  ✓ Updated runners/__init__.py"
            ((updated_count++))
        else
            print_warning "  ✗ Failed to update runners/__init__.py"
            ((failed_count++))
        fi
    fi
    
    # Update setup.py fallback version
    if [ -f "setup.py" ]; then
        if sed -i.bak "s/version_match.group(1) if version_match else \".*\"/version_match.group(1) if version_match else \"$new_version\"/" setup.py 2>/dev/null; then
            rm -f setup.py.bak
            print_info "  ✓ Updated setup.py fallback version"
            ((updated_count++))
        else
            print_warning "  ✗ Failed to update setup.py"
            ((failed_count++))
        fi
    fi
    
    # Summary
    if [ $updated_count -gt 0 ]; then
        print_success "Updated version in $updated_count file(s)"
    fi
    
    if [ $failed_count -gt 0 ]; then
        print_warning "Failed to update $failed_count file(s)"
        return 1
    fi
    
    log_info "Version update completed: $updated_count files updated, $failed_count failed"
    return 0
}

# Verify versions are consistent across all files
verify_versions() {
    print_step "Verifying version consistency..."
    log_info "Starting version consistency check"
    
    local versions=()
    local files=()
    
    # Check pyproject.toml
    if [ -f "pyproject.toml" ]; then
        local v=$(grep '^version = ' pyproject.toml 2>/dev/null | head -1 | sed 's/version = "\(.*\)"/\1/')
        if [ -n "$v" ]; then
            versions+=("$v")
            files+=("pyproject.toml")
            print_info "  pyproject.toml: $v"
        fi
    fi
    
    # Check runner.py
    if [ -f "runner.py" ]; then
        local v=$(grep '^__version__ = ' runner.py 2>/dev/null | sed 's/__version__ = "\(.*\)"/\1/')
        if [ -n "$v" ]; then
            versions+=("$v")
            files+=("runner.py")
            print_info "  runner.py: $v"
        fi
    fi
    
    # Check __init__.py
    if [ -f "__init__.py" ]; then
        local v=$(grep '__version__ = ' __init__.py 2>/dev/null | grep -v 'from\|import' | sed 's/.*__version__ = "\(.*\)".*/\1/' | head -1)
        if [ -n "$v" ]; then
            versions+=("$v")
            files+=("__init__.py")
            print_info "  __init__.py: $v"
        fi
    fi
    
    # Check runners/__init__.py
    if [ -f "runners/__init__.py" ]; then
        local v=$(grep '^__version__ = ' runners/__init__.py 2>/dev/null | sed 's/__version__ = "\(.*\)"/\1/')
        if [ -n "$v" ]; then
            versions+=("$v")
            files+=("runners/__init__.py")
            print_info "  runners/__init__.py: $v"
        fi
    fi
    
    # Check if all versions are the same
    local unique_versions=($(printf '%s\n' "${versions[@]}" | sort -u))
    
    if [ ${#unique_versions[@]} -eq 1 ]; then
        print_success "All versions are consistent: ${unique_versions[0]}"
        log_info "Version consistency check passed: ${unique_versions[0]}"
        return 0
    else
        print_error "Version mismatch detected!"
        for i in "${!versions[@]}"; do
            print_warning "  ${files[$i]}: ${versions[$i]}"
        done
        log_error "Version consistency check failed: found ${#unique_versions[@]} different versions"
        return 1
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
    log_info "Starting version bump: $bump_type (dry_run=$dry_run)"
    
    # Get current version for display
    local current_version
    current_version=$(get_version || echo "unknown")
    print_info "Current version: $current_version"
    
    # Safety check for major version bump
    if [ "$bump_type" = "major" ] && [ "$INTERACTIVE_MODE" = "true" ] && [ "$dry_run" != "dry-run" ]; then
        print_warning "Major version bump detected!"
        print_warning "This indicates breaking changes. Are you sure? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Version bump cancelled"
            exit 0
        fi
    fi
    
    # Auto-commit any uncommitted changes before bumping (only for actual bump, not dry-run)
    if [ "$dry_run" != "dry-run" ]; then
        auto_commit_changes "Auto-commit: uncommitted changes before version bump ($bump_type)"
        register_rollback "git reset --hard HEAD~1"
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
    log_info "Starting validation"
    
    local validation_errors=0
    
    # Check required commands
    print_step "Checking required commands..."
    local required_commands=("python3" "git" "pip")
    for cmd in "${required_commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            print_info "  ✓ $cmd found"
        else
            print_error "  ✗ $cmd not found"
            ((validation_errors++))
        fi
    done
    
    # Check required files
    print_step "Checking for required files..."
    local required_files=("runner.py" "requirements.txt" "LICENSE" "README.md")
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_info "  ✓ $file exists"
        else
            print_error "  ✗ $file missing"
            ((validation_errors++))
        fi
    done
    
    if [ $validation_errors -gt 0 ]; then
        print_error "Validation failed: $validation_errors error(s) found"
        return 1
    fi
    
    # Check Python version
    print_step "Checking Python version..."
    local py_version=$(python3 --version 2>&1 | awk '{print $2}')
    print_info "  Python version: $py_version"
    
    # Check Python compilation
    print_step "Checking code quality..."
    local compile_output
    if compile_output=$(python3 -m py_compile runner.py test_script.py 2>&1); then
        print_success "Compilation successful"
    else
        print_error "Python compilation failed:"
        echo "$compile_output"
        ((validation_errors++))
    fi
    
    # Check dependencies with better error handling
    print_step "Checking Python dependencies..."
    local dep_check_output
    if dep_check_output=$(python3 -c "import psutil, yaml, requests" 2>&1); then
        print_success "Core dependencies available"
    else
        print_warning "Some dependencies missing - attempting installation..."
        log_info "Dependency check output: $dep_check_output"
        
        # Try to install missing dependencies
        local install_output
        if install_output=$(python3 -m pip install --user -q psutil pyyaml requests 2>&1); then
            print_success "Dependencies installed successfully"
        else
            print_warning "Could not auto-install dependencies"
            print_info "You may need to run: pip install -r requirements.txt"
            log_warning "Dependency installation output: $install_output"
            # Don't fail validation for dependency issues in user mode
        fi
    fi
    
    # Check for development artifacts
    print_step "Checking for development artifacts..."
    local dev_files=("PRODUCTION_CHECKLIST.md" "RELEASE_NOTES.md" ".DS_Store")
    local dev_found=0
    for file in "${dev_files[@]}"; do
        if [ -f "$file" ]; then
            print_warning "  Development file found: $file"
            ((dev_found++))
        fi
    done
    
    if [ $dev_found -gt 0 ]; then
        print_warning "Found $dev_found development file(s) - consider cleanup"
    else
        print_success "No development artifacts found"
    fi
    
    # Check git status
    print_step "Checking git repository..."
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not a git repository"
        ((validation_errors++))
    else
        local branch=$(git branch --show-current)
        print_info "  Current branch: $branch"
        
        local commit_count=$(git rev-list --count HEAD 2>/dev/null || echo "0")
        print_info "  Total commits: $commit_count"
        
        if [ -n "$(git status --porcelain)" ]; then
            if [ "$INTERACTIVE_MODE" = "true" ]; then
                print_warning "Uncommitted changes detected:"
                git status --short
                echo ""
                print_warning "Continue anyway? (y/n)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    print_error "Validation cancelled by user"
                    exit 1
                fi
            else
                print_warning "Uncommitted changes detected (will be auto-committed)"
            fi
        else
            print_success "Git working directory clean"
        fi
    fi
    
    # Run tests if available and not skipped
    if [ "$SKIP_TESTS" != "true" ] && [ -f "pytest.ini" ]; then
        print_step "Running tests..."
        if command -v pytest &> /dev/null; then
            local test_output
            if test_output=$(pytest tests/ -q --tb=short 2>&1); then
                print_success "Tests passed"
            else
                print_warning "Some tests failed:"
                echo "$test_output" | head -20
                if [ "$INTERACTIVE_MODE" = "true" ]; then
                    print_warning "Continue despite test failures? (y/n)"
                    read -r response
                    if [[ ! "$response" =~ ^[Yy]$ ]]; then
                        exit 1
                    fi
                fi
            fi
        else
            print_info "pytest not available, skipping tests"
        fi
    fi
    
    if [ $validation_errors -gt 0 ]; then
        print_error "Validation failed with $validation_errors error(s)"
        return 1
    fi
    
    print_success "All validation checks passed!"
    return 0
}

build_bundle_parallel() {
    local bundle_type="$1"
    local bundle_name="$2"
    
    log_info "Building $bundle_name bundle in parallel"
    
    case "$bundle_type" in
        python3)
            build_python3_bundle
            ;;
        pypy3)
            build_pypy3_bundle
            ;;
        *)
            log_error "Unknown bundle type: $bundle_type"
            return 1
            ;;
    esac
}

build_python3_bundle() {
    log_info "Building Python3 bundle"
    
    mkdir -p dist/python3-runner || return 1
    cp runner.py requirements.txt LICENSE README.md dist/python3-runner/ || return 1
    cp config.example.yaml dist/python3-runner/ 2>/dev/null || true
    
    cat > dist/python3-runner/INSTALL.sh << 'INSTALL_SCRIPT' || return 1
#!/bin/bash
set -e
echo "Installing Python Script Runner (Python 3)..."
python3 -m pip install -r requirements.txt
chmod +x runner.py
echo "✅ Installation complete!"
echo "Usage: python3 runner.py <script.py> [options]"
INSTALL_SCRIPT
    
    chmod +x dist/python3-runner/INSTALL.sh || return 1
    
    cd dist || return 1
    tar -czf python3-runner.tar.gz python3-runner/ 2>/dev/null || { cd ..; return 1; }
    zip -q -r python3-runner.zip python3-runner/ 2>/dev/null || { cd ..; return 1; }
    cd .. || return 1
    
    log_info "Python3 bundle completed"
    return 0
}

build_pypy3_bundle() {
    log_info "Building PyPy3 bundle"
    
    mkdir -p dist/pypy3-runner || return 1
    cp runner.py requirements.txt LICENSE README.md dist/pypy3-runner/ || return 1
    cp config.example.yaml requirements-pypy3.txt dist/pypy3-runner/ 2>/dev/null || true
    
    cat > dist/pypy3-runner/INSTALL.sh << 'INSTALL_SCRIPT' || return 1
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
    
    chmod +x dist/pypy3-runner/INSTALL.sh || return 1
    
    cd dist || return 1
    tar -czf pypy3-runner.tar.gz pypy3-runner/ 2>/dev/null || { cd ..; return 1; }
    zip -q -r pypy3-runner.zip pypy3-runner/ 2>/dev/null || { cd ..; return 1; }
    cd .. || return 1
    
    log_info "PyPy3 bundle completed"
    return 0
}

cmd_build_bundles() {
    print_header "Building Release Bundles"
    log_info "Starting bundle build"
    
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
    
    # Build bundles in parallel if enabled
    if [ "$PARALLEL_BUILDS" = "true" ]; then
        print_step "Building bundles in parallel..."
        
        build_python3_bundle &
        local py3_pid=$!
        
        build_pypy3_bundle &
        local pypy3_pid=$!
        
        # Wait for both builds
        local py3_status=0
        local pypy3_status=0
        
        wait $py3_pid || py3_status=$?
        wait $pypy3_pid || pypy3_status=$?
        
        if [ $py3_status -eq 0 ]; then
            print_success "Python 3 bundle created"
        else
            print_error "Python 3 bundle failed"
            exit 1
        fi
        
        if [ $pypy3_status -eq 0 ]; then
            print_success "PyPy3 bundle created"
        else
            print_error "PyPy3 bundle failed"
            exit 1
        fi
    else
        # Sequential build
        print_step "Building Python 3 bundle..."
        if build_python3_bundle; then
            print_success "Python 3 bundle created"
        else
            print_error "Python 3 bundle failed"
            exit 1
        fi
        
        print_step "Building PyPy3 bundle..."
        if build_pypy3_bundle; then
            print_success "PyPy3 bundle created"
        else
            print_error "PyPy3 bundle failed"
            exit 1
        fi
    fi
    
    # Remove old sequential code - now using functions above
    # Build Python3 bundle
    # print_warning "Building Python 3 bundle..."
    # mkdir -p dist/python3-runner || { print_error "Failed to create dist/python3-runner"; exit 1; }
    
    # List created bundles
    print_step "Listing created bundles..."
    ls -lh dist/python3-runner.* 2>/dev/null || print_warning "Could not list python3 bundles"
    ls -lh dist/pypy3-runner.* 2>/dev/null || print_warning "Could not list pypy3 bundles"
    
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
    
    # Update version in code files automatically
    print_warning "Updating version in code files..."
    if ! update_all_versions "$version"; then
        print_warning "Some version updates failed, attempting to continue..."
    fi
    
    # Verify version consistency
    if verify_versions > /dev/null 2>&1; then
        print_success "Version consistency verified"
    else
        print_warning "Version consistency check had warnings"
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

# New utility commands
cmd_status() {
    print_header "Release Status"
    
    cmd_version
    echo ""
    
    print_step "Git Information"
    if git rev-parse --git-dir > /dev/null 2>&1; then
        local branch=$(git branch --show-current)
        local commit=$(git rev-parse --short HEAD)
        local remote_url=$(git config --get remote.origin.url 2>/dev/null || echo "none")
        
        print_info "Branch: $branch"
        print_info "Commit: $commit"
        print_info "Remote: $remote_url"
        
        if [ -n "$(git status --porcelain)" ]; then
            print_warning "Uncommitted changes: $(git status --porcelain | wc -l) file(s)"
        else
            print_success "Working directory clean"
        fi
    else
        print_warning "Not a git repository"
    fi
    
    echo ""
    print_step "Build Artifacts"
    if [ -d "dist" ]; then
        local artifact_count=$(find dist -type f | wc -l)
        print_info "Artifacts in dist/: $artifact_count file(s)"
        du -sh dist/ 2>/dev/null || true
    else
        print_info "No dist/ directory found"
    fi
}

cmd_clean() {
    print_header "Cleaning Build Artifacts"
    log_info "Starting cleanup"
    
    local cleaned=0
    
    # Clean dist directory
    if [ -d "dist" ]; then
        print_step "Removing dist/ directory..."
        if rm -rf dist/; then
            print_success "Removed dist/"
            ((cleaned++))
        else
            print_error "Failed to remove dist/"
        fi
    fi
    
    # Clean build artifacts
    local patterns=("*.pyc" "__pycache__" "*.egg-info" ".pytest_cache" ".coverage" "*.spec")
    for pattern in "${patterns[@]}"; do
        local files=$(find . -name "$pattern" 2>/dev/null)
        if [ -n "$files" ]; then
            print_step "Removing $pattern..."
            find . -name "$pattern" -exec rm -rf {} + 2>/dev/null || true
            ((cleaned++))
        fi
    done
    
    # Clean log files
    if ls /tmp/release-*.log 1> /dev/null 2>&1; then
        print_step "Removing old log files..."
        rm -f /tmp/release-*.log
        ((cleaned++))
    fi
    
    print_success "Cleaned $cleaned item(s)"
}

cmd_auto_release() {
    local bump_type="${1:-patch}"
    
    print_header "Fully Automatic Release ($bump_type)"
    log_info "Starting fully automatic release workflow with bump type: $bump_type"
    
    # Validate bump type
    if [ "$bump_type" != "major" ] && [ "$bump_type" != "minor" ] && [ "$bump_type" != "patch" ]; then
        print_error "Invalid bump type: $bump_type"
        echo "Usage: bash release.sh auto-release [major|minor|patch]"
        echo "Default: patch"
        exit 1
    fi
    
    # Force non-interactive mode for automation
    local original_interactive="$INTERACTIVE_MODE"
    export INTERACTIVE_MODE="false"
    
    echo ""
    print_info "🚀 Starting automated release workflow..."
    print_info "   Bump type: $bump_type"
    print_info "   Mode: Fully automatic (no prompts)"
    echo ""
    
    # Step 1: Clean any previous builds
    print_step "Step 1/6: Cleaning previous builds"
    cmd_clean || { print_warning "Clean failed (non-fatal)"; }
    
    # Step 2: Auto-commit any uncommitted changes
    print_step "Step 2/6: Auto-committing uncommitted changes"
    if [ -n "$(git status --porcelain)" ]; then
        auto_commit_changes "Auto-commit: preparing for automated release ($bump_type)"
    else
        print_info "No uncommitted changes"
    fi
    
    # Step 3: Bump version
    print_step "Step 3/6: Bumping version ($bump_type)"
    
    # Get current version before bump
    local old_version=$(get_version || echo "unknown")
    print_info "Current version: $old_version"
    
    # Calculate new version
    local major minor patch
    IFS='.' read -r major minor patch <<< "$old_version"
    
    case "$bump_type" in
        major)
            major=$((major + 1))
            minor=0
            patch=0
            ;;
        minor)
            minor=$((minor + 1))
            patch=0
            ;;
        patch)
            patch=$((patch + 1))
            ;;
    esac
    
    local new_version="$major.$minor.$patch"
    print_info "New version will be: $new_version"
    
    # Update all version files automatically
    if ! update_all_versions "$new_version"; then
        print_error "Version update failed"
        export INTERACTIVE_MODE="$original_interactive"
        exit 1
    fi
    
    # Verify consistency
    if ! verify_versions > /dev/null 2>&1; then
        print_warning "Version consistency check had warnings (non-fatal)"
    fi
    
    print_success "Version bumped: $old_version → $new_version"
    
    # Commit version bump
    for file in "$VERSION_FILE" "$RUNNER_FILE" "$INIT_FILE"; do
        if [ -f "$file" ]; then
            git add "$file" 2>/dev/null || true
        fi
    done
    
    if [ -n "$(git status --porcelain)" ]; then
        git commit -m "chore: bump version to $new_version" > /dev/null 2>&1 || true
        print_success "Version bump committed"
    fi
    
    # Step 4: Build bundles (optional, parallel)
    print_step "Step 4/6: Building release bundles"
    if cmd_build_bundles > /dev/null 2>&1; then
        print_success "Bundles built successfully"
    else
        print_warning "Bundle build failed (non-fatal, continuing...)"
    fi
    
    # Step 5: Prepare release (create tag)
    print_step "Step 5/6: Preparing release v$new_version"
    
    # Update version in code files
    if bash "$VERSION_SCRIPT" set "$new_version" > /dev/null 2>&1; then
        print_info "Version files updated"
    else
        print_warning "Version update had issues (may already be correct)"
    fi
    
    # Stage any changes
    for file in "$VERSION_FILE" "$RUNNER_FILE" "$INIT_FILE"; do
        if [ -f "$file" ]; then
            git add "$file" 2>/dev/null || true
        fi
    done
    
    # Commit if there are changes
    if [ -n "$(git status --porcelain)" ]; then
        git commit -m "chore: prepare release v$new_version" > /dev/null 2>&1 || true
    fi
    
    # Create git tag
    if git tag -a "v$new_version" -m "Release version $new_version" 2>/dev/null; then
        print_success "Tag created: v$new_version"
    else
        # Tag might already exist, delete and recreate
        git tag -d "v$new_version" 2>/dev/null || true
        if git tag -a "v$new_version" -m "Release version $new_version" 2>/dev/null; then
            print_success "Tag recreated: v$new_version"
        else
            print_error "Failed to create git tag"
            export INTERACTIVE_MODE="$original_interactive"
            exit 1
        fi
    fi
    
    # Step 6: Publish to GitHub
    print_step "Step 6/6: Publishing to GitHub"
    
    # Push commits
    if git push origin main > /dev/null 2>&1; then
        print_success "Commits pushed to main"
    else
        print_warning "Push to main failed (may already be up to date)"
    fi
    
    # Push tag
    if git push origin "v$new_version" > /dev/null 2>&1; then
        print_success "Tag pushed to GitHub"
    else
        # Try to delete remote tag and push again
        git push origin :refs/tags/"v$new_version" > /dev/null 2>&1 || true
        if git push origin "v$new_version" > /dev/null 2>&1; then
            print_success "Tag pushed to GitHub (after cleanup)"
        else
            print_error "Failed to push tag to GitHub"
            export INTERACTIVE_MODE="$original_interactive"
            exit 1
        fi
    fi
    
    # Restore interactive mode
    export INTERACTIVE_MODE="$original_interactive"
    
    # Success summary
    echo ""
    print_success "🎉 Automated Release Complete!"
    echo ""
    echo "📋 Release Summary:"
    echo "   Old Version: $old_version"
    echo "   New Version: $new_version"
    echo "   Git Tag: v$new_version"
    echo "   Branch: main"
    echo ""
    echo "📦 GitHub Actions will now:"
    echo "   ✓ Run tests on Python 3.8-3.12"
    echo "   ✓ Build distributions (wheel + sdist)"
    echo "   ✓ Publish to PyPI"
    echo "   ✓ Publish to GitHub Packages"
    echo "   ✓ Create GitHub Release with assets"
    echo ""
    echo "🔗 Monitor progress:"
    echo "   https://github.com/jomardyan/Python-Script-Runner/actions"
    echo ""
    echo "📦 Release URLs (once published):"
    echo "   PyPI: https://pypi.org/project/python-script-runner/$new_version/"
    echo "   GitHub: https://github.com/jomardyan/Python-Script-Runner/releases/tag/v$new_version"
    echo ""
}

cmd_full_release() {
    local version=$1
    
    if [ -z "$version" ]; then
        print_error "Version required"
        echo "Usage: bash release.sh full-release VERSION"
        exit 1
    fi
    
    validate_version "$version" || exit 1
    
    print_header "Full Release Workflow v$version"
    log_info "Starting full release workflow for version $version"
    
    # Confirm in interactive mode
    if [ "$INTERACTIVE_MODE" = "true" ]; then
        print_warning "This will execute the complete release workflow:"
        echo "  1. Validate codebase"
        echo "  2. Build all bundles"
        echo "  3. Build platform packages (EXE, DEB)"
        echo "  4. Prepare release and create git tag"
        echo "  5. Publish to GitHub"
        echo ""
        print_warning "Continue with full release of v$version? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Release cancelled"
            exit 0
        fi
    fi
    
    # Execute full workflow
    print_step "Step 1/5: Validation"
    cmd_validate || { print_error "Validation failed"; exit 1; }
    
    print_step "Step 2/5: Building bundles"
    cmd_build_bundles || { print_error "Bundle build failed"; exit 1; }
    
    print_step "Step 3/5: Building platform packages"
    if command -v pyinstaller &> /dev/null; then
        cmd_build_exe "$version" || print_warning "EXE build failed (non-fatal)"
    else
        print_warning "Skipping EXE build (pyinstaller not available)"
    fi
    
    if command -v dpkg-deb &> /dev/null; then
        cmd_build_deb "$version" || print_warning "DEB build failed (non-fatal)"
    else
        print_warning "Skipping DEB build (dpkg-deb not available)"
    fi
    
    print_step "Step 4/5: Preparing release"
    cmd_prepare_release "$version" || { print_error "Release preparation failed"; exit 1; }
    
    print_step "Step 5/5: Publishing to GitHub"
    if [ "$INTERACTIVE_MODE" = "true" ]; then
        print_warning "Ready to publish to GitHub. Continue? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Publish step skipped"
            print_info "You can publish later with: bash release.sh publish $version"
            exit 0
        fi
    fi
    
    cmd_publish "$version" || { print_error "Publish failed"; exit 1; }
    
    print_success "Full release completed successfully!"
    print_summary
}

# Main
case "${1:-help}" in
    version)
        cmd_version
        ;;
    status)
        cmd_status
        ;;
    bump)
        cmd_bump "$2" "${3:-}"
        ;;
    validate)
        cmd_validate
        ;;
    verify-versions|verify)
        verify_versions
        ;;
    clean)
        cmd_clean
        ;;
    auto-release|auto)
        cmd_auto_release "${2:-patch}"
        ;;
    build-bundles)
        cmd_build_bundles
        ;;
    build-exe)
        cmd_build_exe "${2:-}"
        ;;
    build-deb)
        cmd_build_deb "${2:-}"
        ;;
    prepare-release)
        cmd_prepare_release "${2:-}"
        ;;
    publish)
        cmd_publish "${2:-}"
        ;;
    full-release)
        cmd_full_release "${2:-}"
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

# Final cleanup and summary
print_summary
log_info "Script completed successfully"
