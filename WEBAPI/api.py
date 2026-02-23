"""Lightweight web API and dashboard wrapper around ScriptRunner.

This module exposes a minimal FastAPI service that lets users trigger
script executions via HTTP endpoints and observe their status on a
simple web dashboard. It is intentionally small and self contained so
it can be deployed like a serverless function.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, UploadFile, File, Form, Body
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure runner.py is importable when the service is launched from the
# WEBAPI directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runner import ScriptRunner  # noqa: E402


class RunRequest(BaseModel):
    """Input payload for a script execution."""

    script_path: str = Field(..., description="Path to the Python script to execute")
    args: List[str] = Field(default_factory=list, description="Arguments passed to the script")
    timeout: Optional[int] = Field(None, description="Optional timeout in seconds")
    log_level: str = Field("INFO", description="Logging level for the ScriptRunner")
    retry_on_failure: bool = Field(
        False, description="Enable ScriptRunner retry configuration during execution"
    )
    history_db: Optional[str] = Field(
        None, description="Optional override for the metrics history SQLite database"
    )
    enable_history: bool = Field(
        True, description="Persist run metrics to the configured SQLite database"
    )
    env_vars: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables to set for the execution"
    )
    working_dir: Optional[str] = Field(
        None,
        description="Working directory for the script process. Defaults to the script's own directory.",
    )
    stream_output: bool = Field(
        False,
        description="Stream stdout/stderr to the runner logger in real time while also capturing them.",
    )


class RunRecord(BaseModel):
    """Stored representation of a running or completed job."""

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    request: RunRequest
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    # Fields populated from the ScriptRunner result
    correlation_id: Optional[str] = None
    run_status: Optional[str] = None  # runner's own status: success/failed/timeout/killed
    error_summary: Optional[Dict[str, Any]] = None


RUN_DB_PATH = Path(os.environ.get("WEBAPI_RUN_DB", PROJECT_ROOT / "WEBAPI" / "runs.db"))
ALLOWED_SCRIPT_ROOT = Path(os.environ.get("WEBAPI_ALLOWED_ROOT", PROJECT_ROOT)).resolve()
UPLOAD_DIR = PROJECT_ROOT / "WEBAPI" / "uploads"


class RunStore:
    """Lightweight SQLite-backed store for run metadata and logs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._ensure_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    stdout TEXT,
                    stderr TEXT,
                    correlation_id TEXT,
                    run_status TEXT,
                    error_summary_json TEXT
                )
                """
            )
            # Add new columns to existing databases (idempotent).
            # Column names and types are sourced from a hardcoded list only—never
            # from user input—so the f-string usage below is safe.
            _NEW_COLS: List[tuple] = [
                ("correlation_id", "TEXT"),
                ("run_status", "TEXT"),
                ("error_summary_json", "TEXT"),
            ]
            _ALLOWED_COLS = frozenset(col for col, _ in _NEW_COLS)
            for col, typedef in _NEW_COLS:
                assert col in _ALLOWED_COLS  # guard against accidental expansion
                try:
                    conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {typedef}")  # noqa: S608
                except sqlite3.OperationalError:
                    pass  # column already exists
            conn.commit()

    def upsert(self, record: RunRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, status, started_at, finished_at, request_json,
                    result_json, error, stdout, stderr,
                    correlation_id, run_status, error_summary_json
                )
                VALUES (
                    :id, :status, :started_at, :finished_at, :request_json,
                    :result_json, :error, :stdout, :stderr,
                    :correlation_id, :run_status, :error_summary_json
                )
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    request_json=excluded.request_json,
                    result_json=excluded.result_json,
                    error=excluded.error,
                    stdout=excluded.stdout,
                    stderr=excluded.stderr,
                    correlation_id=excluded.correlation_id,
                    run_status=excluded.run_status,
                    error_summary_json=excluded.error_summary_json
                """,
                {
                    "id": record.id,
                    "status": record.status,
                    "started_at": record.started_at.isoformat(),
                    "finished_at": record.finished_at.isoformat() if record.finished_at else None,
                    "request_json": record.request.json(),
                    "result_json": json.dumps(record.result) if record.result is not None else None,
                    "error": record.error,
                    "stdout": record.result.get("stdout") if record.result else None,
                    "stderr": record.result.get("stderr") if record.result else None,
                    "correlation_id": record.correlation_id,
                    "run_status": record.run_status,
                    "error_summary_json": json.dumps(record.error_summary) if record.error_summary else None,
                },
            )
            conn.commit()

    def get(self, run_id: str) -> Optional[RunRecord]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return self._row_to_record(row)

    def list(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[RunRecord]:
        query = "SELECT * FROM runs"
        params: List[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: sqlite3.Row) -> RunRecord:
        keys = row.keys()
        error_summary = None
        if "error_summary_json" in keys and row["error_summary_json"]:
            try:
                error_summary = json.loads(row["error_summary_json"])
            except Exception:
                pass
        return RunRecord(
            id=row["id"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            request=RunRequest.parse_raw(row["request_json"]),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
            correlation_id=row["correlation_id"] if "correlation_id" in keys else None,
            run_status=row["run_status"] if "run_status" in keys else None,
            error_summary=error_summary,
        )

    def get_logs(self, run_id: str) -> Optional[Dict[str, Optional[str]]]:
        with self._connect() as conn:
            row = conn.execute("SELECT stdout, stderr FROM runs WHERE id = ?", (run_id,)).fetchone()
        if not row:
            return None
        return {"stdout": row["stdout"], "stderr": row["stderr"]}

    def delete(self, run_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            by_status = dict(conn.execute("SELECT status, COUNT(*) FROM runs GROUP BY status").fetchall())
            
            # Last 24h
            yesterday = (datetime.utcnow().timestamp() - 86400)
            # SQLite stores dates as strings, so we need to be careful. 
            # Assuming ISO format YYYY-MM-DD... which sorts correctly as string.
            yesterday_iso = datetime.fromtimestamp(yesterday).isoformat()
            last_24h = conn.execute("SELECT COUNT(*) FROM runs WHERE started_at > ?", (yesterday_iso,)).fetchone()[0]
            
        return {
            "total_runs": total,
            "by_status": by_status,
            "runs_24h": last_24h
        }


app = FastAPI(title="Script Runner Web API", version="1.3.0")

RUNS: Dict[str, RunRecord] = {}
RUNS_LOCK = threading.Lock()
# RUN_HANDLES stores: {"cancel_event": Event, "runner": ScriptRunner|None}
RUN_HANDLES: Dict[str, Dict[str, Any]] = {}
RUN_STORE = RunStore(RUN_DB_PATH)

with RUNS_LOCK:
    for record in RUN_STORE.list(limit=200):
        RUNS[record.id] = record


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Simple health endpoint for smoke checks."""

    return {"status": "ok"}


@app.get("/api/system/status")
def system_status() -> Dict[str, Any]:
    """Return system resource usage."""
    status = {"cpu_load": [0.0, 0.0, 0.0], "memory": {"total": 0, "available": 0}}
    
    # CPU Load
    if hasattr(os, "getloadavg"):
        status["cpu_load"] = list(os.getloadavg())
    
    # Memory (Linux only)
    if Path("/proc/meminfo").exists():
        try:
            mem_info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0] # kB
                        mem_info[key] = int(val) * 1024 # bytes
            
            if "MemTotal" in mem_info and "MemAvailable" in mem_info:
                status["memory"] = {
                    "total": mem_info["MemTotal"],
                    "available": mem_info["MemAvailable"],
                    "percent": round((1 - mem_info["MemAvailable"] / mem_info["MemTotal"]) * 100, 1)
                }
        except Exception:
            pass
            
    return status


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    """Return aggregated run statistics."""
    return RUN_STORE.get_stats()


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> Dict[str, bool]:
    """Delete a specific run record."""
    with RUNS_LOCK:
        if run_id in RUNS:
            # If running, don't delete
            if RUNS[run_id].status in ("queued", "running"):
                 raise HTTPException(status_code=400, detail="Cannot delete active run")
            del RUNS[run_id]
            
    success = RUN_STORE.delete(run_id)
    if not success:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True}


@app.delete("/api/runs")
def delete_runs(run_ids: List[str] = Body(...)) -> Dict[str, int]:
    """Bulk delete run records."""
    count = 0
    for run_id in run_ids:
        try:
            with RUNS_LOCK:
                if run_id in RUNS:
                    if RUNS[run_id].status in ("queued", "running"):
                        continue
                    del RUNS[run_id]
            if RUN_STORE.delete(run_id):
                count += 1
        except Exception:
            pass
    return {"deleted": count}


def _execute_run(run_id: str, payload: RunRequest, cancel_event: threading.Event) -> None:
    """Worker that executes the script via ScriptRunner and updates the run registry."""

    started_at = datetime.utcnow()
    with RUNS_LOCK:
        RUNS[run_id] = RunRecord(
            id=run_id,
            status="running",
            started_at=started_at,
            finished_at=None,
            request=payload,
        )
    RUN_STORE.upsert(RUNS[run_id])

    try:
        if cancel_event.is_set():
            raise RuntimeError("Run cancelled before start")

        # Filter dangerous env vars before passing to ScriptRunner
        safe_env_vars = {
            k: v for k, v in payload.env_vars.items()
            if k not in _DANGEROUS_ENV_VARS
        }

        runner = ScriptRunner(
            str(_validate_script_path(payload.script_path)),
            script_args=payload.args,
            timeout=payload.timeout,
            log_level=payload.log_level,
            history_db=payload.history_db,
            enable_history=payload.enable_history,
            working_dir=payload.working_dir,
            env_vars=safe_env_vars,
            stream_output=payload.stream_output,
        )

        with RUNS_LOCK:
            if run_id in RUN_HANDLES:
                RUN_HANDLES[run_id]["runner"] = runner

        result = runner.run_script(retry_on_failure=payload.retry_on_failure)

        correlation_id: Optional[str] = result.get("correlation_id")
        run_status: Optional[str] = result.get("status")
        error_summary: Optional[Dict] = result.get("error_summary")
        returncode: int = result.get("returncode", -1)

        if cancel_event.is_set():
            job_status = "cancelled"
            error = "Run cancelled by user"
        else:
            job_status = "completed" if returncode == 0 else "failed"
            error = None

        finished_at = datetime.utcnow()
        record = RunRecord(
            id=run_id,
            status=job_status,
            started_at=started_at,
            finished_at=finished_at,
            request=payload,
            result=result,
            error=error,
            correlation_id=correlation_id,
            run_status=run_status,
            error_summary=error_summary,
        )
        with RUNS_LOCK:
            RUNS[run_id] = record
        RUN_STORE.upsert(record)

    except Exception as exc:  # pragma: no cover - best effort logging
        finished_at = datetime.utcnow()
        record = RunRecord(
            id=run_id,
            status="failed" if not cancel_event.is_set() else "cancelled",
            started_at=started_at,
            finished_at=finished_at,
            request=payload,
            result=None,
            error="Run cancelled by user" if cancel_event.is_set() else str(exc),
        )
        with RUNS_LOCK:
            RUNS[run_id] = record
        RUN_STORE.upsert(record)
    finally:
        RUN_HANDLES.pop(run_id, None)


def _validate_script_path(path_str: str) -> Path:
    if '\x00' in path_str:
        raise HTTPException(status_code=400, detail="Invalid script path")
    raw_path = Path(path_str).expanduser()
    if raw_path.is_symlink():
        raise HTTPException(status_code=400, detail="Symlinks are not allowed")
    candidate = raw_path.resolve()
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail="Script path must point to an existing file")
    try:
        candidate.relative_to(ALLOWED_SCRIPT_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Script must reside within the allowed root") from exc
    if candidate.suffix not in {".py", ".pyw"}:
        raise HTTPException(status_code=400, detail="Only Python files are allowed")
    return candidate


# Environment variables that must not be overridden by API callers.
_DANGEROUS_ENV_VARS = frozenset({
    "PATH", "LD_PRELOAD", "LD_LIBRARY_PATH", "PYTHONPATH",
    "DYLD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES",
})

# Maximum size (in bytes) for captured stdout/stderr to prevent memory exhaustion.
_MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_payload(payload: RunRequest) -> RunRequest:
    _validate_script_path(payload.script_path)
    if payload.timeout is not None and payload.timeout <= 0:
        raise HTTPException(status_code=400, detail="Timeout must be a positive integer")
    if len(payload.args) > 50:
        raise HTTPException(status_code=400, detail="Too many arguments supplied")
    # Filter out dangerous environment variables
    payload.env_vars = {
        k: v for k, v in payload.env_vars.items()
        if k not in _DANGEROUS_ENV_VARS
    }
    # Validate working_dir if provided
    if payload.working_dir is not None:
        wd = Path(payload.working_dir)
        if not wd.is_dir():
            raise HTTPException(status_code=400, detail="working_dir must be an existing directory")
    return payload


def _queue_run(payload: RunRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Helper to queue a run execution."""
    run_id = str(uuid.uuid4())
    now = datetime.utcnow()
    record = RunRecord(
        id=run_id,
        status="queued",
        started_at=now,
        finished_at=None,
        request=payload,
    )
    cancel_event = threading.Event()
    with RUNS_LOCK:
        RUNS[run_id] = record
    RUN_HANDLES[run_id] = {"cancel_event": cancel_event, "runner": None}
    RUN_STORE.upsert(record)

    background_tasks.add_task(_execute_run, run_id, payload, cancel_event)
    return {"run_id": run_id, "status": "queued"}


@app.post("/api/run", status_code=202)
def trigger_run(payload: RunRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Queue a new script execution and return its identifier."""

    payload = _validate_payload(payload)
    return _queue_run(payload, background_tasks)


@app.post("/api/run/upload", status_code=202)
def trigger_run_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    args: str = Form(""),
    timeout: Optional[int] = Form(None),
    log_level: str = Form("INFO"),
    retry_on_failure: bool = Form(False),
    env_vars: str = Form("{}"),
    working_dir: Optional[str] = Form(None),
    stream_output: bool = Form(False),
) -> Dict[str, str]:
    """Upload a script and queue execution."""
    if not file.filename.endswith(('.py', '.pyw')):
        raise HTTPException(status_code=400, detail="Only Python files are allowed")

    # Ensure upload directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse args (comma separated string)
    arg_list = [a.strip() for a in args.split(',') if a.strip()]

    try:
        env_vars_dict = json.loads(env_vars)
    except json.JSONDecodeError:
        env_vars_dict = {}

    payload = RunRequest(
        script_path=str(file_path.resolve()),
        args=arg_list,
        timeout=timeout,
        log_level=log_level,
        retry_on_failure=retry_on_failure,
        env_vars=env_vars_dict,
        working_dir=working_dir,
        stream_output=stream_output,
    )

    payload = _validate_payload(payload)
    return _queue_run(payload, background_tasks)


@app.get("/api/runs")
def list_runs(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of runs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status: Optional[str] = Query(None, description="Optional status filter"),
) -> List[RunRecord]:
    """Return a summary of recent runs (newest first)."""

    return RUN_STORE.list(limit=limit, offset=offset, status=status)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> RunRecord:
    """Return details for a specific run."""

    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    return record


@app.post("/api/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> Dict[str, str]:
    handle = RUN_HANDLES.get(run_id)
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.status in {"completed", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Run already finished")
    if handle:
        handle["cancel_event"].set()
        runner: Optional[ScriptRunner] = handle.get("runner")
        if runner:
            runner.stop()
    finished_at = datetime.utcnow()
    updated = RunRecord(
        id=record.id,
        status="cancelled",
        started_at=record.started_at,
        finished_at=finished_at,
        request=record.request,
        result=record.result,
        error="Run cancelled by user",
        correlation_id=record.correlation_id,
        run_status=record.run_status,
        error_summary=record.error_summary,
    )
    with RUNS_LOCK:
        RUNS[run_id] = updated
    RUN_STORE.upsert(updated)
    return {"run_id": run_id, "status": "cancelled"}


@app.post("/api/runs/{run_id}/stop")
def stop_run(run_id: str) -> Dict[str, str]:
    """Send a graceful stop signal to the running script process.

    Sets the runner's internal stop event (watchdog picks it up) and
    terminates the process tree.  Use this for a clean, user-triggered
    interruption.  If the run is already finished, returns 409.
    """
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Run is not active")

    handle = RUN_HANDLES.get(run_id)
    stopped = False
    if handle:
        runner: Optional[ScriptRunner] = handle.get("runner")
        if runner:
            stopped = runner.stop()
        else:
            handle["cancel_event"].set()

    return {"run_id": run_id, "stopped": stopped}


@app.post("/api/runs/{run_id}/kill")
def kill_run(run_id: str) -> Dict[str, str]:
    """Forcefully kill the running script and all child processes.

    Unlike ``/stop``, this does not set the stop event first; it
    immediately delivers SIGKILL to the entire process group.
    """
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")
    if record.status not in {"queued", "running"}:
        raise HTTPException(status_code=409, detail="Run is not active")

    handle = RUN_HANDLES.get(run_id)
    killed = False
    if handle:
        runner: Optional[ScriptRunner] = handle.get("runner")
        if runner:
            killed = runner.kill()
        else:
            handle["cancel_event"].set()

    return {"run_id": run_id, "killed": killed}


@app.post("/api/runs/{run_id}/restart", status_code=202)
def restart_run(run_id: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Stop the current run (if active) and queue a fresh execution with the same parameters.

    The original run record is marked as ``cancelled`` (if still active) and
    a brand-new run record is created with the same ``RunRequest``.
    """
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")

    # Stop the existing run if still active
    if record.status in {"queued", "running"}:
        handle = RUN_HANDLES.get(run_id)
        if handle:
            handle["cancel_event"].set()
            runner: Optional[ScriptRunner] = handle.get("runner")
            if runner:
                runner.stop()
        finished_at = datetime.utcnow()
        cancelled = RunRecord(
            id=record.id,
            status="cancelled",
            started_at=record.started_at,
            finished_at=finished_at,
            request=record.request,
            result=record.result,
            error="Cancelled by restart",
            correlation_id=record.correlation_id,
            run_status=record.run_status,
            error_summary=record.error_summary,
        )
        with RUNS_LOCK:
            RUNS[run_id] = cancelled
        RUN_STORE.upsert(cancelled)

    # Queue a new run with the same payload
    return _queue_run(record.request, background_tasks)


@app.get("/api/runs/{run_id}/events")
def get_run_events(run_id: str) -> List[Dict[str, Any]]:
    """Return the structured execution events recorded by StructuredLogger for a run.

    Events are stored on the ``ScriptRunner.structured_logger`` while the job
    is running.  Once the job finishes the events are embedded in the result
    metrics (``result.metrics.events``) if available.  Returns an empty list
    if the run is not found or has no events.
    """
    # Check in-memory handle first (for live/active runs)
    handle = RUN_HANDLES.get(run_id)
    if handle:
        runner: Optional[ScriptRunner] = handle.get("runner")
        if runner:
            return runner.structured_logger.get_logs()

    # For completed runs, events may be embedded in the stored result
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if not record:
        record = RUN_STORE.get(run_id)
    if not record:
        raise HTTPException(status_code=404, detail="Run not found")

    if record.result and isinstance(record.result.get("metrics"), dict):
        return record.result["metrics"].get("events", [])

    return []


@app.get("/api/runs/{run_id}/logs")
def get_run_logs(run_id: str) -> StreamingResponse:
    logs = RUN_STORE.get_logs(run_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="Run not found")

    def stream() -> Any:
        yield logs.get("stdout") or ""
        if logs.get("stderr"):
            yield "\n--- STDERR ---\n" + logs.get("stderr")

    return StreamingResponse(stream(), media_type="text/plain")


def _load_dashboard_html() -> str:
    dashboard_path = Path(__file__).with_name("static") / "index.html"
    if not dashboard_path.exists():
        raise FileNotFoundError("Dashboard asset missing")
    return dashboard_path.read_text(encoding="utf-8")


@app.get("/", response_class=HTMLResponse)
def dashboard_page() -> HTMLResponse:
    """Serve the lightweight dashboard that drives the API."""

    html = _load_dashboard_html()
    return HTMLResponse(content=html)


app.mount("/static", StaticFiles(directory=Path(__file__).with_name("static")), name="static")


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser(description="Start the Script Runner Web API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    args = parser.parse_args()

    uvicorn.run(
        "WEBAPI.api:app",
        host=args.host,
        port=args.port,
        reload=False,
    )

