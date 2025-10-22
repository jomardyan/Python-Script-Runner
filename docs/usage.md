# Usage Guide

## Basic Monitoring

```bash
python runner.py data_pipeline.py --timeout 600
```

Monitors CPU, memory, I/O with real-time output.

## Email Alerts on Failure

```bash
python runner.py critical_job.py \
    --email-config email_config.json \
    --alert-config "job_failure:exit_code!=0"
```

## CI/CD with Performance Gates

```bash
python runner.py performance_test.py \
    --add-gate cpu_max:85 \
    --add-gate memory_max_mb:2048 \
    --baseline baseline.json \
    --save-baseline new_baseline.json \
    --junit-output junit.xml \
    --tap-output results.tap \
    --json-output metrics.json
```

## Trend Analysis & Regression Detection

```bash
python runner.py train.py \
    --history-db history.db \
    --detect-regression \
    --regression-threshold 15 \
    --trend-metric execution_time_seconds
```

## Full Production Pipeline

```bash
python runner.py production_job.py \
    --config config.yaml \
    --history-db metrics.db \
    --retry 2 \
    --retry-strategy exponential \
    --detect-anomalies \
    --anomaly-method iqr \
    --send-to-datadog metrics \
    --datadog-api-key "$DATADOG_API_KEY" \
    --junit-output results.xml \
    --json-output metrics.json
```

## Remote Execution

```bash
# SSH
python runner.py my_script.py \
    --ssh-host prod-server.example.com \
    --ssh-user deploy \
    --ssh-key ~/.ssh/id_rsa

# Docker
python runner.py analysis.py \
    --docker-image python:3.11 \
    --docker-env PYTHONUNBUFFERED=1

# Kubernetes
python runner.py ml_training.py \
    --k8s-namespace data-pipelines \
    --k8s-job-name ml-training-job \
    --k8s-image python:3.11-slim
```

## Performance Analysis

```bash
python runner.py long_running_job.py \
    --history-db history.db \
    --analyze-optimization \
    --optimization-days 30 \
    --optimization-report

python runner.py compute_heavy.py \
    --profile-cpu-memory \
    --profile-duration 60
```

## Forecasting

```bash
python runner.py analytics.py \
    --history-db metrics.db \
    --forecast-metric memory_max_mb \
    --forecast-days 14 \
    --predict-sla cpu_max \
    --sla-threshold 85
```
