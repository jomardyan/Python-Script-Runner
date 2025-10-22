# Compiled Executables - Quick Setup Guide

This guide explains how to use the pre-built Windows EXE and Linux DEB executables of Python Script Runner.

## 📥 Download

Executables are available on the [GitHub Releases](https://github.com/jomardyan/Python-Script-Runner/releases) page.

### Available Downloads

- `python-script-runner-X.Y.Z-windows.zip` - Windows standalone executable
- `python-script-runner_X.Y.Z_all.deb` - Linux/Ubuntu/Debian package

## 🪟 Windows Installation

### Option 1: Standalone (Portable)

```bash
# 1. Download: python-script-runner-X.Y.Z-windows.zip
# 2. Extract anywhere
unzip python-script-runner-X.Y.Z-windows.zip
cd python-script-runner-X.Y.Z

# 3. Run directly
python-script-runner.exe --help
```

**Advantages:**
- No installation needed
- No Python required
- Portable - works on any Windows 7 SP1+ machine
- Can run from USB drive

### Option 2: Add to PATH (Global Access)

```cmd
# 1. Extract the ZIP to a permanent location, e.g.:
C:\Program Files\python-script-runner

# 2. Add to PATH:
#    - Right-click This PC > Properties
#    - Click "Advanced system settings"
#    - Click "Environment Variables"
#    - Under "System variables", click "New"
#    - Variable name: PATH (if not exists)
#    - Add: C:\Program Files\python-script-runner

# 3. Now use from anywhere in Command Prompt:
python-script-runner.exe script.py
```

### Windows Usage Examples

```cmd
# Basic execution
python-script-runner.exe myscript.py

# With arguments
python-script-runner.exe train.py --epochs 100 --batch-size 32

# With monitoring
python-script-runner.exe script.py --json-output metrics.json

# With Slack alerts
python-script-runner.exe script.py --slack-webhook "https://hooks.slack.com/..."

# With CI/CD gates
python-script-runner.exe tests/suite.py --add-gate cpu_max:90 --add-gate memory_max_mb:1024
```

### Windows Troubleshooting

| Issue | Solution |
|-------|----------|
| **Antivirus Warning** | PyInstaller-compiled executables can trigger false positives. This is normal and safe to ignore. Add the .exe to your antivirus exceptions. |
| **VCRUNTIME140.dll Missing** | Install Visual C++ Redistributable: https://support.microsoft.com/help/2977003 |
| **MSVCP140.dll Missing** | Same as above - install Visual C++ Redistributable |
| **"Not a valid Win32 application"** | Windows 7 without SP1 detected. Please install Windows 7 Service Pack 1 |
| **Command Not Found** | Ensure the EXE directory is added to PATH |
| **Slow Startup** | First run is slower due to Python runtime initialization. Subsequent runs will be cached. |

## 🐧 Linux Installation

### Option 1: System Package Manager (Recommended)

```bash
# 1. Download: python-script-runner_X.Y.Z_all.deb

# 2. Install with dependency resolution
sudo apt install ./python-script-runner_X.Y.Z_all.deb

# 3. Use globally
python-script-runner --help
```

**Advantages:**
- Automatic dependency installation
- System integration (menu, command completion)
- Easy upgrades: `sudo apt upgrade python-script-runner`
- Easy removal: `sudo apt remove python-script-runner`

### Option 2: Direct Installation

```bash
# 1. Download: python-script-runner_X.Y.Z_all.deb

# 2. Install directly
sudo dpkg -i python-script-runner_X.Y.Z_all.deb

# 3. Install any missing dependencies
sudo apt install -f

# 4. Use globally
python-script-runner --help
```

### Option 3: Portable (Extract Only)

```bash
# For portable use without system installation:
# 1. Install dependencies manually
sudo apt install python3 python3-psutil python3-yaml python3-requests

# 2. Extract the DEB (if needed)
ar x python-script-runner_X.Y.Z_all.deb
tar -xzf data.tar.gz

# 3. Use the extracted files
./usr/bin/python-script-runner --help
```

### Linux Usage Examples

```bash
# Basic execution
python-script-runner myscript.py

# With arguments
python-script-runner train.py --epochs 100 --batch-size 32

# With monitoring
python-script-runner script.py --json-output metrics.json

# With Slack alerts
python-script-runner script.py --slack-webhook "https://hooks.slack.com/..."

# With CI/CD gates
python-script-runner tests/suite.py --add-gate cpu_max:90 --add-gate memory_max_mb:1024

# Check version
python-script-runner --version
```

### Linux Troubleshooting

| Issue | Solution |
|-------|----------|
| **"command not found"** | Ensure `/usr/bin` is in PATH (usually default). Run `echo $PATH` to verify. |
| **"Permission denied"** | Run with `sudo`: `sudo python-script-runner script.py` |
| **"No module named psutil"** | Run `sudo apt install python3-psutil python3-yaml python3-requests` |
| **Installation fails with 404** | Ensure you're on a Debian-based system (Ubuntu, Debian, etc.) |
| **Broken dependencies** | Run `sudo apt install -f` to fix |

### Uninstall

```bash
# Via package manager
sudo apt remove python-script-runner

# Or via dpkg
sudo dpkg -r python-script-runner

# Clean up config files (optional)
sudo apt purge python-script-runner
```

## 📦 System Requirements

### Windows EXE

- **OS**: Windows 7 SP1, Windows 10, Windows 11
- **Architecture**: x86_64 (64-bit)
- **Dependencies**: Microsoft Visual C++ Runtime
- **Disk Space**: ~70 MB
- **Python**: ❌ NOT required

### Linux DEB

- **Distribution**: Debian 9+, Ubuntu 18.04+, Linux Mint 19+
- **Architecture**: All (universal Python package)
- **Dependencies**: Python 3.6+, pip, psutil, pyyaml, requests
- **Disk Space**: ~10 MB (plus ~50 MB for dependencies)
- **Package Manager**: apt

## 🔍 Verification

### Verify File Integrity

```bash
# Windows
certutil -hashfile python-script-runner-X.Y.Z-windows.zip SHA256
# Compare with .sha256 file

# Linux
sha256sum python-script-runner_X.Y.Z_all.deb
# Compare with .deb.sha256 file

# Or use the provided checksums
sha256sum -c python-script-runner_X.Y.Z_all.deb.sha256
sha256sum -c python-script-runner-X.Y.Z-windows.zip.sha256
```

### Verify Installation

```bash
# Windows
python-script-runner.exe --version

# Linux
python-script-runner --version
```

## 📊 Configuration

Create a `config.yaml` for advanced configuration:

```yaml
# config.yaml
alerts:
  - name: cpu_high
    condition: cpu_max > 85
    channels: [slack]
    severity: WARNING

performance_gates:
  - metric_name: cpu_max
    max_value: 90
  - metric_name: memory_max_mb
    max_value: 1024

notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK"
```

Use it:

```bash
# Windows
python-script-runner.exe script.py --config config.yaml

# Linux
python-script-runner script.py --config config.yaml
```

## 🚀 Common Use Cases

### CI/CD Integration

```bash
# Linux
python-script-runner tests/suite.py \
  --add-gate cpu_max:85 \
  --add-gate memory_max_mb:2048 \
  --junit-output results.xml

# Windows (Command Prompt)
python-script-runner.exe tests/suite.py --add-gate cpu_max:85 --add-gate memory_max_mb:2048 --junit-output results.xml
```

### Performance Monitoring

```bash
# Linux
python-script-runner script.py \
  --history-db metrics.db \
  --detect-anomalies \
  --json-output current.json

# Windows
python-script-runner.exe script.py --history-db metrics.db --json-output current.json
```

### Slack Notifications

```bash
# Linux
python-script-runner script.py --slack-webhook "https://hooks.slack.com/services/..."

# Windows
python-script-runner.exe script.py --slack-webhook "https://hooks.slack.com/services/..."
```

## 📚 Documentation

- **Full Guide**: See README.md in the release
- **Building Guide**: See BUILD_EXECUTABLES.md
- **GitHub**: https://github.com/jomardyan/Python-Script-Runner
- **Issues**: https://github.com/jomardyan/Python-Script-Runner/issues

## 💡 Pro Tips

1. **Windows Users**: Add to PATH for global access from any directory
2. **Linux Users**: Use `sudo apt install -f` if installation has dependency issues
3. **Both**: Keep the config.yaml file in the same directory as your script for easy reference
4. **Version Checking**: Always verify SHA256 checksums for downloaded files
5. **Portable Distribution**: Windows EXE is ideal for packaging into CI/CD containers

## 📝 FAQ

**Q: Is Python required?**
- Windows: NO, Python is included in the executable
- Linux: YES, Python 3.6+ is required (comes with most distros)

**Q: Can I use on older versions of Windows/Linux?**
- Windows: Minimum Windows 7 SP1
- Linux: Minimum Debian 9 or Ubuntu 18.04

**Q: Is the executable portable?**
- Windows: YES, it's a standalone file
- Linux: YES, it works on any Debian-based system

**Q: Can I distribute these executables?**
- YES, under the MIT License terms
- Include the LICENSE file with any distribution

**Q: Are updates automatic?**
- Windows: NO, you need to download the new .zip
- Linux: YES, run `sudo apt upgrade` to update the DEB

---

**Questions?** Open an issue on [GitHub](https://github.com/jomardyan/Python-Script-Runner/issues)
