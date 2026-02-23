# WEBAPI

A minimal FastAPI wrapper for `runner.py` that exposes HTTP endpoints and a
small HTML dashboard. The service is intentionally lightweight so it can be
deployed like a serverless function or small container.

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

### Run lifecycle endpoints (v1.3.0)
- `POST /api/runs/{id}/stop` — graceful stop via `runner.stop()`
- `POST /api/runs/{id}/kill` — force kill via `runner.kill()`
- `POST /api/runs/{id}/restart` — cancel if active, queue fresh run (returns `202`)
- `GET  /api/runs/{id}/events` — structured execution events from `StructuredLogger`

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

### `RunRequest` fields (v1.3.0+)
| Field | Type | Default | Description |
|---|---|---|---|
| `working_dir` | `string \| null` | `null` | Working directory for the subprocess |
| `stream_output` | `bool` | `false` | Stream stdout/stderr in real time while capturing |

### `RunRecord` fields (v1.3.0+)
| Field | Type | Description |
|---|---|---|
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

