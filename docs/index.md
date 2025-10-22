# Python Script Runner

**Production-grade Python script execution engine with comprehensive monitoring, alerting, analytics, and enterprise integrations.**

## Overview

Python Script Runner is an enterprise-ready execution framework for production environments where monitoring, reliability, and observability are critical.

### Key Capabilities

- **Real-time Monitoring**: CPU, memory, I/O tracking with < 2% overhead
- **Intelligent Alerting**: Multi-channel notifications (Email, Slack, Webhooks)
- **CI/CD Integration**: Performance gates, JUnit/TAP reporting, baseline comparisons
- **Historical Analytics**: SQLite-backed metrics storage, trend analysis, anomaly detection
- **Advanced Retry**: Linear, exponential, Fibonacci backoff strategies
- **Performance Optimization**: ML-based anomaly detection, resource forecasting
- **Enterprise Ready**: Datadog, Prometheus, New Relic integrations, SSH/Docker/K8s execution

## Getting Started

```bash
# Clone and install
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner
pip install psutil pyyaml requests

# Run a script
python runner.py myscript.py --timeout 300
```

## Documentation

- [Installation](installation.md) - Setup and dependencies
- [Quick Start](quickstart.md) - Basic examples
- [Usage Guide](usage.md) - Detailed usage patterns
- [CLI Reference](cli-reference.md) - All command-line options
- [Configuration](configuration.md) - YAML and JSON setup
- [CI/CD Integration](cicd.md) - GitHub Actions, Jenkins, GitLab
- [API Documentation](api.md) - Python API usage
- [Metrics](metrics.md) - Collected metrics and formats
- [Architecture](architecture.md) - System design overview
- [Advanced Features](advanced.md) - Phase 3 capabilities
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Features Overview

### Phase 1: Monitoring & Alerting
Real-time process monitoring, multi-channel alerting, CI/CD integration with performance gates.

### Phase 2: Historical Analytics
SQLite persistence, trend detection, anomaly detection, advanced retry, data export, retention policies.

### Phase 3: Enterprise Features
ML-based optimization, metrics correlation, benchmarking, enterprise integrations, distributed execution, task scheduling.

## License

MIT License - See LICENSE file for details
