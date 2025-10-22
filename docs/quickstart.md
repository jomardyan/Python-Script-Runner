# Quick Start

## Basic Execution

```bash
python runner.py myscript.py
python runner.py train.py --epochs 100 --batch-size 32
python runner.py process_data.py --timeout 300
```

## With Monitoring & Alerts

```bash
python runner.py myscript.py \
    --alert-config "cpu_high:cpu_max>80" \
    --slack-webhook "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## With CI/CD Integration

```bash
python runner.py tests/suite.py \
    --add-gate cpu_max:90 \
    --add-gate memory_max_mb:1024 \
    --junit-output results.xml \
    --json-output metrics.json
```

## With History & Analytics

```bash
# Run with history storage
python runner.py myscript.py --history-db metrics.db

# View execution history
python runner.py --show-history --history-limit 20

# Analyze trends
python runner.py --analyze-trend --trend-metric cpu_max --trend-days 30
```

## With Retry Strategy

```bash
python runner.py flaky_test.py \
    --retry 3 \
    --retry-strategy exponential \
    --retry-delay 2 \
    --retry-max-delay 30
```

## Next Steps

- [Usage Guide](usage.md) for detailed patterns
- [Configuration](configuration.md) for advanced setup
- [CLI Reference](cli-reference.md) for all options
