# Python Script Runner

A production-grade Python script execution engine with comprehensive monitoring, alerting, analytics, and real-time visualization.

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/python-script-runner?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/python-script-runner)
![Version](https://img.shields.io/badge/version-7.4.4-blue)

---

## Features

- **Script execution** with timeout, retry, and environment management
- **Real-time visualization** of the full execution pipeline
- **DAG-based workflow orchestration** with parallel execution
- **Metrics collection** — CPU, memory, I/O, timing per run
- **Alert management** — rule-based triggers via Slack, email, webhooks with deduplication
- **History & trend analysis** — SQLite persistence with anomaly detection (IQR, Z-score, MAD)
- **CI/CD integration** — JUnit XML, TAP output, performance gates, baseline comparison
- **Remote execution** — SSH, Docker, Kubernetes
- **Web dashboard** — FastAPI REST API with interactive HTML dashboard
- **Security scanning** — code analysis, secret detection, dependency vulnerability scanning
- **Task scheduler** — cron and interval-based scheduling with dependency chains
- **Analytics API** — trends, anomalies, benchmarks, and data export (JSON/CSV)
- **Cloud cost tracking** — resource usage cost estimation during execution
- **Dry-run mode** — validate and preview execution plan without running the script

---

## Visualization

Run any script with real-time orchestration visualization using the `--visualize` flag:

```bash
python runner.py my_script.py --visualize
```

![Execution Flow Visualization](https://github.com/user-attachments/assets/c490c6b2-ece7-4993-98e8-2a9e5b34bcc9)

Each step of the pipeline is displayed with elapsed time and per-step duration (e.g. `(0.101s)`). Status symbols:

| Symbol | Meaning |
|--------|---------|
| `⏳`  | Running |
| `✓`   | Done    |
| `⊘`   | Skipped |
| `✗`   | Error   |
| `🚀`  | Subprocess launched |

### Output file

Write a clean (ANSI-free) copy to disk:

```bash
python runner.py my_script.py --visualize --visualize-output run.log
```

### JSON output format

Machine-readable structured output for CI pipelines and integrations:

```bash
python runner.py my_script.py --visualize --visualize-format json
```

![JSON Visualization Output](https://github.com/user-attachments/assets/f4b8952f-261c-4a10-93df-6a03d1c75c92)

The JSON document contains a `header`, a `steps` list with per-step `elapsed_s` and `duration_s`, and a `footer`. Access it programmatically with `get_execution_report()`:

```python
from runner import ExecutionVisualizer

v = ExecutionVisualizer(enabled=True, output_format="json", output_file="run.log")
v.show_header("pipeline.py")
# ... steps recorded automatically during runner.run_script() ...
v.show_footer(1.23, success=True)

report = v.get_execution_report()
slow_steps = [s for s in report["steps"] if s.get("duration_s", 0) > 0.5]
```

---

## Workflow Orchestration

Execute multiple scripts as a DAG with optional parallelism:

```python
from runner import ScriptWorkflow

wf = ScriptWorkflow(
    name="data_pipeline",
    max_parallel=2,          # run up to 2 scripts concurrently
    stop_on_failure=True,    # abort if any script fails
    on_step_callback=lambda name, status, result: print(f"{name}: {status}"),
)

wf.add_script("fetch",     "fetch.py")
wf.add_script("transform", "transform.py", dependencies=["fetch"])
wf.add_script("validate",  "validate.py",  dependencies=["fetch"])
wf.add_script("load_db",   "load_db.py",   dependencies=["transform", "validate"])

# Visualize the DAG before running
print(wf.visualize_dag())

result = wf.execute()
```

![Workflow DAG and Parallel Execution](https://github.com/user-attachments/assets/3649cde3-a311-460c-bbfa-c6ce8bf3afe7)

### `visualize_dag()`

Prints an ASCII-art dependency graph showing node names, dependency arrows, and live execution status:

```
Workflow: data_pipeline
─────────────────────────────────────────────
[fetch       ] (pending)
    └──▶ [transform   ] (pending)
        └──▶ [load_db     ] (pending)
    └──▶ [validate    ] (pending)
─────────────────────────────────────────────
```

### `execute()` result

```python
{
    "status": "completed",   # or "aborted" if stop_on_failure triggered
    "total_scripts": 4,
    "successful": 4,
    "failed": 0,
    "total_time": 0.054,
    "results": { ... }       # per-script exit codes, timings, success flags
}
```

---

## CLI Reference

```
usage: runner.py [-h] [--timeout TIMEOUT] [--visualize]
                 [--visualize-format {text,json}]
                 [--visualize-output FILE]
                 [--retry N] [--retry-strategy {linear,exponential,fibonacci,exponential_jitter}]
                 [--monitor-interval SECONDS]
                 [--show-history] [--analyze-trend]
                 [--dashboard] [--dry-run]
                 [--enable-code-analysis] [--enable-secret-scanning]
                 [--enable-dependency-scanning]
                 script [script_args ...]
```

Key flags:

| Flag | Description |
|------|-------------|
| `--visualize` | Show real-time execution flow |
| `--visualize-format {text,json}` | Output format (default: `text`) |
| `--visualize-output FILE` | Also write visualization to a file |
| `--retry N` | Retry on failure up to N times |
| `--retry-strategy` | `linear`, `exponential`, `fibonacci`, `exponential_jitter` |
| `--timeout SECONDS` | Kill script after N seconds |
| `--monitor-interval S` | Metric sampling interval (default: 0.1s) |
| `--show-history` | Print recent execution history |
| `--analyze-trend` | Run trend analysis on metric history |
| `--dashboard` | Start the web dashboard |
| `--dry-run` | Validate and show execution plan without running the script |
| `--enable-code-analysis` | Run static code analysis before execution |
| `--enable-secret-scanning` | Scan script for hardcoded secrets before execution |
| `--enable-dependency-scanning` | Scan requirements.txt for known vulnerabilities |

---

## Security Scanning

Pre-execution security checks protect against common risks before a script ever runs:

```python
from runner import ScriptRunner

runner = ScriptRunner("my_script.py")
runner.enable_code_analysis = True       # Static analysis / linting
runner.enable_secret_scanning = True     # Detect hardcoded credentials
runner.enable_dependency_scanning = True # Audit requirements.txt for CVEs
result = runner.run_script()
```

All findings are surfaced in the execution result and, if alerts are configured, dispatched through the alert pipeline.

---

## Task Scheduler

Schedule scripts with cron expressions or plain-English intervals. Tasks can declare dependencies on other tasks to form execution chains:

```python
from runner import TaskScheduler

scheduler = TaskScheduler()

# Interval-based
scheduler.add_scheduled_task(
    task_id="refresh_data",
    script_path="fetch.py",
    schedule="every 5 minutes",
)

# Cron-based with dependency
scheduler.add_scheduled_task(
    task_id="daily_report",
    script_path="report.py",
    cron_expr="0 8 * * *",          # 08:00 every day
    dependencies=["refresh_data"],  # wait for refresh_data to complete first
)

# Run all tasks that are currently due
for task in scheduler.get_due_tasks():
    task.run()
```

---

## Analytics & Benchmarks

Query historical execution data, detect regressions, and export metrics:

```python
from runner import HistoryManager, TrendAnalyzer, BenchmarkManager

hm = HistoryManager()

# Trend analysis on execution time over the last 30 days
history = hm.get_execution_history(script_path="etl.py", days=30)
values  = [e["metrics"]["execution_time_seconds"] for e in history]

ta     = TrendAnalyzer()
trend  = ta.calculate_linear_regression(values)
anomalies = ta.detect_anomalies(values, method="iqr")   # or "zscore", "mad"

# Performance benchmarks & regression detection
bm = BenchmarkManager()
bm.create_benchmark("nightly_etl", script_path="etl.py")
regressions = bm.detect_regressions("nightly_etl", regression_threshold=10.0)

# Export to CSV or JSON
from runner import DataExporter
exporter = DataExporter(hm)
exporter.export_to_csv("metrics.csv", script_path="etl.py")
```

---

## Performance Gates & Baseline

Fail CI runs automatically when a metric exceeds a threshold:

```python
from runner import ScriptRunner, CICDIntegration, PerformanceGate

runner = ScriptRunner("pipeline.py")
result = runner.run_script()

cicd = CICDIntegration(runner)
cicd.add_performance_gate(PerformanceGate(metric="cpu_max",       max_value=85.0))
cicd.add_performance_gate(PerformanceGate(metric="memory_max_mb", max_value=512.0))
gate_result = cicd.check_performance_gates(result)
cicd.generate_junit_xml(result, "test-results.xml")
```

---

## Installation

```bash
pip install python-script-runner
```

Or from source:

```bash
git clone https://github.com/jomardyan/Python-Script-Runner
cd Python-Script-Runner
pip install -e .
```

---

## 👨‍💻 Author

**Hayk Jomardyan**

- 🌐 Website: [lolino.pl](https://lolino.pl)
- 📧 Email: [hayk.jomardyan@outlook.com](mailto:hayk.jomardyan@outlook.com)
- 💼 GitHub: [@jomardyan](https://github.com/jomardyan)

## License

MIT License - See LICENSE file for details
