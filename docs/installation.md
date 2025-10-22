# Installation Guide

## System Requirements

### Minimum
- **Python**: 3.6+ (3.8+ recommended)
- **OS**: Linux, macOS, Windows (with WSL2)
- **RAM**: 256 MB minimum (512 MB recommended)
- **Disk**: ~50 MB for installation

### Required Dependencies
- **psutil** (5.9.0+) - Process monitoring
- **PyYAML** (6.0+) - Config parsing
- **requests** (2.31.0+) - HTTP requests

### Optional Dependencies
- **fastapi** - Web dashboard
- **pyarrow** - Parquet export
- **scikit-learn** - ML features

## Installation Steps

### Method 1: From Repository

```bash
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner
pip install -r requirements.txt
python runner.py --version
```

### Method 2: Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### Method 3: PyPy3 (High Performance)

```bash
bash setup_pypy3_env.sh
source .venv-pypy3/bin/activate
pypy3 runner.py myscript.py
```

### Method 4: Docker

```bash
docker build -t psr .
docker run --rm psr myscript.py
```

## Verification

```bash
python runner.py --version
python runner.py --help
python runner.py test_script.py
```

## Troubleshooting

See [Troubleshooting Guide](troubleshooting.md) for common issues.
