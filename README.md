# Python Script Runner

<!-- Badges -->
<div align="center">

[![Python 3.6+](https://img.shields.io/badge/Python-3.6+-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge&logo=github)](LICENSE)
[![Release](https://img.shields.io/github/v/release/jomardyan/Python-Script-Runner?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jomardyan/Python-Script-Runner/releases)
[![Tests](https://img.shields.io/github/actions/workflow/status/jomardyan/Python-Script-Runner/tests.yml?label=Tests&style=for-the-badge&logo=github&logoColor=white)](https://github.com/jomardyan/Python-Script-Runner/actions)
[![Docker Ready](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/)
[![Status: Active](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)](https://github.com/jomardyan/Python-Script-Runner)

</div>

**Enterprise-grade Python script execution engine with real-time monitoring, alerting, analytics, and distributed execution.**

Transform script execution into a production-ready operation with comprehensive observability, intelligent alerting, CI/CD integration, and advanced analytics.

## Quick Links

📖 [Documentation](https://jomardyan.github.io/Python-Script-Runner/) | 🚀 [Quick Start](#quick-start) | 📊 [Features](#key-features) | 🔧 [Installation](#installation)

## Key Features

| Feature | Description |
|---------|-------------|
| **Real-Time Monitoring** | CPU, memory, I/O tracking with <2% overhead |
| **Multi-Channel Alerts** | Email, Slack, webhooks with threshold-based logic |
| **CI/CD Integration** | Performance gates, JUnit/TAP reporting, baseline comparison |
| **Historical Analytics** | SQLite backend with trend analysis & anomaly detection |
| **Retry Strategies** | Linear, exponential, Fibonacci backoff with smart filtering |
| **Advanced Profiling** | CPU/memory/I/O analysis with bottleneck identification |
| **Enterprise Ready** | Datadog, Prometheus, New Relic integrations |
| **Distributed Execution** | SSH, Docker, Kubernetes support |
| **Web Dashboard** | Real-time metrics visualization & RESTful API |
| **ML-Powered** | Anomaly detection, forecasting, correlation analysis |

## Installation

### Requirements

- **Python**: 3.6+ (3.8+ recommended)
- **OS**: Linux, macOS, Windows
- **Dependencies**: psutil (required), pyyaml, requests (optional)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner

# Install dependencies
pip install psutil pyyaml requests

# Verify installation
python runner.py --help
```

### From PyPI (Coming Soon)

```bash
pip install python-script-runner
```

### PyPy3 High-Performance Setup

For CPU-bound workloads, use PyPy3 for 2-5x faster execution:

```bash
./setup_pypy3_env.sh
source .venv-pypy3/bin/activate
```

See `requirements-pypy3.txt` for PyPy3 dependencies.

## Quick Start

### Basic Usage

```bash
# Simple script execution
python runner.py myscript.py

# With arguments
python runner.py train.py --epochs 100 --batch-size 32

# With monitoring and alerts
python runner.py myscript.py --alert-config "cpu_high:cpu_max>80" --slack-webhook "<webhook_url>"
```

### Common Scenarios

```bash
# CI/CD with performance gates
python runner.py tests/suite.py \
    --add-gate cpu_max:90 \
    --add-gate memory_max_mb:1024 \
    --junit-output results.xml

# Historical tracking and analysis
python runner.py myscript.py \
    --history-db metrics.db \
    --detect-anomalies \
    --analyze-trend

# Remote execution
python runner.py script.py \
    --ssh-host production.example.com \
    --ssh-user deploy \
    --ssh-key ~/.ssh/id_rsa
```

### Documentation

- 📚 [Full Documentation](https://jomardyan.github.io/Python-Script-Runner/)
- 🔧 [CLI Reference](https://jomardyan.github.io/Python-Script-Runner/cli-reference/)
- ⚙️ [Configuration Guide](https://jomardyan.github.io/Python-Script-Runner/configuration/)
- 🏗️ [Architecture](https://jomardyan.github.io/Python-Script-Runner/architecture/)

## Architecture

Real-time monitoring and analytics engine with enterprise integrations.

## API Reference

See [full documentation](https://jomardyan.github.io/Python-Script-Runner/api/) for complete API details.

## Collected Metrics

| Category | Metrics |
|----------|---------|
| **Timing** | start_time, end_time, execution_time_seconds |
| **CPU** | cpu_max, cpu_avg, cpu_min, user_time, system_time |
| **Memory** | memory_max_mb, memory_avg_mb, memory_min_mb, page_faults |
| **System** | num_threads, num_fds, context_switches, block_io |
| **Output** | stdout_lines, stderr_lines, exit_code, success |

## Performance

- **Monitoring Overhead**: <2% CPU/memory impact
- **Sampling Speed**: 10,000+ metrics/second
- **Query Performance**: Sub-second on 1-year data
- **Scalability**: Millions of records with SQLite

## Configuration

Create `config.yaml`:

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

retry:
  strategy: exponential
  max_attempts: 3
  initial_delay: 2
  max_delay: 60

database:
  path: "/var/lib/script-runner/metrics.db"
  retention_days: 90
```

## CI/CD Examples

### GitHub Actions

```yaml
- name: Run with performance gates
  run: |
    python runner.py tests/suite.py \
      --config config.yaml \
      --add-gate cpu_max:85 \
      --add-gate memory_max_mb:2048 \
      --junit-output test-results.xml
```

### Jenkins

```groovy
sh '''
  python runner.py tests/suite.py \
    --config config.yaml \
    --junit-output test-results.xml \
    --json-output metrics.json
'''
```

## Advanced Usage

```bash
# Trend analysis and anomaly detection
python runner.py script.py --history-db metrics.db --detect-anomalies --analyze-trend

# Remote SSH execution
python runner.py script.py --ssh-host prod.example.com --ssh-user deploy --ssh-key ~/.ssh/id_rsa

# Docker container execution
python runner.py script.py --docker-image python:3.11 --docker-env DATA_PATH=/data

# Enterprise integrations
python runner.py script.py --send-to-datadog metrics --datadog-api-key "$KEY"

# Performance forecasting
python runner.py script.py --history-db metrics.db --forecast-metric memory_max_mb --forecast-days 30
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| ImportError: psutil | `pip install psutil` |
| Config not loading | `pip install pyyaml` or use JSON |
| Slack alerts failing | Verify webhook URL, check network connectivity |
| Database locked | Ensure no other processes use the DB |

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push: `git push origin feature/name`
5. Open Pull Request

## License

MIT License - see [LICENSE](LICENSE)

## Support

- 📋 [Issues](https://github.com/jomardyan/Python-Script-Runner/issues)
- 💬 [Discussions](https://github.com/jomardyan/Python-Script-Runner/discussions)

---

**Version**: 3.0.0 | **Status**: Production Ready | **Last Updated**: November 2024
