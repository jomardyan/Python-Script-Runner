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


# ---------------------------------------------------------------------------
# Script Library – catalog of indexed scripts (Script-Manager features)
# ---------------------------------------------------------------------------

# Extension → language mapping
_EXT_LANG: Dict[str, str] = {
    ".py": "Python", ".pyw": "Python",
    ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".sh": "Bash", ".bash": "Bash",
    ".bat": "Batch", ".cmd": "Batch",
    ".sql": "SQL",
    ".js": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript",
    ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON",
    ".tf": "Terraform",
    ".rb": "Ruby",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
}

_SCRIPT_STATUSES = frozenset({"draft", "active", "deprecated", "archived"})


class ScriptLibrary:
    """SQLite-backed catalog of indexed script files (Script-Manager features).

    Tables co-located in the same DB as ``RunStore`` (RUN_DB_PATH) so the
    whole dashboard uses a single file.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self._scan_status: Dict[int, Dict[str, Any]] = {}  # in-memory scan progress
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _ensure_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS lib_folder_roots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    recursive INTEGER DEFAULT 1,
                    include_patterns TEXT DEFAULT '',
                    exclude_patterns TEXT DEFAULT '',
                    last_scan_at TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS lib_scripts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_id INTEGER NOT NULL REFERENCES lib_folder_roots(id) ON DELETE CASCADE,
                    path TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    extension TEXT NOT NULL,
                    language TEXT,
                    size INTEGER DEFAULT 0,
                    mtime TEXT,
                    line_count INTEGER DEFAULT 0,
                    missing_flag INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_lib_scripts_root ON lib_scripts(root_id);
                CREATE INDEX IF NOT EXISTS idx_lib_scripts_lang ON lib_scripts(language);

                CREATE TABLE IF NOT EXISTS lib_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT DEFAULT '#6366f1',
                    created_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS lib_script_tags (
                    script_id INTEGER NOT NULL REFERENCES lib_scripts(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES lib_tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (script_id, tag_id)
                );

                CREATE TABLE IF NOT EXISTS lib_script_status (
                    script_id INTEGER PRIMARY KEY REFERENCES lib_scripts(id) ON DELETE CASCADE,
                    status TEXT DEFAULT 'active',
                    owner TEXT,
                    environment TEXT,
                    notes TEXT,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS lib_scan_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    root_id INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    status TEXT DEFAULT 'running',
                    new_count INTEGER DEFAULT 0,
                    updated_count INTEGER DEFAULT 0,
                    deleted_count INTEGER DEFAULT 0,
                    error_message TEXT
                );
            """)
            conn.commit()

    # ---- Folder Roots ----

    def list_folder_roots(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM lib_folder_roots ORDER BY name"
            ).fetchall()
        return [dict(r) for r in rows]

    def create_folder_root(self, path: str, name: str, recursive: bool = True,
                           include_patterns: str = "", exclude_patterns: str = "") -> Dict[str, Any]:
        abs_path = str(Path(path).resolve())
        if not Path(abs_path).is_dir():
            raise ValueError(f"Path does not exist or is not a directory: {abs_path}")
        with self._lock, self._connect() as conn:
            try:
                cursor = conn.execute(
                    """INSERT INTO lib_folder_roots (path, name, recursive, include_patterns, exclude_patterns)
                       VALUES (?, ?, ?, ?, ?)""",
                    (abs_path, name, int(recursive), include_patterns, exclude_patterns),
                )
                conn.commit()
                root_id = cursor.lastrowid
            except sqlite3.IntegrityError as exc:
                raise ValueError("Folder root with this path already exists") from exc
        return self._get_folder_root(root_id)

    def _get_folder_root(self, root_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lib_folder_roots WHERE id = ?", (root_id,)).fetchone()
        if not row:
            raise KeyError(f"Folder root {root_id} not found")
        return dict(row)

    def get_folder_root(self, root_id: int) -> Optional[Dict[str, Any]]:
        try:
            return self._get_folder_root(root_id)
        except KeyError:
            return None

    def delete_folder_root(self, root_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM lib_folder_roots WHERE id = ?", (root_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ---- Scanning ----

    def scan_folder_root(self, root_id: int) -> int:
        """Kick off a background scan and return scan event ID."""
        root = self.get_folder_root(root_id)
        if not root:
            raise KeyError(f"Folder root {root_id} not found")
        started_at = datetime.utcnow().isoformat()
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO lib_scan_events (root_id, started_at, status) VALUES (?, ?, 'running')",
                (root_id, started_at),
            )
            conn.commit()
            scan_id = cursor.lastrowid
        self._scan_status[scan_id] = {"status": "running", "progress": 0}
        t = threading.Thread(target=self._do_scan, args=(root, scan_id), daemon=True)
        t.start()
        return scan_id

    def _do_scan(self, root: Dict[str, Any], scan_id: int) -> None:
        root_id = root["id"]
        root_path = Path(root["path"])
        recursive: bool = bool(root.get("recursive", 1))
        include_raw: str = root.get("include_patterns", "") or ""
        exclude_raw: str = root.get("exclude_patterns", "") or ""
        include_exts = {p.strip().lower() for p in include_raw.split(",") if p.strip()} if include_raw else set()
        exclude_patterns = [p.strip() for p in exclude_raw.split(",") if p.strip()]

        new_count = updated_count = deleted_count = 0
        try:
            walker = root_path.rglob("*") if recursive else root_path.glob("*")
            scanned_paths: set = set()

            for fpath in walker:
                if not fpath.is_file():
                    continue
                ext = fpath.suffix.lower()
                if include_exts and ext not in include_exts:
                    continue
                if any(fpath.match(pat) for pat in exclude_patterns):
                    continue
                # Only accepted extensions (Python files must always be indexable)
                if ext not in _EXT_LANG and ext not in {".py", ".pyw"}:
                    continue

                lang = _EXT_LANG.get(ext)
                try:
                    stat = fpath.stat()
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    line_count = 0
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                            line_count = sum(1 for _ in f)
                    except OSError:
                        pass
                except OSError:
                    continue

                abs_str = str(fpath.resolve())
                scanned_paths.add(abs_str)

                with self._lock, self._connect() as conn:
                    existing = conn.execute(
                        "SELECT id, mtime FROM lib_scripts WHERE path = ?", (abs_str,)
                    ).fetchone()
                    if existing:
                        if existing["mtime"] != mtime:
                            conn.execute(
                                """UPDATE lib_scripts SET name=?, extension=?, language=?, size=?,
                                   mtime=?, line_count=?, missing_flag=0, updated_at=datetime('now')
                                   WHERE id=?""",
                                (fpath.name, ext, lang, size, mtime, line_count, existing["id"]),
                            )
                            updated_count += 1
                        else:
                            conn.execute("UPDATE lib_scripts SET missing_flag=0 WHERE id=?", (existing["id"],))
                    else:
                        conn.execute(
                            """INSERT INTO lib_scripts (root_id, path, name, extension, language, size, mtime, line_count)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (root_id, abs_str, fpath.name, ext, lang, size, mtime, line_count),
                        )
                        new_count += 1
                    conn.commit()

            # Mark deleted
            with self._lock, self._connect() as conn:
                rows = conn.execute(
                    "SELECT id, path FROM lib_scripts WHERE root_id = ? AND missing_flag = 0",
                    (root_id,),
                ).fetchall()
                for row in rows:
                    if row["path"] not in scanned_paths:
                        conn.execute("UPDATE lib_scripts SET missing_flag=1 WHERE id=?", (row["id"],))
                        deleted_count += 1
                ended_at = datetime.utcnow().isoformat()
                conn.execute(
                    """UPDATE lib_scan_events SET ended_at=?, status='completed',
                       new_count=?, updated_count=?, deleted_count=? WHERE id=?""",
                    (ended_at, new_count, updated_count, deleted_count, scan_id),
                )
                conn.execute(
                    "UPDATE lib_folder_roots SET last_scan_at=? WHERE id=?",
                    (ended_at, root_id),
                )
                conn.commit()

            self._scan_status[scan_id] = {
                "status": "completed", "new": new_count,
                "updated": updated_count, "deleted": deleted_count,
            }

        except Exception as exc:
            ended_at = datetime.utcnow().isoformat()
            with self._connect() as conn:
                conn.execute(
                    "UPDATE lib_scan_events SET ended_at=?, status='failed', error_message=? WHERE id=?",
                    (ended_at, str(exc), scan_id),
                )
                conn.commit()
            self._scan_status[scan_id] = {"status": "failed", "error": str(exc)}

    def get_scan_status(self, scan_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lib_scan_events WHERE id=?", (scan_id,)).fetchone()
        return dict(row) if row else None

    # ---- Scripts ----

    def list_scripts(
        self,
        root_id: Optional[int] = None,
        language: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        conditions = ["s.missing_flag = 0"]
        params: List[Any] = []
        if root_id is not None:
            conditions.append("s.root_id = ?")
            params.append(root_id)
        if language:
            conditions.append("s.language = ?")
            params.append(language)
        if status:
            conditions.append("COALESCE(ss.status, 'active') = ?")
            params.append(status)
        if search:
            conditions.append("(s.name LIKE ? OR s.path LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            conditions.append("EXISTS(SELECT 1 FROM lib_script_tags st2 JOIN lib_tags t2 ON st2.tag_id=t2.id WHERE st2.script_id=s.id AND t2.name=?)")
            params.append(tag)

        where = " AND ".join(conditions)
        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM lib_scripts s LEFT JOIN lib_script_status ss ON s.id=ss.script_id WHERE {where}",
                params,
            ).fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"""SELECT s.*, COALESCE(ss.status,'active') as lifecycle_status,
                           ss.owner, ss.environment,
                           GROUP_CONCAT(t.name,'|') as tags
                    FROM lib_scripts s
                    LEFT JOIN lib_script_status ss ON s.id=ss.script_id
                    LEFT JOIN lib_script_tags lst ON s.id=lst.script_id
                    LEFT JOIN lib_tags t ON lst.tag_id=t.id
                    WHERE {where}
                    GROUP BY s.id
                    ORDER BY s.name ASC
                    LIMIT ? OFFSET ?""",
                params + [page_size, offset],
            ).fetchall()
        items = []
        for row in rows:
            d = dict(row)
            d["tags"] = [t for t in (d.get("tags") or "").split("|") if t]
            items.append(d)
        return {"items": items, "total": total, "page": page, "page_size": page_size,
                "total_pages": max(1, (total + page_size - 1) // page_size)}

    def get_script(self, script_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lib_scripts WHERE id=?", (script_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            ss = conn.execute("SELECT * FROM lib_script_status WHERE script_id=?", (script_id,)).fetchone()
            if ss:
                d.update(dict(ss))
            d["lifecycle_status"] = d.get("status", "active") if ss else "active"
            tags_rows = conn.execute(
                "SELECT t.id, t.name, t.color FROM lib_tags t JOIN lib_script_tags lst ON t.id=lst.tag_id WHERE lst.script_id=?",
                (script_id,),
            ).fetchall()
            d["tags"] = [dict(r) for r in tags_rows]
        return d

    def get_script_content(self, script_id: int) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT path FROM lib_scripts WHERE id=?", (script_id,)).fetchone()
        if not row:
            return None
        path = Path(row["path"])
        if not path.is_file():
            return None
        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def update_script_status(self, script_id: int, status: Optional[str] = None,
                              owner: Optional[str] = None, environment: Optional[str] = None,
                              notes: Optional[str] = None) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM lib_scripts WHERE id=?", (script_id,)).fetchone()
        if not row:
            return False
        with self._lock, self._connect() as conn:
            existing = conn.execute("SELECT script_id FROM lib_script_status WHERE script_id=?", (script_id,)).fetchone()
            if existing:
                updates = []
                vals: List[Any] = []
                if status is not None:
                    updates.append("status=?"); vals.append(status)
                if owner is not None:
                    updates.append("owner=?"); vals.append(owner)
                if environment is not None:
                    updates.append("environment=?"); vals.append(environment)
                if notes is not None:
                    updates.append("notes=?"); vals.append(notes)
                if updates:
                    updates.append("updated_at=datetime('now')")
                    vals.append(script_id)
                    conn.execute(f"UPDATE lib_script_status SET {', '.join(updates)} WHERE script_id=?", vals)
            else:
                conn.execute(
                    "INSERT INTO lib_script_status (script_id, status, owner, environment, notes) VALUES (?,?,?,?,?)",
                    (script_id, status or "active", owner, environment, notes),
                )
            conn.commit()
        return True

    def get_script_notes(self, script_id: int) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT notes FROM lib_script_status WHERE script_id=?", (script_id,)).fetchone()
        return row["notes"] if row else None

    # ---- Tags ----

    def list_tags(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT t.*, COUNT(lst.script_id) as script_count
                   FROM lib_tags t LEFT JOIN lib_script_tags lst ON t.id=lst.tag_id
                   GROUP BY t.id ORDER BY t.name""",
            ).fetchall()
        return [dict(r) for r in rows]

    def create_tag(self, name: str, color: str = "#6366f1") -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            try:
                cursor = conn.execute("INSERT INTO lib_tags (name, color) VALUES (?, ?)", (name, color))
                conn.commit()
                tag_id = cursor.lastrowid
            except sqlite3.IntegrityError as exc:
                raise ValueError("Tag with this name already exists") from exc
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM lib_tags WHERE id=?", (tag_id,)).fetchone()
        return dict(row)

    def delete_tag(self, tag_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM lib_tags WHERE id=?", (tag_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_tag_to_script(self, script_id: int, tag_id: int) -> bool:
        with self._lock, self._connect() as conn:
            try:
                conn.execute("INSERT INTO lib_script_tags (script_id, tag_id) VALUES (?, ?)", (script_id, tag_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # already tagged

    def remove_tag_from_script(self, script_id: int, tag_id: int) -> bool:
        with self._lock, self._connect() as conn:
            cursor = conn.execute("DELETE FROM lib_script_tags WHERE script_id=? AND tag_id=?", (script_id, tag_id))
            conn.commit()
            return cursor.rowcount > 0

    # ---- Duplicates ----

    def list_duplicates(self) -> List[Dict[str, Any]]:
        """Return groups of scripts with identical content (same size+line_count+name heuristic)."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT name, size, line_count, COUNT(*) as count,
                          GROUP_CONCAT(path, '||') as paths,
                          GROUP_CONCAT(id, '||') as ids
                   FROM lib_scripts
                   WHERE missing_flag = 0 AND size > 0
                   GROUP BY name, size, line_count
                   HAVING count > 1
                   ORDER BY count DESC""",
            ).fetchall()
        result = []
        for row in rows:
            result.append({
                "name": row["name"],
                "size": row["size"],
                "line_count": row["line_count"],
                "count": row["count"],
                "paths": row["paths"].split("||") if row["paths"] else [],
                "ids": [int(i) for i in row["ids"].split("||")] if row["ids"] else [],
            })
        return result

    # ---- Library stats ----

    def get_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM lib_scripts WHERE missing_flag=0").fetchone()[0]
            by_lang_rows = conn.execute(
                "SELECT language, COUNT(*) FROM lib_scripts WHERE missing_flag=0 AND language IS NOT NULL GROUP BY language ORDER BY 2 DESC"
            ).fetchall()
            by_status_rows = conn.execute(
                """SELECT COALESCE(ss.status,'active'), COUNT(*)
                   FROM lib_scripts s LEFT JOIN lib_script_status ss ON s.id=ss.script_id
                   WHERE s.missing_flag=0 GROUP BY 1"""
            ).fetchall()
            total_tags = conn.execute("SELECT COUNT(*) FROM lib_tags").fetchone()[0]
            total_roots = conn.execute("SELECT COUNT(*) FROM lib_folder_roots").fetchone()[0]
        return {
            "total_scripts": total,
            "by_language": dict(by_lang_rows),
            "by_lifecycle_status": dict(by_status_rows),
            "total_tags": total_tags,
            "total_roots": total_roots,
        }


app = FastAPI(title="Script Runner Web API", version="1.4.0")

RUNS: Dict[str, RunRecord] = {}
RUNS_LOCK = threading.Lock()
# RUN_HANDLES stores: {"cancel_event": Event, "runner": ScriptRunner|None}
RUN_HANDLES: Dict[str, Dict[str, Any]] = {}
RUN_STORE = RunStore(RUN_DB_PATH)
SCRIPT_LIBRARY = ScriptLibrary(RUN_DB_PATH)

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


# ---------------------------------------------------------------------------
# Library API endpoints
# ---------------------------------------------------------------------------

# ---- Pydantic models for library ----

class FolderRootCreate(BaseModel):
    path: str = Field(..., description="Absolute or relative path to the folder root")
    name: str = Field(..., description="Display name for this folder root")
    recursive: bool = Field(True, description="Scan subdirectories recursively")
    include_patterns: str = Field("", description="Comma-separated extension patterns to include, e.g. '.py,.sh'")
    exclude_patterns: str = Field("", description="Comma-separated glob patterns to exclude")


class TagCreate(BaseModel):
    name: str = Field(..., description="Tag name")
    color: str = Field("#6366f1", description="Hex color for the tag badge")


class ScriptStatusUpdate(BaseModel):
    status: Optional[str] = Field(None, description="Lifecycle status: draft, active, deprecated, archived")
    owner: Optional[str] = Field(None, description="Owner/team responsible for this script")
    environment: Optional[str] = Field(None, description="Target environment, e.g. prod, staging")
    notes: Optional[str] = Field(None, description="Free-form notes about this script")


# ---- Folder Roots ----

@app.get("/api/library/stats")
def library_stats() -> Dict[str, Any]:
    """Return aggregate statistics for the script library."""
    return SCRIPT_LIBRARY.get_stats()


@app.get("/api/library/folder-roots")
def list_folder_roots() -> List[Dict[str, Any]]:
    """Return all registered folder roots."""
    return SCRIPT_LIBRARY.list_folder_roots()


@app.post("/api/library/folder-roots", status_code=201)
def create_folder_root(payload: FolderRootCreate) -> Dict[str, Any]:
    """Register a new folder root to be scanned."""
    try:
        root = SCRIPT_LIBRARY.create_folder_root(
            path=payload.path,
            name=payload.name,
            recursive=payload.recursive,
            include_patterns=payload.include_patterns,
            exclude_patterns=payload.exclude_patterns,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return root


@app.delete("/api/library/folder-roots/{root_id}")
def delete_folder_root(root_id: int) -> Dict[str, bool]:
    """Remove a folder root and all its indexed scripts."""
    if not SCRIPT_LIBRARY.delete_folder_root(root_id):
        raise HTTPException(status_code=404, detail="Folder root not found")
    return {"success": True}


@app.post("/api/library/folder-roots/{root_id}/scan", status_code=202)
def scan_folder_root(root_id: int, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Trigger a background scan of the folder root. Returns a scan_id to poll."""
    try:
        scan_id = SCRIPT_LIBRARY.scan_folder_root(root_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"scan_id": scan_id, "status": "running"}


@app.get("/api/library/folder-roots/{root_id}/scan/{scan_id}")
def get_scan_status(root_id: int, scan_id: int) -> Dict[str, Any]:
    """Poll the status of a scan operation."""
    result = SCRIPT_LIBRARY.get_scan_status(scan_id)
    if not result:
        raise HTTPException(status_code=404, detail="Scan not found")
    return result


# ---- Scripts ----

@app.get("/api/library/scripts")
def list_library_scripts(
    root_id: Optional[int] = Query(None),
    language: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> Dict[str, Any]:
    """List indexed scripts with optional filters."""
    return SCRIPT_LIBRARY.list_scripts(
        root_id=root_id,
        language=language,
        status=status,
        search=search,
        tag=tag,
        page=page,
        page_size=page_size,
    )


@app.get("/api/library/scripts/{script_id}")
def get_library_script(script_id: int) -> Dict[str, Any]:
    """Return full details for a single indexed script."""
    script = SCRIPT_LIBRARY.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script


@app.get("/api/library/scripts/{script_id}/content")
def get_library_script_content(script_id: int) -> Dict[str, Any]:
    """Return the raw file content of a script (UTF-8)."""
    script = SCRIPT_LIBRARY.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    content = SCRIPT_LIBRARY.get_script_content(script_id)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found on disk")
    return {"script_id": script_id, "path": script["path"], "content": content}


@app.put("/api/library/scripts/{script_id}/status")
def update_library_script_status(script_id: int, payload: ScriptStatusUpdate) -> Dict[str, str]:
    """Update lifecycle status, owner, environment, and notes for a script."""
    if payload.status is not None and payload.status not in _SCRIPT_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(_SCRIPT_STATUSES)}")
    if not SCRIPT_LIBRARY.update_script_status(
        script_id,
        status=payload.status,
        owner=payload.owner,
        environment=payload.environment,
        notes=payload.notes,
    ):
        raise HTTPException(status_code=404, detail="Script not found")
    return {"message": "Status updated"}


@app.get("/api/library/scripts/{script_id}/notes")
def get_library_script_notes(script_id: int) -> Dict[str, Any]:
    """Return the notes attached to a script."""
    script = SCRIPT_LIBRARY.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return {"script_id": script_id, "notes": SCRIPT_LIBRARY.get_script_notes(script_id)}


@app.post("/api/library/scripts/{script_id}/tags/{tag_id}")
def add_tag_to_library_script(script_id: int, tag_id: int) -> Dict[str, str]:
    """Attach a tag to a script."""
    SCRIPT_LIBRARY.add_tag_to_script(script_id, tag_id)
    return {"message": "Tag added"}


@app.delete("/api/library/scripts/{script_id}/tags/{tag_id}")
def remove_tag_from_library_script(script_id: int, tag_id: int) -> Dict[str, str]:
    """Detach a tag from a script."""
    SCRIPT_LIBRARY.remove_tag_from_script(script_id, tag_id)
    return {"message": "Tag removed"}


# ---- Tags ----

@app.get("/api/library/tags")
def list_library_tags() -> List[Dict[str, Any]]:
    """Return all tags in the library with script counts."""
    return SCRIPT_LIBRARY.list_tags()


@app.post("/api/library/tags", status_code=201)
def create_library_tag(payload: TagCreate) -> Dict[str, Any]:
    """Create a new tag."""
    try:
        return SCRIPT_LIBRARY.create_tag(payload.name, payload.color)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/library/tags/{tag_id}")
def delete_library_tag(tag_id: int) -> Dict[str, bool]:
    """Delete a tag."""
    if not SCRIPT_LIBRARY.delete_tag(tag_id):
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"success": True}


# ---- Duplicates ----

@app.get("/api/library/duplicates")
def list_library_duplicates() -> List[Dict[str, Any]]:
    """Return groups of scripts that appear to be duplicates (same name + size + line count)."""
    return SCRIPT_LIBRARY.list_duplicates()


# ---- Run from Library ----

@app.post("/api/library/scripts/{script_id}/run", status_code=202)
def run_library_script(
    script_id: int,
    background_tasks: BackgroundTasks,
    args: List[str] = Body(default_factory=list),
    timeout: Optional[int] = Body(None),
    env_vars: Dict[str, str] = Body(default_factory=dict),
    working_dir: Optional[str] = Body(None),
    stream_output: bool = Body(False),
    enable_history: bool = Body(True),
) -> Dict[str, str]:
    """Queue a run for a script from the library. Same as POST /api/run but takes a library script ID."""
    script = SCRIPT_LIBRARY.get_script(script_id)
    if not script:
        raise HTTPException(status_code=404, detail="Library script not found")

    payload = RunRequest(
        script_path=script["path"],
        args=args,
        timeout=timeout,
        env_vars=env_vars,
        working_dir=working_dir,
        stream_output=stream_output,
        enable_history=enable_history,
    )
    try:
        payload = _validate_payload(payload)
    except HTTPException:
        raise
    return _queue_run(payload, background_tasks)


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

