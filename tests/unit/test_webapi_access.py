"""Boundary checks exercise requests before a script can be queued."""
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "WEBAPI"))
import api


def test_remote_key_is_required_before_parsing_payload(monkeypatch):
    monkeypatch.setenv("WEBAPI_API_KEY", "test-credential")
    client = TestClient(api.app, client=("127.0.0.1", 50000), base_url="http://localhost")
    assert client.post("/api/run", json={}).status_code == 401
    assert client.post("/api/run", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/api/run", json={}, headers={"Authorization": "Bearer test-credential"}).status_code == 422
    assert client.get("/api/health").status_code == 200


def test_cross_site_form_upload_and_reads_are_blocked(monkeypatch):
    monkeypatch.delenv("WEBAPI_API_KEY", raising=False)
    client = TestClient(api.app, client=("127.0.0.1", 50000), base_url="http://localhost")
    assert client.post("/api/run/upload", headers={"Origin": "https://untrusted.example"}, data={}).status_code == 403
    assert client.get("/api/runs", headers={"Origin": "null"}).status_code == 403
    assert client.get("/api/health", headers={"Origin": "http://localhost"}).status_code == 200


def test_remote_requests_fail_closed_without_a_key(monkeypatch):
    monkeypatch.delenv("WEBAPI_API_KEY", raising=False)
    client = TestClient(api.app, client=("203.0.113.9", 50000), base_url="http://localhost")
    assert client.post("/api/run", json={}).status_code == 503
    assert client.get("/api/health").status_code == 200


def test_rebound_browser_host_cannot_reach_local_execution(monkeypatch):
    monkeypatch.delenv("WEBAPI_API_KEY", raising=False)
    client = TestClient(api.app, client=("127.0.0.1", 50000), base_url="http://rebound.example")
    assert client.post("/api/run", json={}, headers={"Origin": "http://rebound.example"}).status_code == 403
