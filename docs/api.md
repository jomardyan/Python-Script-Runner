# API Reference

> Complete Python API documentation for Python Script Runner

## Overview

Python Script Runner provides a comprehensive Python API with 32 main classes.

## Core Classes

### AdvancedProfiler

Advanced CPU/memory/I/O profiling with call stack and system call tracing.

**Methods:**

- `profile_cpu_and_memory()` - Profile CPU and memory usage with high-frequency sampling
- `io_profile()` - Profile I/O operations (disk reads/writes)
- `get_profile_summary()` - Get summary of profiling results

### Alert

Represents an alert configuration

**Methods:**

- `should_trigger()` - Evaluate if alert should trigger based on metrics
- `can_trigger()` - Check if alert is not throttled
- `mark_triggered()` - Mark alert as triggered

### AlertChannel

Available alert channels

### AlertIntelligence

Intelligent alert management with auto-tuning, deduplication, and context-aware routing.

**Methods:**

- `deduplicate_alerts()` - Remove duplicate alerts within a time window
- `calculate_adaptive_threshold()` - Calculate adaptive thresholds based on metric history
- `analyze_alert_patterns()` - Analyze alert patterns to identify recurring issues
- `suggest_alert_routing()` - Suggest intelligent routing for an alert based on context

### AlertManager

Manages alerts and notifications

**Methods:**

- `add_alert()` - Add a new alert configuration
- `configure_email()` - Configure email notifications
- `configure_slack()` - Configure Slack webhook notifications
- `configure_webhook()` - Configure custom webhook notifications
- `check_alerts()` - Check all alerts against current metrics

### AlertSeverity

Alert severity levels

### BaselineCalculator

Automatically calculate intelligent performance baselines from historical data.

**Methods:**

- `calculate_from_percentile()` - Calculate baseline using percentile method
- `calculate_with_iqr_filtering()` - Calculate baseline using IQR method to exclude outliers
- `calculate_intelligent_baseline()` - Calculate intelligent baseline automatically selecting optimal method.
- `calculate_time_based_baseline()` - Calculate baseline comparing recent performance to historical

### BenchmarkManager

Manage performance benchmarks and detect regressions between versions.

**Methods:**

- `create_benchmark()` - Create a performance benchmark from current metrics
- `compare_benchmarks()` - Compare two benchmark versions to detect changes
- `detect_regressions()` - Detect performance regressions in a benchmark
- `list_benchmarks()` - List all benchmarks or versions of a specific benchmark

### CICDIntegration

CI/CD pipeline integration features

**Methods:**

- `add_performance_gate()` - Add a performance gate
- `check_gates()` - Check all performance gates
- `load_baseline()` - Load baseline metrics from file
- `save_baseline()` - Save current metrics as baseline
- `compare_with_baseline()` - Compare current metrics with baseline

### DataExporter

Export metrics to various formats (CSV, JSON, Parquet)

**Methods:**

- `export_to_csv()` - Export metrics to CSV file
- `export_to_json()` - Export metrics to JSON file
- `export_to_parquet()` - Export metrics to Parquet file (requires pyarrow)

### EnterpriseIntegrations

Integrate with enterprise monitoring platforms (DataDog, New Relic, Prometheus, etc).

**Methods:**

- `send_to_datadog()` - Send metrics to Datadog
- `send_to_prometheus()` - Send metrics to Prometheus via Pushgateway
- `send_to_newrelic()` - Send metrics to New Relic
- `get_integration_status()` - Get status of all configured integrations

### ExecutionHook

Hook system for custom pre/post execution logic.

**Methods:**

- `register_pre_hook()` - Register pre-execution hook function.
- `register_post_hook()` - Register post-execution hook function.
- `execute_pre_hooks()` - Execute all registered pre-execution hooks.
- `execute_post_hooks()` - Execute all registered post-execution hooks.

### HistoryManager

Manages persistent storage and retrieval of execution metrics using SQLite.

**Methods:**

- `save_execution()` - Save execution metrics to database.
- `save_alerts()` - Save triggered alerts for an execution
- `get_execution_history()` - Retrieve execution history with optional filtering.
- `get_metrics_for_script()` - Get all values of a specific metric for a script over time
- `get_aggregated_metrics()` - Get aggregated statistics for metrics

### LogAnalyzer

Analyzes logs and detects error patterns and anomalies.

**Methods:**

- `extract_error_patterns()` - Extract error patterns from text.
- `analyze_execution_log()` - Comprehensive analysis of execution logs.
- `generate_summary()` - Generate summary statistics from multiple analyses.

### MLAnomalyDetector

Machine learning-based anomaly detection for metrics

**Methods:**

- `detect_anomalies_zscore()` - Detect anomalies using Z-score method
- `detect_anomalies_iqr()` - Detect anomalies using Interquartile Range method
- `detect_trend_anomalies()` - Detect anomalies based on trend changes
- `get_predictive_baseline()` - Calculate predictive baseline using statistical methods

### MetricsCorrelationAnalyzer

Analyzes correlations between different metrics to identify relationships and dependencies.

**Methods:**

