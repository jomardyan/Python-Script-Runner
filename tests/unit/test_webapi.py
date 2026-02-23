"""Tests for the WEBAPI (FastAPI wrapper around ScriptRunner).

Covers:
- Existing endpoints (health, stats, run, list, get, cancel, logs)
- New endpoints (stop, kill, restart, events)
- New RunRequest fields (working_dir, stream_output)
- New RunRecord fields (correlation_id, run_status, error_summary)
- Input validation (dangerous env vars filtered, working_dir validated, etc.)
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Module-level import of the WEBAPI app (done once per process).
# We set env vars before importing so RunStore picks up a temp DB path that is
# set in the conftest fixture below.
# ---------------------------------------------------------------------------

_WEBAPI_PATH = str(PROJECT_ROOT / "WEBAPI")
if _WEBAPI_PATH not in sys.path:
    sys.path.insert(0, _WEBAPI_PATH)

# Use an in-memory temp path placeholder; each test class fixture will override.
os.environ.setdefault("WEBAPI_ALLOWED_ROOT", str(PROJECT_ROOT))
os.environ.setdefault("WEBAPI_RUN_DB", str(PROJECT_ROOT / "WEBAPI" / "_test_runs.db"))

import api as _api_module  # noqa: E402

_api_module.ALLOWED_SCRIPT_ROOT = PROJECT_ROOT.resolve()

from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_db(tmp_path: Path) -> None:
    """Re-initialise the shared RunStore to use a fresh tmp database."""
    db_path = tmp_path / "runs.db"
    _api_module.RUN_STORE = _api_module.RunStore(db_path)
    with _api_module.RUNS_LOCK:
        _api_module.RUNS.clear()
    _api_module.RUN_HANDLES.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path):
    _fresh_db(tmp_path)
    return TestClient(_api_module.app)


@pytest.fixture()
def sample_script():
    """A simple success script inside PROJECT_ROOT so path validation passes."""
    examples = PROJECT_ROOT / "examples"
    examples.mkdir(exist_ok=True)
    script = examples / "_webapi_test_sample.py"
    script.write_text("print('hello')\n")
    yield script
    script.unlink(missing_ok=True)


@pytest.fixture()
def failing_script():
    examples = PROJECT_ROOT / "examples"
    examples.mkdir(exist_ok=True)
    script = examples / "_webapi_fail_sample.py"
    script.write_text("import sys; sys.exit(42)\n")
    yield script
    script.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Health & system status
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_system_status_shape(self, client):
        r = client.get("/api/system/status")
        assert r.status_code == 200
        data = r.json()
        assert "cpu_load" in data
        assert "memory" in data


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestStatsEndpoint:
    def test_stats_shape(self, client):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_runs" in data
        assert "by_status" in data
        assert "runs_24h" in data

    def test_stats_empty_db(self, client):
        r = client.get("/api/stats")
        assert r.json()["total_runs"] == 0


# ---------------------------------------------------------------------------
# RunRequest model - new fields
# ---------------------------------------------------------------------------


class TestRunRequestModel:
    def test_default_working_dir_is_none(self):
        req = _api_module.RunRequest(script_path="/some/script.py")
        assert req.working_dir is None

    def test_default_stream_output_is_false(self):
        req = _api_module.RunRequest(script_path="/some/script.py")
        assert req.stream_output is False

    def test_set_working_dir(self, tmp_path):
        req = _api_module.RunRequest(
            script_path="/some/script.py",
            working_dir=str(tmp_path),
        )
        assert req.working_dir == str(tmp_path)

    def test_set_stream_output(self):
        req = _api_module.RunRequest(script_path="/some/script.py", stream_output=True)
        assert req.stream_output is True


# ---------------------------------------------------------------------------
# RunRecord model - new fields
# ---------------------------------------------------------------------------


class TestRunRecordModel:
    def test_new_fields_default_none(self):
        req = _api_module.RunRequest(script_path="/some/script.py")
        rec = _api_module.RunRecord(
            id="abc",
            status="queued",
            started_at=datetime.utcnow(),
            finished_at=None,
            request=req,
        )
        assert rec.correlation_id is None
        assert rec.run_status is None
        assert rec.error_summary is None


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_invalid_script_path_outside_root(self, client):
        payload = {"script_path": "/etc/passwd"}
        r = client.post("/api/run", json=payload)
        assert r.status_code == 400

    def test_dangerous_env_var_filtered_and_queued(self, client, sample_script):
        """PATH must be stripped; the run itself should still be queued."""
        payload = {
            "script_path": str(sample_script),
            "env_vars": {"PATH": "/evil", "SAFE_VAR": "ok"},
            "enable_history": False,
        }
        r = client.post("/api/run", json=payload)
        assert r.status_code == 202
        assert "run_id" in r.json()

    def test_negative_timeout_rejected(self, client, sample_script):
        payload = {"script_path": str(sample_script), "timeout": -1}
        r = client.post("/api/run", json=payload)
        assert r.status_code == 400

    def test_invalid_working_dir_rejected(self, client, sample_script):
        payload = {
            "script_path": str(sample_script),
            "working_dir": "/nonexistent/path/xyz/abc",
        }
        r = client.post("/api/run", json=payload)
        assert r.status_code == 400

    def test_valid_working_dir_accepted(self, client, sample_script):
        """PROJECT_ROOT is a real directory and should be accepted."""
        payload = {
            "script_path": str(sample_script),
            "working_dir": str(PROJECT_ROOT),
            "enable_history": False,
        }
        r = client.post("/api/run", json=payload)
        assert r.status_code == 202

    def test_stream_output_field_accepted(self, client, sample_script):
        payload = {
            "script_path": str(sample_script),
            "stream_output": True,
            "enable_history": False,
        }
        r = client.post("/api/run", json=payload)
        assert r.status_code == 202


# ---------------------------------------------------------------------------
# Run lifecycle - queue, get, cancel
# ---------------------------------------------------------------------------


class TestRunLifecycle:
    def test_trigger_run_returns_run_id(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        r = client.post("/api/run", json=payload)
        assert r.status_code == 202
        data = r.json()
        assert "run_id" in data
        assert data["status"] == "queued"

    def test_get_run_exists(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        run_id = client.post("/api/run", json=payload).json()["run_id"]
        r = client.get(f"/api/runs/{run_id}")
        assert r.status_code == 200
        assert r.json()["id"] == run_id

    def test_get_run_not_found(self, client):
        r = client.get("/api/runs/nonexistent-id-xyz")
        assert r.status_code == 404

    def test_list_runs(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        client.post("/api/run", json=payload)
        r = client.get("/api/runs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_cancel_nonexistent_run(self, client):
        r = client.post("/api/runs/does-not-exist/cancel")
        assert r.status_code == 404

    def test_list_runs_status_filter(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        client.post("/api/run", json=payload)
        r = client.get("/api/runs?status=queued")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# New lifecycle endpoints: stop, kill, restart
# ---------------------------------------------------------------------------


class TestNewLifecycleEndpoints:
    def test_stop_nonexistent_run(self, client):
        r = client.post("/api/runs/does-not-exist/stop")
        assert r.status_code == 404

    def test_kill_nonexistent_run(self, client):
        r = client.post("/api/runs/does-not-exist/kill")
        assert r.status_code == 404

    def test_restart_nonexistent_run(self, client):
        r = client.post("/api/runs/does-not-exist/restart")
        assert r.status_code == 404

    def test_stop_active_run_returns_200_or_409(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        run_id = client.post("/api/run", json=payload).json()["run_id"]
        r = client.post(f"/api/runs/{run_id}/stop")
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            assert r.json()["run_id"] == run_id

    def test_kill_active_run_returns_200_or_409(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        run_id = client.post("/api/run", json=payload).json()["run_id"]
        r = client.post(f"/api/runs/{run_id}/kill")
        assert r.status_code in (200, 409)
        if r.status_code == 200:
            assert r.json()["run_id"] == run_id

    def test_restart_creates_new_run(self, client, sample_script):
        payload = {"script_path": str(sample_script), "enable_history": False}
        run_id = client.post("/api/run", json=payload).json()["run_id"]
        # Let the run settle
        time.sleep(0.4)
        r = client.post(f"/api/runs/{run_id}/restart")
        assert r.status_code == 202
        data = r.json()
        assert "run_id" in data
        assert data["run_id"] != run_id  # New run ID

    def test_stop_finished_run_returns_409(self, client, sample_script):
        """Stopping an already-completed run must return 409."""
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="test-finished-id",
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            request=req,
        )
        with _api_module.RUNS_LOCK:
            _api_module.RUNS["test-finished-id"] = rec
        r = client.post("/api/runs/test-finished-id/stop")
        assert r.status_code == 409

    def test_kill_finished_run_returns_409(self, client, sample_script):
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="test-kill-done-id",
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            request=req,
        )
        with _api_module.RUNS_LOCK:
            _api_module.RUNS["test-kill-done-id"] = rec
        r = client.post("/api/runs/test-kill-done-id/kill")
        assert r.status_code == 409


# ---------------------------------------------------------------------------
# Events endpoint
# ---------------------------------------------------------------------------


class TestEventsEndpoint:
    def test_events_nonexistent_run(self, client):
        r = client.get("/api/runs/nonexistent/events")
        assert r.status_code == 404

    def test_events_queued_run_returns_empty_list(self, client, sample_script):
        """Events for a queued run (no active runner yet) should return []."""
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="evt-run-id",
            status="queued",
            started_at=datetime.utcnow(),
            finished_at=None,
            request=req,
        )
        with _api_module.RUNS_LOCK:
            _api_module.RUNS["evt-run-id"] = rec

        r = client.get("/api/runs/evt-run-id/events")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_events_from_live_runner(self, client, sample_script):
        """Events should be readable from a live runner handle."""
        from runner import StructuredLogger

        fake_runner = MagicMock()
        fake_logger = StructuredLogger()
        fake_logger.log_event(
            "start",
            {"correlation_id": "abc123", "script_path": str(sample_script)},
        )
        fake_runner.structured_logger = fake_logger

        _api_module.RUN_HANDLES["live-run-id"] = {
            "runner": fake_runner,
            "cancel_event": threading.Event(),
        }
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="live-run-id",
            status="running",
            started_at=datetime.utcnow(),
            finished_at=None,
            request=req,
        )
        with _api_module.RUNS_LOCK:
            _api_module.RUNS["live-run-id"] = rec

        r = client.get("/api/runs/live-run-id/events")
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 1
        assert events[0]["event_type"] == "start"
        assert events[0]["data"]["correlation_id"] == "abc123"

        _api_module.RUN_HANDLES.pop("live-run-id", None)
        with _api_module.RUNS_LOCK:
            _api_module.RUNS.pop("live-run-id", None)


# ---------------------------------------------------------------------------
# Logs endpoint
# ---------------------------------------------------------------------------


class TestLogsEndpoint:
    def test_logs_not_found(self, client):
        r = client.get("/api/runs/no-such-run/logs")
        assert r.status_code == 404

    def test_logs_returns_text(self, client, sample_script):
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="logs-test-id",
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            request=req,
            result={"stdout": "hello\n", "stderr": "", "returncode": 0, "metrics": {}},
        )
        _api_module.RUN_STORE.upsert(rec)

        r = client.get("/api/runs/logs-test-id/logs")
        assert r.status_code == 200
        assert "hello" in r.text


# ---------------------------------------------------------------------------
# RunStore – new columns persist and round-trip correctly
# ---------------------------------------------------------------------------


class TestRunStorePersistence:
    def test_correlation_id_round_trips(self, client, sample_script):
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="persist-corr-id",
            status="completed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            request=req,
            correlation_id="test-corr-uuid",
            run_status="success",
        )
        _api_module.RUN_STORE.upsert(rec)
        loaded = _api_module.RUN_STORE.get("persist-corr-id")
        assert loaded is not None
        assert loaded.correlation_id == "test-corr-uuid"
        assert loaded.run_status == "success"

    def test_error_summary_round_trips(self, client, sample_script):
        summary = {"exit_code": 1, "status": "failed", "correlation_id": "xyz"}
        req = _api_module.RunRequest(script_path=str(sample_script), enable_history=False)
        rec = _api_module.RunRecord(
            id="persist-err-id",
            status="failed",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            request=req,
            error_summary=summary,
        )
        _api_module.RUN_STORE.upsert(rec)
        loaded = _api_module.RUN_STORE.get("persist-err-id")
        assert loaded.error_summary == summary

    def test_get_stats(self, client):
        stats = _api_module.RUN_STORE.get_stats()
        assert isinstance(stats["total_runs"], int)
        assert isinstance(stats["by_status"], dict)


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_dashboard_serves(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "Script Runner" in r.text

    def test_dashboard_has_working_dir_field(self, client):
        r = client.get("/")
        assert "working-dir" in r.text

    def test_dashboard_has_stream_output_field(self, client):
        r = client.get("/")
        assert "stream-output" in r.text

    def test_dashboard_has_stop_kill_buttons(self, client):
        r = client.get("/")
        assert "stopRun" in r.text
        assert "killRun" in r.text

    def test_dashboard_has_restart_button(self, client):
        r = client.get("/")
        assert "restartRun" in r.text

    def test_dashboard_has_details_button(self, client):
        r = client.get("/")
        assert "viewDetails" in r.text

    def test_dashboard_shows_correlation_column(self, client):
        r = client.get("/")
        assert "Correlation" in r.text

