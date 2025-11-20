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


class RunRecord(BaseModel):
    """Stored representation of a running or completed job."""

    id: str
    status: str
    started_at: datetime
    finished_at: Optional[datetime]
    request: RunRequest
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


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
                    stderr TEXT
                )
                """
            )
            conn.commit()

    def upsert(self, record: RunRecord) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, status, started_at, finished_at, request_json, result_json, error, stdout, stderr)
                VALUES (:id, :status, :started_at, :finished_at, :request_json, :result_json, :error, :stdout, :stderr)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    request_json=excluded.request_json,
                    result_json=excluded.result_json,
                    error=excluded.error,
                    stdout=excluded.stdout,
                    stderr=excluded.stderr
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
        return RunRecord(
            id=row["id"],
            status=row["status"],
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            request=RunRequest.parse_raw(row["request_json"]),
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error=row["error"],
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


app = FastAPI(title="Script Runner Web API", version="1.1.0")

RUNS: Dict[str, RunRecord] = {}
RUNS_LOCK = threading.Lock()
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
        except:
            pass
    return {"deleted": count}


def _execute_run(run_id: str, payload: RunRequest, cancel_event: threading.Event) -> None:
    """Worker that executes the script and updates the run registry."""

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

    json_output_path = UPLOAD_DIR / f"{run_id}_metrics.json.gz"
    stdout_path = UPLOAD_DIR / f"{run_id}.stdout"
    stderr_path = UPLOAD_DIR / f"{run_id}.stderr"

    try:
        # Build command to run runner.py
        cmd = [sys.executable, "-u", str(PROJECT_ROOT / "runner.py")]
        
        if payload.timeout:
            cmd.extend(["--timeout", str(payload.timeout)])
        
        cmd.extend(["--log-level", payload.log_level])
        
        if payload.history_db:
            cmd.extend(["--history-db", payload.history_db])
            
        if not payload.enable_history:
            cmd.append("--disable-history")
            
        if payload.retry_on_failure:
            cmd.extend(["--retry", "3"])

        # Use JSON output to capture metrics
        cmd.extend(["--json-output", str(json_output_path)])

        # Script and args
        cmd.append(payload.script_path)
        cmd.extend(payload.args)

        if cancel_event.is_set():
            raise RuntimeError("Run cancelled before start")

        # Prepare environment
        run_env = os.environ.copy()
        run_env.update(payload.env_vars)

        with open(stdout_path, "w") as f_out, open(stderr_path, "w") as f_err:
            process = subprocess.Popen(
                cmd,
                stdout=f_out,
                stderr=f_err,
                text=True,
                cwd=PROJECT_ROOT,
                env=run_env
            )
            
            RUN_HANDLES[run_id]["process"] = process

            # Wait for completion or cancellation
            while process.poll() is None:
                if cancel_event.is_set():
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise RuntimeError("Run cancelled by user")
                threading.Event().wait(0.1) # Sleep briefly

        stdout = ""
        stderr = ""
        if stdout_path.exists():
            stdout = stdout_path.read_text(errors="replace")
        if stderr_path.exists():
            stderr = stderr_path.read_text(errors="replace")

        returncode = process.returncode

        # Read metrics from JSON output
        metrics = {}
        if json_output_path.exists():
            try:
                with gzip.open(json_output_path, 'rt') as f:
                    metrics = json.load(f)
                json_output_path.unlink()
            except Exception as e:
                print(f"Failed to read metrics: {e}")

        result = {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
            "metrics": metrics
        }

        if cancel_event.is_set():
            status = "cancelled"
            error = "Run cancelled by user"
        else:
            status = "completed" if returncode == 0 else "failed"
            error = None
            
        finished_at = datetime.utcnow()
        record = RunRecord(
            id=run_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            request=payload,
            result=result,
            error=error,
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
        for p in [json_output_path, stdout_path, stderr_path]:
            if p.exists():
                try:
                    p.unlink()
                except:
                    pass


def _validate_script_path(path_str: str) -> Path:
    candidate = Path(path_str).expanduser().resolve()
    if not candidate.is_file():
        raise HTTPException(status_code=400, detail="Script path must point to an existing file")
    try:
        candidate.relative_to(ALLOWED_SCRIPT_ROOT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Script must reside within the allowed root") from exc
    if candidate.suffix not in {".py", ".pyw"}:
        raise HTTPException(status_code=400, detail="Only Python files are allowed")
    return candidate


def _validate_payload(payload: RunRequest) -> RunRequest:
    _validate_script_path(payload.script_path)
    if payload.timeout is not None and payload.timeout <= 0:
        raise HTTPException(status_code=400, detail="Timeout must be a positive integer")
    if len(payload.args) > 50:
        raise HTTPException(status_code=400, detail="Too many arguments supplied")
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
    RUN_HANDLES[run_id] = {"cancel_event": cancel_event, "process": None}
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
        env_vars=env_vars_dict
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
        process = handle.get("process")
        if process:
            process.terminate()
    finished_at = datetime.utcnow()
    updated = RunRecord(
        id=record.id,
        status="cancelled",
        started_at=record.started_at,
        finished_at=finished_at,
        request=record.request,
        result=record.result,
        error="Run cancelled by user",
    )
    with RUNS_LOCK:
        RUNS[run_id] = updated
    RUN_STORE.upsert(updated)
    return {"run_id": run_id, "status": "cancelled"}


@app.get("/api/runs/{run_id}/logs")
def get_run_logs(run_id: str) -> StreamingResponse:
    # Check for live log files first
    stdout_path = UPLOAD_DIR / f"{run_id}.stdout"
    stderr_path = UPLOAD_DIR / f"{run_id}.stderr"
    
    if stdout_path.exists() or stderr_path.exists():
        def stream_live() -> Any:
            if stdout_path.exists():
                yield stdout_path.read_text(errors="replace")
            if stderr_path.exists():
                err = stderr_path.read_text(errors="replace")
                if err:
                    yield "\n--- STDERR ---\n" + err
        return StreamingResponse(stream_live(), media_type="text/plain")

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
