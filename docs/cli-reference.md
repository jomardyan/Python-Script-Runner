# CLI Reference

> Complete command-line interface documentation

## Usage

```bash
python runner.py [SCRIPT] [OPTIONS]
```

## Common Options

### Basic Options
| Option | Description |
|--------|-------------|
| `--help` | Show help message |
| `--version` | Show version |
| `--config FILE` | Config file path |
| `--json-output FILE` | Output metrics as JSON |
| `--junit-output FILE` | Output as JUnit XML |

### Monitoring Options
| Option | Description |
|--------|-------------|
| `--history-db DB` | SQLite database path |
| `--detect-anomalies` | Detect anomalies |
| `--analyze-trend` | Analyze trends |
| `--detect-regression` | Detect regressions |

### Alert Options
| Option | Description |
|--------|-------------|
| `--alert-config RULE` | Add alert rule |
| `--slack-webhook URL` | Slack webhook URL |
| `--email-to ADDR` | Email recipient |

### Performance Gate Options
| Option | Description |
|--------|-------------|
| `--add-gate METRIC:VALUE` | Add performance gate |
| `--fail-on-gate-failure` | Exit with error on gate failure |

### Retry Options
| Option | Description |
|--------|-------------|
| `--retry-strategy STR` | Retry strategy (linear/exponential/fibonacci) |
| `--max-attempts N` | Maximum retry attempts |
| `--initial-delay SEC` | Initial delay in seconds |
| `--max-delay SEC` | Maximum delay in seconds |

## Examples

### Basic Execution
```bash
python runner.py myscript.py
```

### With Monitoring
```bash
python runner.py script.py \
    --history-db metrics.db \
    --detect-anomalies \
    --analyze-trend
```

### CI/CD with Performance Gates
```bash
python runner.py tests/suite.py \
    --add-gate cpu_max:90 \
    --add-gate memory_max_mb:1024 \
    --junit-output test-results.xml
```

### With Alerts
```bash
python runner.py script.py \
    --config config.yaml \
    --slack-webhook 'https://hooks.slack.com/...'
```

