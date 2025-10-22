# CLI Reference

## Execution Options

| Option | Type | Description |
|--------|------|-------------|
| `--timeout` | int | Execution timeout in seconds |
| `--log-level` | choice | DEBUG, INFO, WARNING, ERROR |
| `--suppress-warnings` | flag | Suppress warning messages |

## Monitoring & Alerts

| Option | Description |
|--------|-------------|
| `--config` | YAML configuration file |
| `--monitor-interval` | Sampling interval (default: 0.1) |
| `--alert-config` | Alert condition (e.g., "high_cpu:cpu_max>80") |
| `--slack-webhook` | Slack webhook URL |
| `--email-config` | Email config JSON file |

## CI/CD Integration

| Option | Description |
|--------|-------------|
| `--add-gate` | Performance gate (e.g., "cpu_max:90") |
| `--junit-output` | Generate JUnit XML report |
| `--tap-output` | Generate TAP format report |
| `--baseline` | Load baseline metrics JSON |
| `--save-baseline` | Save metrics as baseline |
| `--json-output` | Export metrics as JSON |

## History & Database

| Option | Description |
|--------|-------------|
| `--history-db` | SQLite database file |
| `--show-history` | Display execution history |
| `--history-days` | Days of history to show (default: 30) |
| `--history-limit` | Max records (default: 50) |
| `--db-stats` | Show database statistics |
| `--cleanup-old` | Delete records older than N days |

## Retry Options

| Option | Description |
|--------|-------------|
| `--retry` | Number of retry attempts |
| `--retry-strategy` | linear, exponential, fibonacci, exponential_jitter |
| `--retry-delay` | Initial delay (seconds) |
| `--retry-max-delay` | Maximum delay (seconds) |
| `--retry-multiplier` | Exponential multiplier (default: 2.0) |

## Trend Analysis

| Option | Description |
|--------|-------------|
| `--analyze-trend` | Analyze trends and exit |
| `--trend-metric` | Metric to analyze |
| `--trend-days` | Days to analyze (default: 30) |
| `--detect-regression` | Detect regressions |
| `--detect-anomalies` | Detect anomalies |
| `--anomaly-method` | iqr, zscore, mad |

## Advanced Features

| Option | Description |
|--------|-------------|
| `--send-to-datadog` | Send metrics to Datadog |
| `--send-to-prometheus` | Send to Prometheus |
| `--send-to-newrelic` | Send to New Relic |
| `--forecast-metric` | Forecast metric values |
| `--analyze-correlations` | Analyze metric correlations |
| `--profile-cpu-memory` | Profile CPU/memory usage |

See README.md for complete CLI reference.
