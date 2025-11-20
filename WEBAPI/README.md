# WEBAPI

A minimal FastAPI wrapper for `runner.py` that exposes HTTP endpoints and a
small HTML dashboard. The service is intentionally lightweight so it can be
used like a serverless function or small container.

## Features
- `POST /api/run` to queue a script execution with ScriptRunner (validated paths)
- `GET /api/runs` and `/api/runs/{id}` for live status with pagination and filtering
- `POST /api/runs/{id}/cancel` to request cancellation of queued/running jobs
- `GET /api/runs/{id}/logs` to fetch captured stdout/stderr for a run
- `GET /` serves a static dashboard that uses the API and supports filtering/cancellation
- SQLite-backed registry for runs at `WEBAPI/runs.db` (configurable via `WEBAPI_RUN_DB`)

## Quick start
```bash
pip install -r WEBAPI/requirements.txt
python WEBAPI/api.py --host 0.0.0.0 --port 9000
# or use the helper script (respects HOST/PORT env vars)
./WEBAPI/serve.sh
```

Then open http://localhost:9000 to launch scripts and monitor progress.

## Deployment and usage notes
- Constrain script execution roots via `WEBAPI_ALLOWED_ROOT` to avoid executing arbitrary paths
- Persist run history outside the container by pointing `WEBAPI_RUN_DB` at a mounted volume
- For production, run with `uvicorn WEBAPI.api:app --host 0.0.0.0 --port 9000 --workers 2 --log-level info`
- Health: `GET /api/health`; Metrics/log review: `GET /api/runs`, `GET /api/runs/{id}/logs`
