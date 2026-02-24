# WEBAPI

A FastAPI wrapper for `runner.py` that exposes HTTP endpoints and an interactive HTML dashboard. The service is intentionally lightweight so it can be deployed like a serverless function or small container.

## Dashboard

### Runner Tab
![Dashboard – Launch Script & Recent Runs](https://github.com/user-attachments/assets/9c16d393-0fd9-4d49-a273-5bad4d01cba8)

The Runner tab shows real-time stats (total runs, last 24 h, success rate), the
launch form with all configuration options, and the runs table with correlation
IDs, runner status badges, and per-run action buttons (Logs · Details · Stop ·
Kill · ↺ Restart).

### Script Library Tab
![Library Tab – Folder Roots & Tags](https://github.com/user-attachments/assets/f131f6f0-ada6-40bd-9f91-9d85ab151ec6)
![Script Browser](https://github.com/user-attachments/assets/d6b9dd3d-0553-4a19-ba5d-2490b83df27a)
![Content Viewer](https://github.com/user-attachments/assets/6fd3a964-0a97-42a8-b2af-936eb5b16bb5)

The Script Library tab (Script-Manager feature parity) lets you:
- Register folder roots and trigger background scans to index scripts
- Browse, search, and filter scripts by name, language, lifecycle status, tag, or folder root
- Preview file content directly in the dashboard
- Assign lifecycle status (`active`, `draft`, `deprecated`, `archived`), owner, environment, and notes to each script
- Manage coloured tags and attach them to scripts
- Detect duplicate scripts (same name + size + line count)
- Launch any indexed script directly with the **▶ Run** button (switches to Runner tab)

## Features

### Core endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Liveness check — returns `{"status":"ok"}` |
| `GET` | `/api/system/status` | CPU load averages and memory usage |
| `GET` | `/api/stats` | Total / 24 h / by-status aggregates |
| `GET` | `/` | Interactive HTML dashboard |

### Run lifecycle endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/run` | Queue a script execution (validated paths, env-var filtering) |
| `POST` | `/api/run/upload` | Upload a Python file and queue execution |
| `GET`  | `/api/runs` | List runs with pagination and status filter |
| `GET`  | `/api/runs/{id}` | Full run record including correlation ID and error summary |
| `POST` | `/api/runs/{id}/cancel` | Graceful cancellation |
| `GET`  | `/api/runs/{id}/logs` | Captured stdout/stderr as plain text |
| `GET`  | `/api/runs/{id}/events` | Structured execution events from `StructuredLogger` |
| `GET`  | `/api/runs/{id}/visualization` | Per-step timing report from `ExecutionVisualizer` |
| `POST` | `/api/runs/{id}/stop` | Graceful stop via `runner.stop()` |
| `POST` | `/api/runs/{id}/kill` | Force kill via `runner.kill()` |
| `POST` | `/api/runs/{id}/restart` | Cancel if active, queue fresh run (returns `202`) |
| `DELETE` | `/api/runs/{id}` | Delete a specific (completed) run record |
| `DELETE` | `/api/runs` | Bulk delete run records (body: `["id1","id2",...]`) |

### Script Library endpoints (v1.4.0)

#### Folder Roots
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/library/folder-roots` | List all registered folder roots |
| `POST` | `/api/library/folder-roots` | Register a new folder root |
| `DELETE` | `/api/library/folder-roots/{id}` | Remove a folder root and its scripts |
| `POST` | `/api/library/folder-roots/{id}/scan` | Trigger a background scan (returns `scan_id`) |
| `GET` | `/api/library/folder-roots/{id}/scan/{scan_id}` | Poll scan status |

#### Scripts
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/library/scripts` | List/search scripts (filters: language, status, tag, root_id, search) |
| `GET` | `/api/library/scripts/{id}` | Full script details |
| `GET` | `/api/library/scripts/{id}/content` | Raw file content (UTF-8) |
| `PUT` | `/api/library/scripts/{id}/status` | Update lifecycle status, owner, environment, notes |
| `GET` | `/api/library/scripts/{id}/notes` | Get notes |
| `POST` | `/api/library/scripts/{id}/tags/{tag_id}` | Attach a tag |
| `DELETE` | `/api/library/scripts/{id}/tags/{tag_id}` | Detach a tag |
| `POST` | `/api/library/scripts/{id}/run` | Queue execution of a library script |

#### Tags & Utilities
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/library/tags` | List all tags (with script counts) |
| `POST` | `/api/library/tags` | Create a tag |
| `DELETE` | `/api/library/tags/{id}` | Delete a tag |
| `GET` | `/api/library/duplicates` | Find duplicate scripts |
| `GET` | `/api/library/stats` | Library aggregate statistics |

### Analytics endpoints (v1.5.0)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analytics/history` | Execution history from `HistoryManager` (filter by `script_path`, `days`, `limit`) |
| `GET` | `/api/analytics/history/stats` | Database statistics from `HistoryManager` |
| `GET` | `/api/analytics/trends` | Linear regression trend for a metric (`metric`, `script_path`, `days`) |
| `GET` | `/api/analytics/anomalies` | Anomaly detection on a metric (`method`: `iqr` / `zscore` / `mad`) |
| `GET` | `/api/analytics/baseline` | Performance baseline calculation (`method`: `percentile` / `iqr` / `intelligent`) |
| `POST` | `/api/analytics/export` | Download metrics as JSON or CSV file |
| `GET` | `/api/analytics/benchmarks` | List benchmarks or versions of a specific benchmark |
| `POST` | `/api/analytics/benchmarks` | Create a performance benchmark snapshot |
| `GET` | `/api/analytics/benchmarks/{name}/regressions` | Detect regressions vs previous versions |
| `DELETE` | `/api/analytics/cleanup` | Delete history records older than `days` (default: 90) |

### Scheduler endpoints (v1.5.0)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/scheduler/tasks` | List all registered scheduled tasks |
| `POST` | `/api/scheduler/tasks` | Register a new task (schedule or cron expression, optional dependencies) |
| `DELETE` | `/api/scheduler/tasks/{task_id}` | Remove a scheduled task |
| `POST` | `/api/scheduler/tasks/{task_id}/run` | Trigger a scheduled task immediately (returns `202`) |
| `POST` | `/api/scheduler/events/{event_name}` | Fire a named event and return triggered task IDs |
| `GET` | `/api/scheduler/due` | Return tasks currently due for execution |

### `RunRequest` fields
| Field | Type | Default | Description |
|---|---|---|---|
| `script_path` | `string` | — | Path to the Python script to execute |
| `args` | `string[]` | `[]` | Arguments passed to the script |
| `timeout` | `int \| null` | `null` | Timeout in seconds |
| `log_level` | `string` | `"INFO"` | Logging level |
| `retry_on_failure` | `bool` | `false` | Enable retry on failure |
| `retry_max_attempts` | `int` | `3` | Maximum retry attempts |
| `retry_strategy` | `string` | `"exponential"` | Backoff: `linear`, `exponential`, `fibonacci`, `exponential_jitter` |
| `retry_initial_delay` | `float` | `1.0` | Initial retry delay (seconds) |
| `retry_max_delay` | `float` | `60.0` | Maximum retry delay (seconds) |
| `retry_multiplier` | `float` | `2.0` | Multiplier for exponential backoff |
| `retry_max_time` | `float` | `300.0` | Maximum total retry time (seconds) |
| `working_dir` | `string \| null` | `null` | Working directory for the subprocess |
| `stream_output` | `bool` | `false` | Stream stdout/stderr in real time while capturing |
| `monitor_interval` | `float` | `0.1` | Process monitor sampling interval (seconds) |
| `enable_visualizer` | `bool` | `false` | Enable `ExecutionVisualizer` and store report |
| `visualizer_format` | `string` | `"text"` | Visualizer output format: `text` or `json` |
| `env_vars` | `object` | `{}` | Environment variables for the execution |
| `history_db` | `string \| null` | `null` | Override the metrics history SQLite DB path |
| `enable_history` | `bool` | `true` | Persist run metrics to the SQLite database |
| `performance_gates` | `object[]` | `[]` | Gates list: `[{metric, max_value?, min_value?}]` |
| `junit_output` | `string \| null` | `null` | Path to write JUnit XML output |
| `save_baseline` | `string \| null` | `null` | Save current run metrics as baseline JSON |
| `load_baseline` | `string \| null` | `null` | Load baseline JSON for comparison |
| `alerts` | `object[]` | `[]` | Alert rules: `[{name, condition, channels, severity?}]` |
| `slack_webhook` | `string \| null` | `null` | Slack webhook URL for alert notifications |
| `dry_run` | `bool` | `false` | Validate and show execution plan without running |
| `enable_code_analysis` | `bool` | `false` | Run static code analysis / security scan before execution |
| `enable_secret_scanning` | `bool` | `false` | Scan script for hardcoded secrets before execution |
| `enable_dependency_scanning` | `bool` | `false` | Scan requirements.txt for known vulnerabilities |
| `enable_cost_tracking` | `bool` | `false` | Enable cloud cost tracking during execution |

### `RunRecord` fields
| Field | Type | Description |
|---|---|---|
| `id` | `string` | Run UUID |
| `status` | `string` | API-level status: `queued` / `running` / `completed` / `failed` / `cancelled` |
| `started_at` | `datetime` | UTC start timestamp |
| `finished_at` | `datetime \| null` | UTC finish timestamp |
| `correlation_id` | `string \| null` | UUID4 from `ScriptRunner` |
| `run_status` | `string \| null` | Runner's own status: `success` / `failed` / `timeout` / `killed` |
| `error_summary` | `object \| null` | Structured dict with `exit_code`, `stderr_snippet`, `status`, `correlation_id` |

## Quick start

```bash
pip install -r WEBAPI/requirements.txt
python WEBAPI/api.py --host 0.0.0.0 --port 9000
# or use the helper script (respects HOST/PORT env vars)
./WEBAPI/serve.sh
```

Then open http://localhost:9000 to launch scripts and monitor progress.

## Running tests

```bash
pip install pytest pytest-timeout httpx fastapi python-multipart psutil pyyaml
python -m pytest tests/unit/test_webapi.py -v
```

## Deployment and usage notes

- Constrain script execution roots via `WEBAPI_ALLOWED_ROOT` to avoid executing arbitrary paths
- Persist run history outside the container by pointing `WEBAPI_RUN_DB` at a mounted volume
- For production, run with `uvicorn WEBAPI.api:app --host 0.0.0.0 --port 9000 --workers 2 --log-level info`
- Health: `GET /api/health`; Metrics/log review: `GET /api/runs`, `GET /api/runs/{id}/logs`

