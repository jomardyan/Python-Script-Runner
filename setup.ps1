# setup.ps1 - Setup script for Python Script Runner (Windows)
#
# This script:
# 1. Checks Python installation and version
# 2. Creates/activates virtual environment
# 3. Installs necessary dependencies
# 4. Runs setup.py with the chosen option
# 5. Keeps the virtual environment activated in the terminal
#
# Usage:::
#   .\setup.ps1
#   OR (to bypass execution policy if needed)
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
#
# Note: Run from PowerShell (not CMD)

# Requires PowerShell 5.1 or later (Windows 10+)
#Requires -Version 5.1

# Enable strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Function to Write colored output
function Write-Color {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

function Write-Success {
    param([string]$Text)
    Write-Color "✓ $Text" "Green"
}

function Write-Info {
    param([string]$Text)
    Write-Color $Text "Cyan"
}

function Write-Warning {
    param([string]$Text)
    Write-Color $Text "Yellow"
}

function Write-ErrorMsg {
    param([string]$Text)
    Write-Color $Text "Red"
}

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Color "======================================" "Yellow"
    Write-Color $Text "Yellow"
    Write-Color "======================================" "Yellow"
    Write-Host ""
}

# Clear screen for clean output
Clear-Host

Write-Section "Python Script Runner - Setup"

# Get script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

# Check if Python is installed
Write-Info "Checking Python installation..."

$pythonCmd = $null
$pythonVersion = $null

# Try to find Python (check python3 first, then python, then py launcher)
foreach ($cmd in @("python3", "python", "py")) {
    try {
        $version = & $cmd --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pythonCmd = $cmd
            $pythonVersion = $version
            break
        }
    }
    catch {
        continue
    }
}

if (-not $pythonCmd) {
    Write-Section "Python Not Found"
    Write-ErrorMsg "Python 3 is required but not installed on your system."
    Write-Host ""
    Write-Host "Please install Python 3 using one of these methods:"
    Write-Host ""
    Write-Color "Option 1: Official Python Installer (Recommended)" "Cyan"
    Write-Host "  1. Download from: https://www.python.org/downloads/"
    Write-Host "  2. Run the installer"
    Write-Host "  3. ✅ CHECK 'Add Python to PATH' during installation"
    Write-Host "  4. Choose 'Install Now' or 'Customize' for advanced options"
    Write-Host ""
    Write-Color "Option 2: Windows Package Manager (winget)" "Cyan"
    Write-Host "  winget install Python.Python.3.12"
    Write-Host ""
    Write-Color "Option 3: Chocolatey" "Cyan"
    Write-Host "  choco install python"
    Write-Host ""
    Write-Color "Option 4: Microsoft Store" "Cyan"
    Write-Host "  Search for 'Python 3.12' in Microsoft Store"
    Write-Host ""
    Write-Host "After installing Python, restart PowerShell and run this script again."
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Success "Python $pythonVersion found"
Write-Host ""

# Check Python version (must be 3.6+)
try {
    $versionOutput = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $versionParts = $versionOutput.Split('.')
    $majorVersion = [int]$versionParts[0]
    $minorVersion = [int]$versionParts[1]

    if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 6)) {
        Write-Section "Python Version Too Old"
        Write-ErrorMsg "Python 3.6 or higher is required."
        Write-ErrorMsg "Found: Python $versionOutput"
        Write-Host ""
        Write-Host "Please upgrade Python to version 3.6 or higher."
        Write-Host "Download from: https://www.python.org/downloads/"
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}
catch {
    Write-Warning "Could not verify Python version, continuing anyway..."
}

# Check if virtual environment exists
$VENV_PATH = ".venv"

