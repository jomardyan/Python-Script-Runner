# Python Script Runner

> **Enterprise-grade Python script execution engine** with real-time monitoring, alerting, analytics, and distributed execution.

[![Python 3.6+](https://img.shields.io/badge/Python-3.6+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square&logo=github)](LICENSE)
[![PyPI Version](https://img.shields.io/pypi/v/python-script-runner?style=flat-square&logo=pypi&logoColor=white)](https://pypi.org/project/python-script-runner/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/python-script-runner?style=flat-square&logo=pypi)](https://pypi.org/project/python-script-runner/)
[![Tests](https://img.shields.io/github/actions/workflow/status/jomardyan/Python-Script-Runner/tests.yml?label=Tests&style=flat-square&logo=github&logoColor=white)](https://github.com/jomardyan/Python-Script-Runner/actions)
[![GitHub Packages](https://img.shields.io/badge/GitHub_Packages-📦-blue?style=flat-square)](https://github.com/jomardyan/Python-Script-Runner/packages)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)](https://github.com/jomardyan/Python-Script-Runner)

Transform script execution into a production-ready operation with comprehensive observability, intelligent alerting, CI/CD integration, and advanced analytics.

---

## 🎯 Who Is This For?

Python Script Runner is designed for **developers, data engineers, DevOps teams, and organizations** who need production-grade execution monitoring for Python scripts. Whether you're running scripts locally, in CI/CD pipelines, or on production servers, this tool provides enterprise-level observability without the complexity.

### Perfect For:

- **🔬 Data Scientists & ML Engineers** - Monitor training scripts, data pipelines, and model inference
- **⚙️ DevOps & Platform Engineers** - Track maintenance scripts, automation tasks, and deployment jobs
- **🏢 Enterprise Teams** - Ensure compliance, SLA monitoring, and performance tracking
- **🚀 Startup/Scale-Up Teams** - Production-ready monitoring without expensive APM tools
- **🧪 QA & Test Engineers** - Performance regression testing and CI/CD integration
- **📊 Data Engineers** - ETL pipeline monitoring and data quality checks

---

## 💼 Real-World Use Cases

### 1. **Data Pipeline Monitoring**
```bash
# Monitor nightly ETL job with alerting
python -m runner etl_pipeline.py \
  --history-db /var/log/etl-metrics.db \
  --alert-config "runtime_sla:execution_time_seconds>3600" \
  --slack-webhook "$SLACK_WEBHOOK" \
  --email-to data-team@company.com
```
**Benefit**: Catch performance degradation before it impacts downstream systems. Historical trends show when pipelines are slowing down.

### 2. **ML Model Training with Performance Gates**
```bash
# Ensure training stays within resource limits
python -m runner train_model.py \
  --add-gate memory_max_mb:8192 \
  --add-gate cpu_max:90 \
  --timeout 7200 \
  --retry-strategy exponential
```
**Benefit**: Prevent runaway training jobs from consuming cluster resources. Auto-retry with exponential backoff on transient failures.

### 3. **CI/CD Performance Regression Testing**
```yaml
# GitHub Actions workflow
- name: Run tests with performance benchmarks
  run: |
    python -m runner tests/integration_suite.py \
      --junit-output test-results.xml \
      --baseline-db baseline-metrics.db \
      --add-gate execution_time_seconds:60
```
**Benefit**: Block deployments if performance degrades beyond baseline. JUnit output integrates with CI/CD dashboards.

### 4. **Production Maintenance Scripts**
```python
from runner import ScriptRunner

# Database backup script with monitoring
runner = ScriptRunner("backup_database.py")

# Configure alerts via config file or add programmatically
# For config file approach, see config.example.yaml
result = runner.run_script()

if not result['metrics']['success']:
    # Handle failure, send alerts, etc.
    print(f"Backup failed with exit code: {result['exit_code']}")
```
**Benefit**: Immediate alerts when critical scripts fail. Historical metrics show backup duration trends.

### 5. **Distributed Task Execution**
```bash
# Run data processing on remote server
python -m runner process_data.py \
  --ssh-host worker-node-01.prod \
  --ssh-user deploy \
  --ssh-key ~/.ssh/prod-key \
  --json-output results.json
```
**Benefit**: Monitor remote script execution with local observability. Perfect for distributed data processing.

### 6. **API Integration Testing**
```bash
# Load test API endpoints with retry logic
python -m runner api_load_test.py \
  --max-retries 3 \
  --retry-strategy fibonacci \
  --detect-anomalies \
  --history-db load-test-history.db
```
**Benefit**: ML-powered anomaly detection identifies unusual response times. Retry logic handles transient network failures.

### 7. **Scheduled Reporting Jobs**
```bash
# Daily report generation with SLA monitoring
0 9 * * * python -m runner generate_daily_report.py \
  --alert-config "slow_report:execution_time_seconds>600" \
  --email-to executives@company.com \
  --attach-metrics
```
**Benefit**: Ensures reports are generated on time. Email includes performance metrics alongside business reports.

### 8. **Kubernetes CronJob Monitoring**
```yaml
# K8s CronJob with integrated monitoring
spec:
  containers:
  - name: data-processor
    command: 
    - python
    - -m
    - runner
    - process_data.py
    - --prometheus-pushgateway
    - http://prometheus:9091
    - --add-gate
    - memory_max_mb:2048
```
**Benefit**: Push metrics to Prometheus without changing application code. Resource gates prevent pod OOM kills.

### 9. **Multi-Environment Testing**
```bash
# Run same script across dev/staging/prod with different configs
for env in dev staging prod; do
  python -m runner smoke_test.py \
    --config configs/$env.yaml \
    --history-db metrics-$env.db \
    --tag environment=$env
done
```
**Benefit**: Compare performance across environments. Identify environment-specific bottlenecks.

### 10. **Compliance & Audit Logging**
```python
from runner import ScriptRunner

runner = ScriptRunner(
    "process_pii_data.py",
    history_db="audit-trail.db"
)
result = runner.run_script()

# Immutable audit trail with full execution metrics
print(f"Execution ID: {result.get('execution_id', 'N/A')}")
print(f"Start Time: {result['metrics']['start_time']}")
print(f"Exit Code: {result['exit_code']}")
print(f"Success: {result['metrics']['success']}")
```
**Benefit**: SQLite database provides immutable audit trail for SOC2/HIPAA compliance. Every execution logged with full context.

---

## 🚀 Quick Start

### Install via pip (Recommended)

```bash
pip install python-script-runner
```

### Basic Usage

```bash
# Simple execution - automatically shows detailed metrics
python -m runner myscript.py

# With performance monitoring
python -m runner script.py --history-db metrics.db

# With alerts
python -m runner script.py --slack-webhook "YOUR_WEBHOOK_URL"

# As CLI command
python-script-runner myscript.py
```

### 📊 Default Output - Comprehensive Metrics Report

Every run automatically displays a detailed metrics report with:

- **📋 Script Information** - path, execution status, exit code
- **⏱️ Execution Timing** - start time, end time, total duration, CPU user/system time
- **💻 CPU Metrics** - maximum, average, and minimum CPU usage, context switches
- **🧠 Memory Metrics** - peak memory, average usage, minimum baseline, page faults
- **⚙️ System Metrics** - active threads, file descriptors, block I/O operations
- **📤 Output Metrics** - stdout and stderr line counts

No configuration needed - just run and get full observability by default!

### Python Code

```python
from runner import ScriptRunner

runner = ScriptRunner("myscript.py")
result = runner.run_script()

print(f"Exit Code: {result['exit_code']}")
print(f"Execution Time: {result['metrics']['execution_time_seconds']}s")
print(f"Max CPU: {result['metrics']['cpu_max']}%")
print(f"Max Memory: {result['metrics']['memory_max_mb']}MB")
```

---

## 📚 Using as a Python Library

Python Script Runner is designed to be used as both a CLI tool and as a Python library in your own code.

### Basic Library Import

```python
from runner import ScriptRunner, HistoryManager, AlertManager

# Execute a script and get metrics
runner = ScriptRunner("data_processing.py")
result = runner.run_script()

print(f"Success: {result['metrics']['success']}")
print(f"Duration: {result['metrics']['execution_time_seconds']}s")
```

### Advanced Library Usage

```python
from runner import ScriptRunner, AlertManager

# Create a runner with configuration
runner = ScriptRunner(
    script_path="ml_training.py",
    timeout_seconds=3600
)

# Configure retry behavior
runner.retry_config = {
    'strategy': 'exponential',
    'max_attempts': 3,
    'base_delay': 1.0
}

# Configure alerts
runner.alert_manager.configure_slack("https://hooks.slack.com/...")
runner.alert_manager.add_alert(
    name="high_memory",
    condition="memory_max_mb > 2048",
    severity="WARNING"
)

# Execute with retry
result = runner.run_script(retry_on_failure=True)
metrics = result['metrics']

if not metrics['success']:
    print(f"Script failed after {metrics.get('attempt_number', 1)} attempts")
else:
    print(f"✅ Completed in {metrics['execution_time_seconds']:.2f}s")
```

### Access Historical Data

```python
from runner import HistoryManager

# Query historical metrics
history = HistoryManager("metrics.db")
stats = history.get_aggregated_metrics("cpu_max", days=7)

print(f"Last 7 days CPU max average: {stats['avg']:.1f}%")
print(f"Peak CPU: {stats['max']:.1f}%")
```

### CI/CD Integration

```python
from runner import ScriptRunner, CICDIntegration

runner = ScriptRunner("tests/suite.py")
runner.cicd_integration.add_performance_gate("cpu_max", max_value=90)
runner.cicd_integration.add_performance_gate("memory_max_mb", max_value=1024)

result = runner.run_script()
gates_passed, gate_results = runner.cicd_integration.check_gates(result['metrics'])

if not gates_passed:
    print("Performance gates failed:")
    for gate_result in gate_results:
        print(f"  ❌ {gate_result}")
    exit(1)
else:
    print("✅ All performance gates passed!")
```

### Available Classes for Import

All of these can be imported directly:

```python
from runner import (
    ScriptRunner,            # Main class for running scripts
    HistoryManager,          # SQLite-based metrics history
    AlertManager,            # Email/Slack/webhook alerting
    CICDIntegration,         # Performance gates and CI/CD reporting
    PerformanceAnalyzer,     # Statistical analysis and trending
    AdvancedProfiler,        # CPU/Memory/I/O profiling
    EnterpriseIntegration,   # Datadog/Prometheus/New Relic
)
```

---

## ✨ Key Features

- **🔍 Real-Time Monitoring** - CPU, memory, I/O tracking with <2% overhead
- **🔔 Multi-Channel Alerts** - Email, Slack, webhooks with threshold-based logic
- **🚀 CI/CD Integration** - Performance gates, JUnit/TAP reporting, baseline comparison
- **📊 Historical Analytics** - SQLite backend with trend analysis & anomaly detection
- **🔄 Retry Strategies** - Linear, exponential, Fibonacci backoff with smart filtering
- **🎯 Advanced Profiling** - CPU/memory/I/O analysis with bottleneck identification
- **🏢 Enterprise Ready** - Datadog, Prometheus, New Relic integrations
- **🌐 Distributed Execution** - SSH, Docker, Kubernetes support
- **📈 Web Dashboard** - Real-time metrics visualization & RESTful API
- **🤖 ML-Powered** - Anomaly detection, forecasting, correlation analysis

---

## 📦 Installation

### Requirements

- **Python**: 3.6+ (3.8+ recommended)
- **OS**: Linux, macOS, Windows
- **Core Dependency**: psutil

### Install from PyPI

```bash
pip install python-script-runner
```

This is the recommended way to install and use the package globally.

### Install with Optional Features

```bash
# Dashboard with FastAPI
pip install python-script-runner[dashboard]

# Data export and ML features
pip install python-script-runner[export]

# Development and documentation
pip install python-script-runner[dev,docs]

# All features
pip install python-script-runner[dashboard,export,dev,docs]
```

### From Source (Development)

```bash
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner
pip install -e .
```

### 🔧 Quick Setup Scripts (Development)

For developers working from source, we provide cross-platform setup scripts:

#### **Bash (Linux/macOS)**
```bash
# Interactive setup with virtual environment
source ./setup.sh

# Features:
# - Auto-detects Python 3.6+
# - Creates/activates virtual environment
# - Installs all dependencies
# - Multiple setup modes (develop/install/build)
```

#### **PowerShell (Windows/macOS/Linux)**
```powershell
# Cross-platform interactive setup
.\setup.ps1

# Features:
# - Works on Windows, macOS, and Linux
# - Smart Python detection (python3/python/py)
# - Handles execution policies automatically
# - Supports py2exe for Windows executables
```

#### **Interactive Config Builder**
```bash
# Generate config.yaml interactively
.\build-config.ps1   # PowerShell (all platforms)

# Wizard-based configuration for:
# - Alert rules (CPU, memory, time thresholds)
# - Performance gates (CI/CD limits)
# - Notifications (Slack, email, webhooks)
# - Database settings (metrics storage)
# - Retry strategies (exponential, fibonacci)
```

**When to use:**
- `setup.sh` / `setup.ps1`: First-time development environment setup
- `build-config.ps1`: Creating custom monitoring configurations

### Pre-Compiled Executables

**No Python installation required!** Download pre-built standalone executables:

#### 🪟 Windows (Standalone EXE)

```bash
# Download from GitHub Releases: python-script-runner-X.Y.Z-windows.zip
unzip python-script-runner-X.Y.Z-windows.zip
cd python-script-runner-X.Y.Z
python-script-runner.exe script.py
```

**Features:**

- No Python required - completely standalone
- Windows 7 SP1 or later
- ~70 MB size

#### 🐧 Linux/Ubuntu/Debian (DEB Package)

```bash
# Download from GitHub Releases: python-script-runner_X.Y.Z_all.deb
sudo apt install ./python-script-runner_X.Y.Z_all.deb
python-script-runner script.py
```

**Features:**

- System package integration
- Automatic updates via `apt upgrade`
- Installs to `/usr/bin/python-script-runner`
- ~10 MB size

#### 📖 Full Executable Guide

See **[INSTALL_EXECUTABLES.md](INSTALL_EXECUTABLES.md)** for:

- Detailed Windows EXE setup and troubleshooting
- Linux DEB installation and system integration
- System requirements and verification steps
- Common use cases and configuration
- FAQ and pro tips

---

## 💡 Usage Examples

### 1. Simple Script Execution with Detailed Metrics

```bash
python -m runner myscript.py
```

**Output includes:**

- ✅ Script status (success/failure)
- ⏱️ Execution timing (start, end, total duration)
- 💻 CPU metrics (max, avg, min %)
- 🧠 Memory metrics (max, avg, min MB)
- ⚙️ System metrics (threads, file descriptors, I/O)
- 📤 Output metrics (stdout/stderr lines)

**Example output:**

```text
================================================================================
EXECUTION METRICS REPORT
================================================================================

📋 SCRIPT INFORMATION
────────────────────────────────────────────────────────────────────────────────
  Script Path: myscript.py
  Status: ✅ SUCCESS
  Exit Code: 0

⏱️  EXECUTION TIMING
────────────────────────────────────────────────────────────────────────────────
  Start Time: 2025-10-22 14:30:45.123456
  End Time: 2025-10-22 14:30:50.456789
  Total Duration: 5.3333s
  User Time: 4.2100s
  System Time: 0.8900s

💻 CPU METRICS
────────────────────────────────────────────────────────────────────────────────
  Max CPU: 45.2%
  Avg CPU: 28.1%
  Min CPU: 2.3%
  Context Switches: 1245

🧠 MEMORY METRICS
────────────────────────────────────────────────────────────────────────────────
  Max Memory: 256.4 MB
  Avg Memory: 189.2 MB
  Min Memory: 45.1 MB
  Page Faults: 3421

⚙️  SYSTEM METRICS
────────────────────────────────────────────────────────────────────────────────
  Process Threads: 4
  Open File Descriptors: 12
  Block I/O Operations: 1024

📤 OUTPUT METRICS
────────────────────────────────────────────────────────────────────────────────
  Stdout Lines: 1523
  Stderr Lines: 0

================================================================================
```

### 2. Pass Arguments

```bash
python -m runner train.py --epochs 100 --batch-size 32
```

### 3. Performance Monitoring & Gates (CI/CD)

```bash
python -m runner tests/suite.py \
  --add-gate cpu_max:90 \
  --add-gate memory_max_mb:1024 \
  --junit-output test-results.xml
```

### 4. Historical Tracking & Trend Analysis

```bash
python -m runner myscript.py \
  --history-db metrics.db \
  --detect-anomalies \
  --analyze-trend
```

### 5. Slack Alerts

```bash
python -m runner myscript.py \
  --alert-config "cpu_high:cpu_max>80" \
  --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK"
```

### 6. Remote SSH Execution

```bash
python -m runner script.py \
  --ssh-host production.example.com \
  --ssh-user deploy \
  --ssh-key ~/.ssh/id_rsa
```

### 7. JSON & JUnit Output

```bash
python -m runner script.py \
  --json-output metrics.json \
  --junit-output results.xml
```

---

## ⚙️ Configuration

Create `config.yaml` for advanced setup:

```yaml
alerts:
  - name: cpu_high
    condition: cpu_max > 85
    channels: [slack, email]
    severity: WARNING

performance_gates:
  - metric_name: cpu_max
    max_value: 90
  - metric_name: memory_max_mb
    max_value: 1024

notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK"
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    from: "alerts@company.com"
    to: ["team@company.com"]
    use_tls: true

database:
  path: "/var/lib/script-runner/metrics.db"
  retention_days: 90
```

Use it:

```bash
python -m runner script.py --config config.yaml
```

---

## 📊 Performance Characteristics

| Metric | Value |
|--------|-------|
| Monitoring Overhead | <2% CPU/memory |
| Sampling Speed | 10,000+ metrics/second |
| Query Performance | Sub-second on 1-year data |
| Scalability | Millions of records with SQLite |

---

## 📈 Collected Metrics

| Category | Metrics |
|----------|---------|
| **Timing** | start_time, end_time, execution_time_seconds |
| **CPU** | cpu_max, cpu_avg, cpu_min, user_time, system_time |
| **Memory** | memory_max_mb, memory_avg_mb, memory_min_mb, page_faults |
| **System** | num_threads, num_fds, context_switches, block_io |
| **Output** | stdout_lines, stderr_lines, exit_code, success |

---

## 🔄 CI/CD Integration

### GitHub Actions

```yaml
- name: Run tests with performance gates
  run: |
    pip install python-script-runner
    python -m runner tests/suite.py \
      --add-gate cpu_max:85 \
      --add-gate memory_max_mb:2048 \
      --junit-output test-results.xml
```

### Jenkins

```groovy
sh '''
  pip install python-script-runner
  python -m runner tests/suite.py \
    --junit-output test-results.xml \
    --json-output metrics.json
'''
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: psutil` | `pip install psutil` |
| `YAML config not loading` | `pip install pyyaml` |
| `Module not found after pip install` | `pip install --upgrade python-script-runner` |
| `Slack alerts not working` | Verify webhook URL and network access |
| `Database locked error` | Ensure no other processes are using the DB |

For more help: `python -m runner --help`

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Submit a Pull Request

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🔗 Links & Resources

| Resource | Link |
|----------|------|
| **PyPI Package** | [python-script-runner](https://pypi.org/project/python-script-runner/) |
| **GitHub Repository** | [Python-Script-Runner](https://github.com/jomardyan/Python-Script-Runner) |
| **Report Issues** | [GitHub Issues](https://github.com/jomardyan/Python-Script-Runner/issues) |
| **Discussions** | [GitHub Discussions](https://github.com/jomardyan/Python-Script-Runner/discussions) |

---

## 📋 Project Status

- **Latest Version**: 6.4.3
- **Status**: Production Ready ✅
- **Python Support**: 3.6 - 3.11 (CPython & PyPy)
- **License**: MIT
- **Last Updated**: October 2025

---

## 🎯 Getting Started Now

```bash
# 1. Install
pip install python-script-runner

# 2. Run your first script
python -m runner myscript.py

# 3. View metrics
cat metrics.json  # if you used --json-output
```

---

Made with ❤️ by Hayk Jomardyan

[**Install Now**](https://pypi.org/project/python-script-runner/) • [**GitHub**](https://github.com/jomardyan/Python-Script-Runner) • [**Report Issue**](https://github.com/jomardyan/Python-Script-Runner/issues)
