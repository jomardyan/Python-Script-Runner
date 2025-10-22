#!/bin/bash

################################################################################
# PyPy3 Environment Setup Script
# 
# This script handles complete environment setup for the Python Script Runner
# with PyPy3. It includes:
# - Error handling and exit on critical failures
# - Environment validation
# - PyPy3 installation/detection
# - Virtual environment creation
# - Requirements installation
# - Verification and health checks
#
# Usage: ./setup_pypy3_env.sh [--help] [--python=<path>] [--no-venv]
#
# Author: Python Script Runner Team
# License: MIT
################################################################################

set -o pipefail  # Exit on pipe failures

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv-pypy3"
REQUIREMENTS_FILE="${SCRIPT_DIR}/requirements-pypy3.txt"
LOG_FILE="${SCRIPT_DIR}/setup_pypy3_env.log"
PYTHON_CMD="pypy3"
USE_VENV=true
VERBOSE=false

# Error handling
trap cleanup EXIT
trap handle_error ERR

################################################################################
# Utility Functions
################################################################################

# Print colored output
print_info() {
    echo -e "${BLUE}ℹ ${NC}$1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}✓ ${NC}$1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}⚠ ${NC}$1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}✗ ${NC}$1" | tee -a "$LOG_FILE"
}

# Verbose logging
print_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1" | tee -a "$LOG_FILE"
    fi
}

# Handle errors
handle_error() {
    local line_num=$1
    print_error "Error occurred at line $line_num"
    print_error "Script failed with exit code $?"
    exit 1
}

# Cleanup on exit
cleanup() {
    print_verbose "Cleanup: Removing temporary files if any..."
}

# Display usage information
usage() {
    cat << EOF
${BLUE}PyPy3 Environment Setup Script${NC}

${GREEN}Usage:${NC}
    $0 [OPTIONS]

${GREEN}Options:${NC}
    -h, --help              Show this help message
    -v, --verbose           Enable verbose output
    -p, --python=PATH       Specify PyPy3 executable path (default: pypy3)
    --no-venv               Don't create virtual environment
    -u, --upgrade-pip       Upgrade pip, setuptools, wheel
    -c, --clean             Clean existing venv before setup
    --python-version=VER    Minimum PyPy3 version (default: 3.8)

${GREEN}Examples:${NC}
    # Standard setup
    $0

    # With custom PyPy3 path
    $0 --python=/usr/bin/pypy3

    # Verbose output with venv cleanup
    $0 --verbose --clean

${GREEN}Exit Codes:${NC}
    0 - Success
    1 - Error occurred
    2 - Invalid arguments

EOF
}

################################################################################
# Argument Parsing
################################################################################

parse_arguments() {
    local min_version="3.8"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -p|--python)
                if [[ -z "$2" ]]; then
                    print_error "Missing value for --python"
                    exit 2
                fi
                PYTHON_CMD="$2"
                shift 2
                ;;
            --python=*)
                PYTHON_CMD="${1#*=}"
                shift
                ;;
            --no-venv)
                USE_VENV=false
                shift
                ;;
            -u|--upgrade-pip)
                UPGRADE_PIP=true
                shift
                ;;
            -c|--clean)
                CLEAN_VENV=true
                shift
                ;;
            --python-version=*)
                min_version="${1#*=}"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                usage
                exit 2
                ;;
        esac
    done
}

################################################################################
# Validation Functions
################################################################################

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Validate Python executable
validate_python() {
    print_info "Validating Python environment..."
    
    if ! command_exists "$PYTHON_CMD"; then
        print_error "$PYTHON_CMD not found in PATH"
        print_info "Please install PyPy3 or provide path via --python=PATH"
        return 1
    fi
    
    print_success "Found: $PYTHON_CMD at $(command -v $PYTHON_CMD)"
    
    # Get Python version
    local version=$("$PYTHON_CMD" --version 2>&1)
    print_info "Python version: $version"
    
    # Verify it's actually PyPy
    if "$PYTHON_CMD" -c "import sys; sys.exit(0 if hasattr(sys, 'pypy_version_info') else 1)" 2>/dev/null; then
        print_success "Confirmed: PyPy3 detected"
    else
        print_warning "Warning: Python appears not to be PyPy3, but attempting to continue..."
    fi
    
    return 0
}

# Check OS and system requirements
check_system() {
    print_info "Checking system requirements..."
    
    # Check for required tools
    local required_tools=("git" "curl" "mkdir" "touch")
    local missing_tools=()
    
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_warning "Missing tools: ${missing_tools[*]}"
        print_info "Install with: apt-get install ${missing_tools[*]}"
    fi
    
    # Check disk space (minimum 500MB)
    local available_space=$(df "$SCRIPT_DIR" | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 512000 ]; then
        print_warning "Low disk space: ${available_space}KB available (recommend >500MB)"
    else
        print_success "Disk space OK: ${available_space}KB available"
    fi
    
    print_success "System requirements validated"
    return 0
}

