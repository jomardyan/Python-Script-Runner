# Usage Guide

> Common usage scenarios and best practices

## Basic Usage

```bash
python runner.py myscript.py
```

## With Arguments

```bash
python runner.py train.py --epochs 100 --batch-size 32
```

## Continuous Monitoring

```bash
python runner.py script.py \
    --history-db metrics.db \
    --detect-anomalies \
    --analyze-trend
```

## CI/CD Integration

```bash
python runner.py tests/suite.py \
    --add-gate cpu_max:90 \
    --add-gate memory_max_mb:1024 \
    --junit-output results.xml
```

## Remote Execution

```bash
python runner.py script.py \
    --ssh-host prod.example.com \
    --ssh-user deploy \
    --ssh-key ~/.ssh/id_rsa
```

