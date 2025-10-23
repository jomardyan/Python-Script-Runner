# GitHub Action: Python Script Runner

This GitHub Action provides zero-configuration integration for Python Script Runner into CI/CD pipelines.

## Features

- **Zero Configuration**: Works out of the box with sensible defaults
- **Production Features**: Built-in support for retries, timeouts, and monitoring
- **Security Scanning**: Optional pre-execution security and dependency scanning
- **Distributed Tracing**: Optional OpenTelemetry integration
- **Cost Attribution**: Cloud resource cost tracking (AWS, Azure, GCP)
- **Metrics Export**: Built-in metrics upload capability

## Usage

### Basic Example

```yaml
name: Run Python Script
on: [push]

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: jomardyan/python-script-runner@v1
        with:
          script-path: './scripts/my_script.py'
```

### With Retries and Timeout

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/etl_pipeline.py'
    python-version: '3.11'
    timeout-minutes: 60
    max-retries: 3
    retry-delay-seconds: 10
```

### With Security Scanning

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/api_integration.py'
    enable-security-scan: true
    enable-dependency-scan: true
    fail-fast: true  # Block execution if vulnerabilities found
```

### With OpenTelemetry Tracing

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/background_job.py'
    enable-tracing: true
    extra-dependencies: 'opentelemetry-api opentelemetry-sdk'
  env:
    OTEL_EXPORTER_OTLP_ENDPOINT: https://your-collector.example.com:4317
```

### With Metrics Upload

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/benchmark.py'
    upload-metrics: https://metrics.example.com/api/metrics
```

### With Cloud Cost Tracking

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/data_processing.py'
    enable-cost-tracking: true
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    AWS_REGION: us-east-1
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `script-path` | Path to Python script | **Required** |
| `python-version` | Python version (3.9, 3.10, 3.11) | 3.11 |
| `timeout-minutes` | Execution timeout | 30 |
| `max-retries` | Retry attempts | 0 |
| `retry-delay-seconds` | Delay between retries | 5 |
| `fail-fast` | Exit on first error | false |
| `extra-dependencies` | Additional pip packages | "" |
| `enable-tracing` | Enable OpenTelemetry | false |
| `enable-security-scan` | Enable security scanning | false |
| `enable-dependency-scan` | Enable CVE scanning | false |
| `enable-cost-tracking` | Enable cost attribution | false |
| `upload-metrics` | Metrics endpoint URL | "" |

## Outputs

| Output | Description |
|--------|-------------|
| `exit-code` | Script exit code (0 = success) |
| `execution-time-seconds` | Total execution duration |
| `metrics` | JSON-formatted execution metrics |

## Real-World Examples

### Example 1: Scheduled ETL Pipeline

```yaml
name: Daily ETL Pipeline
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM daily

jobs:
  etl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: jomardyan/python-script-runner@v1
        with:
          script-path: './etl/daily_pipeline.py'
          python-version: '3.11'
          timeout-minutes: 120
          max-retries: 2
          enable-dependency-scan: true
```

### Example 2: CI/CD Performance Gate

```yaml
name: Performance Tests
on: [pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: jomardyan/python-script-runner@v1
        with:
          script-path: './tests/performance_benchmark.py'
          fail-fast: true
          upload-metrics: https://benchmarks.example.com/api
```

### Example 3: Distributed Tracing

```yaml
name: Trace Integration
on: [push]

jobs:
  trace:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: jomardyan/python-script-runner@v1
        with:
          script-path: './services/distributed_job.py'
          enable-tracing: true
        env:
          OTEL_EXPORTER_OTLP_ENDPOINT: ${{ secrets.OTEL_COLLECTOR_URL }}
```

## Error Handling

The action will fail the job if:
- Script exits with non-zero code (unless retried successfully)
- Security scan finds critical vulnerabilities (with `fail-fast: true`)
- Dependency scan finds critical CVEs
- Timeout is exceeded

## Troubleshooting

### Script Not Found
Ensure the script path is relative to the workspace root and the repository is checked out first:
```yaml
- uses: actions/checkout@v3
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/my_script.py'
```

### Permission Denied
Make sure the script has execute permissions:
```bash
git update-index --chmod=+x scripts/my_script.py
```

### Dependency Not Found
Use `extra-dependencies` to install required packages:
```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/my_script.py'
    extra-dependencies: 'pandas numpy scipy'
```

## Integration with Python Script Runner Features

All Python Script Runner v7.0+ features are available through environment variables:

- **Retries**: `PSR_MAX_RETRIES`, `PSR_RETRY_DELAY_SECONDS`
- **Monitoring**: `PSR_ENABLE_TRACING`, `PSR_ENABLE_COST_TRACKING`
- **Alerts**: `PSR_ALERT_CONFIG` (path to alert config)
- **Metrics**: `PSR_METRICS_DB` (path to metrics database)

## Support

For issues, feature requests, or questions, please visit:
- GitHub Issues: https://github.com/jomardyan/Python-Script-Runner/issues
- Documentation: https://github.com/jomardyan/Python-Script-Runner

## License

MIT - See LICENSE file in main repository
