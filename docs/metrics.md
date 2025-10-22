# Metrics Reference

> Complete guide to all metrics collected by Python Script Runner

## Overview

Python Script Runner automatically collects 30 different metrics during script execution.
All metrics are stored in SQLite database and available for analysis and alerting.

## Timing Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `start_time` | float/int | Start Time |
| `end_time` | float/int | End Time |
| `execution_time` | float/int | Execution Time |

## CPU Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `cpu_max` | float/int | Cpu Max |
| `cpu_avg` | float/int | Cpu Avg |
| `cpu_min` | float/int | Cpu Min |
| `user_time` | float/int | User Time |
| `system_time` | float/int | System Time |

## Memory Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `memory_max` | float/int | Memory Max |
| `memory_avg` | float/int | Memory Avg |
| `memory_min` | float/int | Memory Min |
| `page_faults` | float/int | Page Faults |

## System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `num_threads` | float/int | Num Threads |
| `num_fds` | float/int | Num Fds |
| `context_switches` | float/int | Context Switches |
| `block_io` | float/int | Block Io |

## Output Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `stdout_lines` | float/int | Stdout Lines |
| `stderr_lines` | float/int | Stderr Lines |
| `exit_code` | float/int | Exit Code |
| `success` | float/int | Success |

## Querying Metrics

### Via HistoryManager

```python
from runner import HistoryManager

manager = HistoryManager('metrics.db')
history = manager.get_execution_history('script.py', days=30)
metrics = manager.get_aggregated_metrics('script.py')
```

### Via TimeSeriesDB

```python
from runner import TimeSeriesDB, HistoryManager

history_manager = HistoryManager('metrics.db')
ts_db = TimeSeriesDB(history_manager)
results = ts_db.query(
    metric_name='cpu_max',
    script_path='script.py',
    days=30
)
```

## Metric Aggregation

```python
aggs = ts_db.aggregations(
    metric_name='execution_time_seconds',
    script_path='script.py'
)
# Returns: min, max, avg, median, p50, p75, p90, p95, p99, stddev
```