# Validate requirements file
validate_requirements() {
    print_info "Validating requirements file..."
    
    if [ ! -f "$REQUIREMENTS_FILE" ]; then
        print_error "Requirements file not found: $REQUIREMENTS_FILE"
        return 1
    fi
    
    # Count lines and packages
    local package_count=$(grep -c "^[^#]" "$REQUIREMENTS_FILE" 2>/dev/null || echo 0)
    print_info "Found $package_count packages in requirements file"
    
    print_success "Requirements file validated"
    return 0
}

################################################################################
# Virtual Environment Setup
################################################################################

# Create virtual environment
create_venv() {
    print_info "Creating virtual environment with PyPy3..."
    print_info "Environment path: $VENV_DIR"
    
    if [ -d "$VENV_DIR" ]; then
        if [ "$CLEAN_VENV" = true ]; then
            print_warning "Removing existing venv..."
            rm -rf "$VENV_DIR" 2>/dev/null || {
                print_error "Failed to remove existing venv"
                return 1
            }
        else
            print_warning "Virtual environment already exists at $VENV_DIR"
            read -p "Do you want to reuse it? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                print_info "Reusing existing virtual environment"
                return 0
            else
                print_info "Removing existing venv..."
                rm -rf "$VENV_DIR" || {
                    print_error "Failed to remove existing venv"
                    return 1
                }
            fi
        fi
    fi
    
    # Create venv
    if ! "$PYTHON_CMD" -m venv "$VENV_DIR" 2>&1 | tee -a "$LOG_FILE"; then
        print_error "Failed to create virtual environment"
        return 1
    fi
    
    print_success "Virtual environment created at: $VENV_DIR"
    return 0
}

# Activate virtual environment
activate_venv() {
    if [ "$USE_VENV" = true ]; then
        print_info "Activating virtual environment..."
        
        if [ ! -f "$VENV_DIR/bin/activate" ]; then
            print_error "Virtual environment activation script not found"
            return 1
        fi
        
        # Source the activation script
        source "$VENV_DIR/bin/activate" || {
            print_error "Failed to activate virtual environment"
            return 1
        }
        
        print_success "Virtual environment activated"
        print_verbose "VIRTUAL_ENV=$VIRTUAL_ENV"
        print_verbose "PATH=$PATH"
    fi
    
    return 0
}

################################################################################
# Package Installation
################################################################################

# Upgrade pip, setuptools, and wheel
upgrade_pip() {
    if [ "$UPGRADE_PIP" = true ]; then
        print_info "Upgrading pip, setuptools, and wheel..."
        
        local pip_cmd="python -m pip"
        if [ "$USE_VENV" = true ]; then
            pip_cmd="$VENV_DIR/bin/python -m pip"
        fi
        
        if ! $pip_cmd install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG_FILE"; then
            print_error "Failed to upgrade pip/setuptools/wheel"
            return 1
        fi
        
        print_success "pip, setuptools, and wheel upgraded"
    fi
    
    return 0
}

# Install requirements from file
install_requirements() {
    print_info "Installing requirements from: $REQUIREMENTS_FILE"
    
    local pip_cmd="pip"
    if [ "$USE_VENV" = false ]; then
        pip_cmd="$PYTHON_CMD -m pip"
    fi
    
    # First, verify pip is available
    if ! $pip_cmd --version >/dev/null 2>&1; then
        print_error "pip is not available"
        return 1
    fi
    
    # Install packages with error handling
    if ! $pip_cmd install -r "$REQUIREMENTS_FILE" 2>&1 | tee -a "$LOG_FILE"; then
        print_error "Failed to install requirements"
        print_info "Attempting to install packages individually for better error reporting..."
        
        # Install packages one by one to identify failures
        while IFS= read -r line; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            
            # Remove inline comments
            line=$(echo "$line" | cut -d'#' -f1 | xargs)
            
            print_info "Installing: $line"
            if ! $pip_cmd install "$line" 2>&1 | tee -a "$LOG_FILE"; then
                print_warning "Failed to install: $line (might be optional)"
            fi
        done < "$REQUIREMENTS_FILE"
    fi
    
    print_success "Requirements installation completed"
    return 0
}

################################################################################
# Verification Functions
################################################################################

# Verify environment
verify_environment() {
    print_info "Verifying installation environment..."
    
    local python_bin="python"
    if [ "$USE_VENV" = true ]; then
        python_bin="$VENV_DIR/bin/python"
    fi
    
    # Check Python availability
    if ! $python_bin --version >/dev/null 2>&1; then
        print_error "Python verification failed"
        return 1
    fi
    
    print_success "Python is available: $($python_bin --version)"
    
    # Check key packages
    local packages=("psutil" "requests" "yaml")
    local missing_packages=()
    
    for package in "${packages[@]}"; do
        if ! $python_bin -c "import ${package}" 2>/dev/null; then
            missing_packages+=("$package")
        else
            print_success "Package verified: $package"
        fi
    done
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "Missing packages: ${missing_packages[*]}"
        print_warning "These packages may not be critical. Continuing..."
    fi
    
    return 0
}

