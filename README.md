# Python Script Runner

A production-grade Python script execution engine with comprehensive monitoring, alerting, analytics, and real-time visualization.

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/python-script-runner?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/python-script-runner)

---

## Features

- **Script execution** with timeout, retry, and environment management
- **Real-time visualization** of the full execution pipeline
- **DAG-based workflow orchestration** with parallel execution
- **Metrics collection** — CPU, memory, I/O, timing per run
- **Alert management** — rule-based triggers via Slack, email, webhooks
- **History & trend analysis** — SQLite persistence with anomaly detection
- **CI/CD integration** — JUnit XML, TAP output, performance gates
- **Remote execution** — SSH, Docker, Kubernetes
- **Web dashboard** — FastAPI backend with WebSocket live updates

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
                 [--retry N] [--retry-strategy {linear,exponential,fibonacci}]
                 [--monitor-interval SECONDS]
                 [--show-history] [--analyze-trend]
                 [--dashboard] ...
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