- `analyze_metric_correlations()` - Analyze correlations between all available metrics
- `find_metric_predictors()` - Find metrics that predict or strongly correlate with a target metric
- `detect_metric_dependencies()` - Detect lagged dependencies between metrics (X at time t predicts Y at time t+lag)

### PerformanceGate

Performance gate for CI/CD integration

**Methods:**

- `check()` - Check if gate passes

### PerformanceOptimizer

Analyze metrics and provide optimization recommendations

**Methods:**

- `analyze_script_performance()` - Analyze script performance and generate recommendations
- `get_optimization_report()` - Generate a human-readable optimization report

### ProcessMonitor

Monitor child process resource usage during execution.

**Methods:**

- `start()` - 
- `stop()` - 
- `get_summary()` - Get aggregated monitoring summary statistics.

### RemoteExecutor

Execute scripts on remote machines and containers

**Methods:**

- `execute_ssh()` - Execute script on remote host via SSH
- `execute_docker()` - Execute script in Docker container
- `execute_kubernetes()` - Execute script as Kubernetes Job

### ResourceForecaster

Predict future resource needs and forecast SLA compliance.

**Methods:**

- `forecast_metric()` - Forecast metric values for future periods
- `predict_sla_compliance()` - Predict SLA compliance based on forecasted metrics
- `estimate_capacity_needs()` - Estimate capacity needs based on metric growth

### RetentionPolicy

Configurable data retention and archival policies (compliance: SOC2, HIPAA)

**Methods:**

- `add_policy()` - Add retention policy
- `apply_policy()` - Apply retention policy
- `get_policies()` - Get all configured policies

### RetryConfig

Configuration for retry behavior with multiple backoff strategies

**Methods:**

- `get_delay()` - Calculate delay for given attempt number (0-indexed)
- `should_retry()` - Determine if retry should be attempted
- `get_retry_info()` - Get human-readable retry configuration

### RetryStrategy

Available retry backoff strategies

### ScheduledTask

Represents a scheduled task

### ScriptNode

Represents a script node in a DAG

**Methods:**

- `add_dependency()` - Add a dependency on another script

### ScriptRunner

Enhanced wrapper class to run Python scripts with comprehensive metrics collection.

**Methods:**

- `load_config()` - Load runner configuration from YAML file.
- `collect_system_metrics_start()` - 
- `collect_system_metrics_end()` - 
- `validate_script()` - Validate script exists and is readable before execution.
- `run_script()` - Execute script with advanced retry and monitoring capabilities.

### ScriptWorkflow

DAG-based multi-script orchestration engine (68% demand feature)

**Methods:**

- `add_script()` - Add script to workflow
- `build_dag()` - Build DAG and validate for cycles
- `get_executable_scripts()` - Get scripts ready to execute (all dependencies met)
- `execute()` - Execute workflow sequentially
- `get_statistics()` - Get workflow execution statistics

### StructuredLogger

Provides structured JSON logging for all events.

**Methods:**

- `log_event()` - Log a structured event.
- `get_logs()` - Retrieve logs with optional filtering.

### TaskScheduler

Manages scheduled script execution and event-driven triggers

**Methods:**

- `add_scheduled_task()` - Add a scheduled task
- `add_event_trigger()` - Add event trigger for a task
- `trigger_event()` - Trigger an event and return tasks to execute
- `get_due_tasks()` - Get tasks that are due for execution
- `mark_executed()` - Mark task as executed

### TimeSeriesDB

Advanced time-series query API for metrics with flexible filtering and aggregations

**Methods:**

- `query()` - Query metrics with flexible filtering
- `aggregate()` - Aggregate metric values using specified method
- `aggregations()` - Calculate multiple aggregations at once
- `bucket()` - Downsample metrics into time buckets for large datasets
- `metrics_list()` - Get list of available metrics for query context

### TrendAnalyzer

Analyze trends in metrics and detect performance regressions.

**Methods:**

- `calculate_linear_regression()` - Calculate linear regression trend line for metric values.
- `detect_anomalies()` - Detect anomalies in metric values using statistical methods.
- `detect_regression()` - Detect performance regressions (significant increases in metric values)
- `calculate_percentiles()` - Calculate key percentiles for a metric series
- `analyze_metric_history()` - Comprehensive analysis of a metric's history

## Usage Examples

### Basic Execution

```python
from runner import ScriptRunner

runner = ScriptRunner('myscript.py')
result = runner.execute()
print(f"Exit code: {result['exit_code']}")
```

### With History Tracking

```python
from runner import ScriptRunner, HistoryManager

history = HistoryManager('metrics.db')
runner = ScriptRunner('script.py', history_manager=history)
result = runner.execute()
```

### With Alerts

```python
from runner import ScriptRunner, AlertManager

runner = ScriptRunner('script.py')
alerts = AlertManager()
alerts.add_alert('cpu_high', 'cpu_max > 80')
result = runner.execute()
```

### Workflow Orchestration

```python
from runner import ScriptWorkflow

workflow = ScriptWorkflow('my_pipeline', max_parallel=4)
workflow.add_script('task1', 'script1.py')
workflow.add_script('task2', 'script2.py', dependencies=['task1'])
result = workflow.execute()
```