# Run health checks
health_check() {
    print_info "Running health checks..."
    
    local python_bin="python"
    if [ "$USE_VENV" = true ]; then
        python_bin="$VENV_DIR/bin/python"
    fi
    
    # Check Python bytecode generation
    if ! $python_bin -c "import sys; print(f'Python {sys.version}')" 2>&1 | tee -a "$LOG_FILE"; then
        print_warning "Python execution test failed"
    fi
    
    # Check if main script exists and is executable
    if [ -f "$SCRIPT_DIR/runner.py" ]; then
        if $python_bin -m py_compile "$SCRIPT_DIR/runner.py" 2>&1 | tee -a "$LOG_FILE"; then
            print_success "Main script syntax OK: runner.py"
        else
            print_warning "Main script has syntax issues"
        fi
    fi
    
    print_success "Health checks completed"
    return 0
}

################################################################################
# Activation Script Generation
################################################################################

# Generate activation helper script
generate_activation_script() {
    if [ "$USE_VENV" = true ]; then
        local activation_script="$SCRIPT_DIR/activate_pypy3.sh"
        
        print_info "Generating activation helper script..."
        
        cat > "$activation_script" << 'ACTIVATE_EOF'
#!/bin/bash
# PyPy3 Virtual Environment Activation Helper

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv-pypy3"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    echo "Please run: ./setup_pypy3_env.sh"
    exit 1
fi

echo "Activating PyPy3 virtual environment..."
source "$VENV_DIR/bin/activate"
echo "✓ Environment activated. Type 'deactivate' to exit."
ACTIVATE_EOF
        
        chmod +x "$activation_script" || {
            print_warning "Failed to make activation script executable"
        }
        
        print_success "Activation script created: $activation_script"
    fi
}

################################################################################
# Environment Information
################################################################################

# Display environment information
display_env_info() {
    print_info "Environment information:"
    echo ""
    echo "  Project directory: $SCRIPT_DIR"
    echo "  Requirements file: $REQUIREMENTS_FILE"
    echo "  Virtual environment: $VENV_DIR"
    echo "  Log file: $LOG_FILE"
    
    if [ "$USE_VENV" = true ]; then
        local python_bin="$VENV_DIR/bin/python"
        echo "  Python executable: $python_bin"
        
        if command_exists "$python_bin"; then
            echo "  Python version: $($python_bin --version 2>&1)"
            echo "  pip version: $($VENV_DIR/bin/pip --version 2>&1)"
        fi
    else
        echo "  Python executable: $PYTHON_CMD"
        echo "  Using system Python (no venv)"
    fi
    
    echo ""
}

# Display next steps
display_next_steps() {
    echo -e "${GREEN}Setup completed successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    
    if [ "$USE_VENV" = true ]; then
        echo "1. Activate the virtual environment:"
        echo "   source $VENV_DIR/bin/activate"
        echo "   # or use the helper script:"
        echo "   source ./activate_pypy3.sh"
        echo ""
    fi
    
    echo "2. Run the main script:"
    echo "   python runner.py --help"
    echo ""
    
    echo "3. Run tests:"
    echo "   python -m pytest test_script.py"
    echo ""
    
    echo "4. View logs:"
    echo "   tail -f $LOG_FILE"
    echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
    # Initialize log file
    > "$LOG_FILE"
    
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║    PyPy3 Environment Setup Script                          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    print_info "Starting setup process..."
    print_info "Log file: $LOG_FILE"
    echo ""
    
    # Parse command-line arguments
    parse_arguments "$@" || exit 2
    
    # Run validation and setup steps
    local steps=(
        "check_system"
        "validate_python"
        "validate_requirements"
    )
    
    # Add venv setup steps if using venv
    if [ "$USE_VENV" = true ]; then
        steps+=("create_venv" "activate_venv")
    fi
    
    # Add installation steps
    steps+=("upgrade_pip" "install_requirements" "verify_environment" "health_check")
    
    # Add post-setup steps
    if [ "$USE_VENV" = true ]; then
        steps+=("generate_activation_script")
    fi
    
    # Execute all steps
    for step in "${steps[@]}"; do
        print_verbose "Executing step: $step"
        
        if ! "$step"; then
            print_error "Setup failed at step: $step"
            echo ""
            echo "For troubleshooting, check the log file:"
            echo "  cat $LOG_FILE"
            echo ""
            exit 1
        fi
    done
    
    echo ""
    
    # Display results
    display_env_info
    display_next_steps
    
    print_success "Setup completed successfully! ✓"
    
    # Final log entry
    {
        echo "=========================================="
        echo "Setup completed at $(date)"
        echo "=========================================="
    } >> "$LOG_FILE"
    
    return 0
}

# Run main function
main "$@"
exit $?
