#!/bin/bash
# setup.sh - Setup script for Python Script Runner
#
# This script:
# 1. Activates the virtual environment
# 2. Installs necessary dependencies
# 3. Runs setup.py with the chosen option
# 4. Keeps the virtual environment activated in the terminal
#
# Usage:
#   source ./setup.sh
#   OR
#   . ./setup.sh
#
# Note: Use 'source' or '.' to keep the virtual environment active after completion

set -e  # Exit on error

echo "======================================"
echo "Python Script Runner - Setup"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
VENV_PATH=".venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    echo "Please create a virtual environment first:"
    echo "  python3 -m venv .venv"
    exit 1
fi

# Activate virtual environment
echo -e "${BLUE}[1/3] Activating virtual environment...${NC}"
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo ""

# Upgrade pip
echo -e "${BLUE}[2/3] Upgrading pip...${NC}"
pip install --upgrade pip
echo -e "${GREEN}✓ pip upgraded${NC}"
echo ""

# Install build dependencies
echo -e "${BLUE}[2.5/3] Installing build dependencies...${NC}"
pip install setuptools wheel
echo -e "${GREEN}✓ Build dependencies installed${NC}"
echo ""

# Install project dependencies first (before setup.py runs)
echo -e "${BLUE}[2.7/3] Installing core dependencies...${NC}"
pip install psutil pyyaml requests
echo -e "${GREEN}✓ Core dependencies installed${NC}"
echo ""

# Install additional project dependencies
echo -e "${BLUE}[2.8/3] Installing additional dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt || echo "Warning: Some requirements.txt packages failed to install"
else
    echo "No requirements.txt found, skipping..."
fi
echo -e "${GREEN}✓ Additional dependencies installed${NC}"
echo ""

# Ask user what setup mode to use
echo -e "${YELLOW}======================================"
echo "Select setup mode:"
echo "======================================${NC}"
echo ""
echo "  1) develop      - Install in development mode (editable, default)"
echo "  2) install      - Install the package"
echo "  3) py2app       - Build macOS app bundle"
echo "  4) sdist        - Create source distribution"
echo "  5) bdist_wheel  - Create wheel distribution"
echo ""
echo -e -n "${BLUE}Enter your choice [1-5] (default: 1): ${NC}"
read -r choice

# Set default choice
choice=${choice:-1}

SETUP_COMMAND=""
NEEDS_PY2APP=false

case $choice in
    1)
        SETUP_COMMAND="develop"
        echo -e "${GREEN}Selected: Development mode${NC}"
        ;;
    2)
        SETUP_COMMAND="install"
        echo -e "${GREEN}Selected: Install${NC}"
        ;;
    3)
        SETUP_COMMAND="py2app"
        NEEDS_PY2APP=true
        echo -e "${GREEN}Selected: macOS app bundle${NC}"
        ;;
    4)
        SETUP_COMMAND="sdist"
        echo -e "${GREEN}Selected: Source distribution${NC}"
        ;;
    5)
        SETUP_COMMAND="bdist_wheel"
        echo -e "${GREEN}Selected: Wheel distribution${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using default (develop)${NC}"
        SETUP_COMMAND="develop"
        ;;
esac

echo ""

# Install py2app if needed
if [ "$NEEDS_PY2APP" = true ]; then
    echo -e "${BLUE}Installing py2app...${NC}"
    pip install py2app
    echo -e "${GREEN}✓ py2app installed${NC}"
    echo ""
    
    # Clean previous builds
    if [ -d "dist" ]; then
        echo -e "${BLUE}Cleaning previous build...${NC}"
        rm -rf dist
        echo -e "${GREEN}✓ Previous build cleaned${NC}"
        echo ""
    fi
    
    if [ -d "build" ]; then
        echo -e "${BLUE}Cleaning build cache...${NC}"
        rm -rf build
        echo -e "${GREEN}✓ Build cache cleaned${NC}"
        echo ""
    fi
fi

# Run setup.py with the selected command
echo -e "${BLUE}[3/3] Running: python setup.py $SETUP_COMMAND${NC}"
python setup.py $SETUP_COMMAND
echo ""

# Post-installation messages
if [ "$SETUP_COMMAND" = "develop" ]; then
    echo -e "${GREEN}======================================"
    echo "✓ Development installation completed!"
    echo "======================================${NC}"
    echo ""
    echo "You can now run the script runner:"
    echo "  python-script-runner test_script.py"
    echo "  python -m runner test_script.py"
    echo ""
elif [ "$SETUP_COMMAND" = "install" ]; then
    echo -e "${GREEN}======================================"
    echo "✓ Installation completed!"
    echo "======================================${NC}"
    echo ""
    echo "You can now run the script runner:"
    echo "  python-script-runner test_script.py"
    echo ""
elif [ "$SETUP_COMMAND" = "py2app" ]; then
    if [ -d "dist/Python Script Runner.app" ]; then
        echo -e "${GREEN}======================================"
        echo "✓ macOS app build completed successfully!"
        echo "======================================${NC}"
        echo ""
        echo "The macOS app is located at:"
        echo "  dist/Python Script Runner.app"
        echo ""
        echo "To test the app, run:"
        echo "  \"./dist/Python Script Runner.app/Contents/MacOS/Python Script Runner\" test_script.py"
        echo ""
        echo "To install the app, drag it to /Applications"
    else
        echo -e "${RED}======================================"
        echo "✗ Build failed!"
        echo "======================================${NC}"
        echo ""
        echo "Please check the error messages above."
        exit 1
    fi
elif [ "$SETUP_COMMAND" = "sdist" ]; then
    echo -e "${GREEN}======================================"
    echo "✓ Source distribution created!"
    echo "======================================${NC}"
    echo ""
    echo "Distribution files are in the 'dist' directory."
    echo ""
elif [ "$SETUP_COMMAND" = "bdist_wheel" ]; then
    echo -e "${GREEN}======================================"
    echo "✓ Wheel distribution created!"
    echo "======================================${NC}"
    echo ""
    echo "Distribution files are in the 'dist' directory."
    echo ""
fi

# Keep virtual environment activated
echo -e "${BLUE}======================================"
echo "Virtual Environment Status"
echo "======================================${NC}"
echo ""
echo -e "${GREEN}✓ Virtual environment is ACTIVE${NC}"
echo ""
echo "The virtual environment will remain active in this terminal."
echo "You can now run commands like:"
echo "  python-script-runner test_script.py"
echo "  python -m runner test_script.py"
echo ""
echo "To deactivate the virtual environment, type: deactivate"
echo ""
