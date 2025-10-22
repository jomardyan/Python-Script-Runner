#!/bin/bash

set -euo pipefail

VERSION_FILE="pyproject.toml"
RUNNER_FILE="runner.py"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() { echo -e "${BLUE}=== $1 ===${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

check_files_exist() {
    if [ ! -f "$VERSION_FILE" ]; then
        print_error "$VERSION_FILE not found"
        exit 1
    fi
    if [ ! -f "$RUNNER_FILE" ]; then
        print_error "$RUNNER_FILE not found"
        exit 1
    fi
}

get_version_raw() {
    grep '^version = ' "$VERSION_FILE" | sed 's/version = "\(.*\)"/\1/'
}

parse_version() {
    if [[ ! $1 =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
        print_error "Invalid version format: $1"
        return 1
    fi
    echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]} ${BASH_REMATCH[3]}"
}

bump_version() {
    local version=$1 bump_type=$2
    local parts
    parts=$(parse_version "$version") || return 1
    local -a parts_arr=($parts)
    local major=${parts_arr[0]} minor=${parts_arr[1]} patch=${parts_arr[2]}
    
    case "$bump_type" in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
        *) print_error "Unknown bump type: $bump_type"; return 1 ;;
    esac
    echo "${major}.${minor}.${patch}"
}

update_pyproject() {
    local new_version=$1
    if ! sed -i "s/^version = \".*\"/version = \"$new_version\"/" "$VERSION_FILE"; then
        print_error "Failed to update $VERSION_FILE"
        return 1
    fi
    print_success "Updated $VERSION_FILE to $new_version"
}

update_runner() {
    local new_version=$1
    if ! sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" "$RUNNER_FILE"; then
        print_error "Failed to update $RUNNER_FILE"
        return 1
    fi
    print_success "Updated $RUNNER_FILE to $new_version"
}

cmd_current() {
    check_files_exist
    get_version_raw
}

cmd_bump() {
    check_files_exist
    [ -z "${1:-}" ] && { print_error "Bump type required (major|minor|patch)"; exit 1; }
    current_ver=$(get_version_raw) || { print_error "Failed to get current version"; exit 1; }
    new_ver=$(bump_version "$current_ver" "$1") || exit 1
    echo "Bumping $current_ver → $new_ver ($1)"
    [ "${2:-}" = "dry-run" ] && { print_warning "DRY-RUN: no changes"; exit 0; }
    update_pyproject "$new_ver" || exit 1
    update_runner "$new_ver" || exit 1
    print_success "Bumped to $new_ver"
}

cmd_set() {
    check_files_exist
    [ -z "${1:-}" ] && { print_error "Version required (format: X.Y.Z)"; exit 1; }
    parse_version "$1" > /dev/null || exit 1
    update_pyproject "$1" || exit 1
    update_runner "$1" || exit 1
    print_success "Version set to $1"
}

cmd_validate() {
    check_files_exist
    print_header "Version Validation"
    local ver
    ver=$(get_version_raw) || { print_error "Failed to read version"; exit 1; }
    if parse_version "$ver" > /dev/null; then
        echo "Format: $ver"
        print_success "Valid version format"
    else
        exit 1
    fi
}

cmd_sync() {
    check_files_exist
    print_header "Sync Versions"
    local pyproject_ver runner_ver
    pyproject_ver=$(grep '^version = ' "$VERSION_FILE" | sed 's/version = "\(.*\)"/\1/')
    runner_ver=$(grep "__version__ = " "$RUNNER_FILE" | sed 's/__version__ = "\(.*\)"/\1/')
    echo "pyproject.toml: $pyproject_ver"
    echo "runner.py:      $runner_ver"
    if [ "$pyproject_ver" = "$runner_ver" ]; then
        print_success "Versions synchronized"
    else
        print_warning "Versions out of sync - syncing to $pyproject_ver"
        update_runner "$pyproject_ver" || exit 1
    fi
}

cmd_help() {
    cat << 'EOF'
Version Management - Semantic Versioning

Usage: bash version.sh [command] [args]

Commands:
  current                      Show current version
  bump (major|minor|patch)     Bump version (auto-update files)
  set VERSION                  Set specific version
  validate                     Validate version format
  sync                         Synchronize versions across files
  help                         Show this help message

Examples:
  bash version.sh current              # Output: 3.0.0
  bash version.sh bump patch           # Bump to 3.0.1
  bash version.sh bump minor dry-run   # Preview bump
  bash version.sh validate             # Check format validity

EOF
}

# Main dispatch
case "${1:-help}" in
    current)
        cmd_current
        ;;
    bump)
        shift
        cmd_bump "$@"
        ;;
    set)
        shift
        cmd_set "$@"
        ;;
    validate)
        cmd_validate
        ;;
    sync)
        cmd_sync
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        print_error "Unknown command: ${1:-help}"
        echo ""
        cmd_help
        exit 1
        ;;
esac

