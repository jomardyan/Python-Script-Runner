# WEBAPI

A minimal FastAPI wrapper for `runner.py` that exposes HTTP endpoints and a
small HTML dashboard. The service is intentionally lightweight so it can be
used like a serverless function or small container.

## Dashboard

![Dashboard – Launch Script & Recent Runs](https://github.com/user-attachments/assets/9c16d393-0fd9-4d49-a273-5bad4d01cba8)

The dashboard shows real-time stats (total runs, last 24 h, success rate), the
launch form with all configuration options, and the runs table with correlation
IDs, runner status badges, and per-run action buttons (Logs · Details · Stop ·
Kill · ↺ Restart).

## Features

### Existing endpoints
- `POST /api/run` — queue a script execution (validated paths, env-var filtering)
- `POST /api/run/upload` — upload a Python file and queue execution
- `GET  /api/runs` — list runs with pagination and status filter
- `GET  /api/runs/{id}` — full run record including correlation ID and error summary
- `POST /api/runs/{id}/cancel` — graceful cancellation
- `GET  /api/runs/{id}/logs` — captured stdout/stderr as plain text
- `GET  /api/stats` — total/24 h/by-status aggregates
- `GET  /api/system/status` — CPU load and memory usage
- `GET  /` — interactive HTML dashboard

### New endpoints (v1.3.0)
- `POST /api/runs/{id}/stop` — send a graceful stop signal (sets `_stop_event`; watchdog kills the process tree)
- `POST /api/runs/{id}/kill` — immediately SIGKILL the process and all children
- `POST /api/runs/{id}/restart` — cancel if active, then queue a fresh execution with the same parameters (returns `202`)
- `GET  /api/runs/{id}/events` — return the structured execution events (`start`, `success`, `failure`, `timeout`, `forced_termination`) recorded by `StructuredLogger`

### New `RunRequest` fields
| Field | Type | Default | Description |
|---|---|---|---|
| `working_dir` | `string \| null` | `null` | Working directory for the subprocess (defaults to the script's own directory) |
| `stream_output` | `bool` | `false` | Stream stdout/stderr to the runner logger in real time while also capturing them |

### New `RunRecord` fields
| Field | Type | Description |
|---|---|---|
| `correlation_id` | `string \| null` | UUID4 generated per execution by `ScriptRunner` |
| `run_status` | `string \| null` | Runner's own status: `success` / `failed` / `timeout` / `killed` |
| `error_summary` | `object \| null` | Structured dict with `exit_code`, `stderr_snippet`, `status`, `correlation_id` on non-zero exit |

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