if (-not (Test-Path $VENV_PATH)) {
    Write-Section "Virtual Environment Not Found"
    Write-Host "A virtual environment is required to run this setup."
    Write-Host "Location: $VENV_PATH"
    Write-Host ""
    
    $createVenv = Read-Host "Would you like to create it now? [Y/n]"
    
    # Default to Yes if user just presses Enter
    if ([string]::IsNullOrWhiteSpace($createVenv)) {
        $createVenv = "Y"
    }
    
    if ($createVenv -match "^[Yy]") {
        Write-Host ""
        Write-Info "Creating virtual environment at $VENV_PATH..."
        
        try {
            & $pythonCmd -m venv $VENV_PATH
            Write-Success "Virtual environment created successfully"
            Write-Host ""
        }
        catch {
            Write-ErrorMsg "Failed to create virtual environment"
            Write-Host "Error: $_"
            Write-Host ""
            Write-Host "Please create it manually:"
            Write-Host "  $pythonCmd -m venv .venv"
            Write-Host "Then run this script again."
            Write-Host ""
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
    else {
        Write-Host ""
        Write-ErrorMsg "Setup cancelled."
        Write-Host "Please create a virtual environment manually:"
        Write-Host "  $pythonCmd -m venv .venv"
        Write-Host "Then run this script again."
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Activate virtual environment
Write-Info "[1/3] Activating virtual environment..."

# Detect OS and use correct activation script path
# Check if running on Windows (compatible with PowerShell 5.1 and 6+)
$isWindowsOS = if (Test-Path variable:IsWindows) { $IsWindows } else { $true }

if ($isWindowsOS) {
    # Windows: Scripts\Activate.ps1
    $activateScript = Join-Path $VENV_PATH "Scripts\Activate.ps1"
} else {
    # macOS/Linux: bin/activate (need to source it via sh)
    $activateScript = Join-Path $VENV_PATH "bin/Activate.ps1"
    # Fallback to bash activation if PowerShell activation not available
    if (-not (Test-Path $activateScript)) {
        $activateScript = Join-Path $VENV_PATH "bin/activate"
    }
}

if (-not (Test-Path $activateScript)) {
    Write-ErrorMsg "Virtual environment activation script not found at: $activateScript"
    Write-Host "Please recreate the virtual environment:"
    if ($isWindowsOS) {
        Write-Host "  Remove-Item -Recurse -Force .venv"
        Write-Host "  $pythonCmd -m venv .venv"
    } else {
        Write-Host "  rm -rf .venv"
        Write-Host "  $pythonCmd -m venv .venv"
    }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    if ($isWindowsOS) {
        # Windows: Check execution policy and activate PowerShell script
        $policy = Get-ExecutionPolicy -Scope CurrentUser
        if ($policy -eq "Restricted") {
            Write-Warning "Execution policy is Restricted. Temporarily setting to RemoteSigned for this session..."
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
        }
        & $activateScript
    } else {
        # macOS/Linux: Source the activation script
        if ($activateScript -like "*.ps1") {
            # PowerShell activation script exists
            & $activateScript
        } else {
            # Use bash activation script via sourcing in current shell
            # Note: PowerShell on Unix can't directly source bash scripts
            # We'll set the PATH manually instead
            $venvBin = Join-Path $VENV_PATH "bin"
            $env:PATH = "$venvBin$([System.IO.Path]::PathSeparator)$env:PATH"
            $env:VIRTUAL_ENV = (Resolve-Path $VENV_PATH).Path
            
            # Update prompt to show venv is active
            function global:prompt {
                "(.venv) PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
            }
        }
    }
    Write-Success "Virtual environment activated"
    Write-Host ""
}
catch {
    Write-ErrorMsg "Failed to activate virtual environment"
    Write-Host "Error: $_"
    Write-Host ""
    if ($isWindowsOS) {
        Write-Host "Try running PowerShell as Administrator and executing:"
        Write-Host "  Set-ExecutionPolicy RemoteSigned"
    } else {
        Write-Host "Try manually activating:"
        Write-Host "  source .venv/bin/activate"
    }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Upgrade pip
Write-Info "[2/3] Upgrading pip..."
try {
    & python -m pip install --upgrade pip --quiet
    Write-Success "pip upgraded"
    Write-Host ""
}
catch {
    Write-Warning "Failed to upgrade pip, continuing anyway..."
    Write-Host ""
}

# Install build dependencies
Write-Info "[2.5/3] Installing build dependencies..."
try {
    & python -m pip install setuptools wheel --quiet
    Write-Success "Build dependencies installed"
    Write-Host ""
}
catch {
    Write-Warning "Failed to install build dependencies, continuing anyway..."
    Write-Host ""
}

# Install core dependencies
Write-Info "[2.7/3] Installing core dependencies..."
try {
    & python -m pip install psutil pyyaml requests --quiet
    Write-Success "Core dependencies installed"
    Write-Host ""
}
catch {
    Write-Warning "Failed to install some core dependencies, continuing anyway..."
    Write-Host ""
}

# Install additional project dependencies
Write-Info "[2.8/3] Installing additional dependencies..."
if (Test-Path "requirements.txt") {
    try {
        & python -m pip install -r requirements.txt --quiet
        Write-Success "Additional dependencies installed"
        Write-Host ""
    }
    catch {
        Write-Warning "Some requirements.txt packages failed to install"
        Write-Host ""
    }
}
else {
    Write-Host "No requirements.txt found, skipping..."
    Write-Host ""
}

# Ask user what setup mode to use
Write-Section "Select setup mode:"
Write-Host "  1) develop      - Install in development mode (editable, default)"
Write-Host "  2) install      - Install the package"
Write-Host "  3) sdist        - Create source distribution"
Write-Host "  4) bdist_wheel  - Create wheel distribution"
Write-Host "  5) py2exe       - Build Windows executable (requires py2exe)"
Write-Host ""

$choice = Read-Host "Enter your choice [1-5] (default: 1)"

# Set default choice
if ([string]::IsNullOrWhiteSpace($choice)) {
    $choice = "1"
}

$SETUP_COMMAND = ""
$NEEDS_PY2EXE = $false

switch ($choice) {
    "1" {
        $SETUP_COMMAND = "develop"
        Write-Success "Selected: Development mode"
    }
    "2" {
        $SETUP_COMMAND = "install"
        Write-Success "Selected: Install"
    }
    "3" {
        $SETUP_COMMAND = "sdist"
        Write-Success "Selected: Source distribution"
    }
    "4" {
        $SETUP_COMMAND = "bdist_wheel"
        Write-Success "Selected: Wheel distribution"
    }
    "5" {
        $SETUP_COMMAND = "py2exe"
        $NEEDS_PY2EXE = $true
        Write-Success "Selected: Windows executable"
    }
    default {
        Write-Warning "Invalid choice. Using default (develop)"
        $SETUP_COMMAND = "develop"
    }
}

Write-Host ""

# Install py2exe if needed
if ($NEEDS_PY2EXE) {
    Write-Info "Installing py2exe..."
    try {
        & python -m pip install py2exe
        Write-Success "py2exe installed"
        Write-Host ""
    }
    catch {
        Write-ErrorMsg "Failed to install py2exe"
        Write-Host "Error: $_"
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
    
    # Clean previous builds
    if (Test-Path "dist") {
        Write-Info "Cleaning previous build..."
        Remove-Item -Recurse -Force "dist"
        Write-Success "Previous build cleaned"
        Write-Host ""
    }
    
    if (Test-Path "build") {
        Write-Info "Cleaning build cache..."
        Remove-Item -Recurse -Force "build"
        Write-Success "Build cache cleaned"
        Write-Host ""
    }
}

# Run setup.py with the selected command
Write-Info "[3/3] Running: python setup.py $SETUP_COMMAND"
try {
    & python setup.py $SETUP_COMMAND
    Write-Host ""
}
catch {
    Write-ErrorMsg "Setup command failed"
    Write-Host "Error: $_"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Post-installation messages
if ($SETUP_COMMAND -eq "develop") {
    Write-Section "✓ Development installation completed!"
    Write-Host "You can now run the script runner:"
    Write-Host "  python-script-runner examples/sample_script.py"
    Write-Host "  python -m runner examples/sample_script.py"
    Write-Host ""
}
elseif ($SETUP_COMMAND -eq "install") {
    Write-Section "✓ Installation completed!"
    Write-Host "You can now run the script runner:"
    Write-Host "  python-script-runner examples/sample_script.py"
    Write-Host ""
}
elseif ($SETUP_COMMAND -eq "py2exe") {
    if (Test-Path "dist\python-script-runner.exe") {
        Write-Section "✓ Windows executable build completed successfully!"
        Write-Host "The Windows executable is located at:"
        Write-Host "  dist\python-script-runner.exe"
        Write-Host ""
        Write-Host "To test the executable, run:"
        Write-Host "  .\dist\python-script-runner.exe examples/sample_script.py"
        Write-Host ""
        Write-Host "You can distribute this executable to other Windows machines"
        Write-Host "without requiring Python installation."
    }
    else {
        Write-Section "✗ Build failed!"
        Write-Host "Please check the error messages above."
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}
elseif ($SETUP_COMMAND -eq "sdist") {
    Write-Section "✓ Source distribution created!"
    Write-Host "Distribution files are in the 'dist' directory."
    Write-Host ""
}
elseif ($SETUP_COMMAND -eq "bdist_wheel") {
    Write-Section "✓ Wheel distribution created!"
    Write-Host "Distribution files are in the 'dist' directory."
    Write-Host ""
}

# Keep virtual environment activated
Write-Section "Virtual Environment Status"
Write-Success "Virtual environment is ACTIVE"
Write-Host ""
Write-Host "The virtual environment will remain active in this PowerShell session."
Write-Host "You can now run commands like:"
Write-Host "  python-script-runner examples/sample_script.py"
Write-Host "  python -m runner examples/sample_script.py"
Write-Host ""
Write-Host "To deactivate the virtual environment, type: deactivate"
Write-Host ""
Write-Host "Note: If you close this PowerShell window, you'll need to"
Write-Host "reactivate the virtual environment in a new session:"
if ($isWindowsOS) {
    Write-Host "  .\.venv\Scripts\Activate.ps1"
} else {
    Write-Host "  source .venv/bin/activate  (bash/zsh)"
    Write-Host "  . .venv/bin/Activate.ps1   (PowerShell on Unix)"
}
Write-Host ""

# Pause at the end so user can read messages (Windows only, optional on Unix)
if ($isWindowsOS) {
    Read-Host "Press Enter to continue"
} else {
    Write-Host "Setup complete! Virtual environment is ready to use."
}
