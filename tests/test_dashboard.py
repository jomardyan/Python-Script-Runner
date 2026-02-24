"""
Comprehensive test suite for WEBAPI Dashboard Backend
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import status

# Point to the WEBAPI directory so `api` module can be imported
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_WEBAPI_PATH = str(_PROJECT_ROOT / "WEBAPI")
if _WEBAPI_PATH not in sys.path:
    sys.path.insert(0, _WEBAPI_PATH)

# Use a temp DB for tests (override before importing api)
_TMP_TEST_DB = str(Path(tempfile.mkdtemp()) / "dashboard_test.db")
os.environ.setdefault("WEBAPI_RUN_DB", _TMP_TEST_DB)
os.environ.setdefault("WEBAPI_ALLOWED_ROOT", str(_PROJECT_ROOT))

import api as _api_module  # noqa: E402
_api_module.ALLOWED_SCRIPT_ROOT = _PROJECT_ROOT.resolve()


@pytest.fixture(scope="module")
def client():
    """Create test client for WEBAPI app."""
    return TestClient(_api_module.app)


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_ok(self, client):
        """Test health endpoint returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"


class TestSystemStatusEndpoint:
    """Test system status endpoint"""

    def test_system_status(self, client):
        """Test system status endpoint returns resource info"""
        response = client.get("/api/system/status")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cpu_load" in data
        assert "memory" in data
        assert isinstance(data["cpu_load"], list)


class TestStatsEndpoint:
    """Test aggregated run statistics endpoint"""

    def test_get_stats(self, client):
        """Test /api/stats returns aggregated run statistics"""
        response = client.get("/api/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_runs" in data
        assert "by_status" in data
        assert "runs_24h" in data
        assert isinstance(data["total_runs"], int)
        assert isinstance(data["runs_24h"], int)


class TestRunsEndpoint:
    """Test runs list and detail endpoints"""

    def test_list_runs_empty(self, client):
        """Test /api/runs returns list (may be empty for fresh DB)"""
        response = client.get("/api/runs")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_list_runs_with_limit(self, client):
        """Test /api/runs respects limit parameter"""
        response = client.get("/api/runs?limit=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_list_runs_invalid_limit(self, client):
        """Test /api/runs with invalid limit returns error"""
        response = client.get("/api/runs?limit=0")
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_get_nonexistent_run(self, client):
        """Test /api/runs/{run_id} returns 404 for unknown id"""
        response = client.get("/api/runs/nonexistent-run-id-xyz")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAnalyticsEndpoints:
    """Test analytics endpoints"""

    def test_analytics_history(self, client):
        """Test /api/analytics/history returns history data"""
        response = client.get("/api/analytics/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data

    def test_analytics_history_stats(self, client):
        """Test /api/analytics/history/stats returns stats dict"""
        response = client.get("/api/analytics/history/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

    def test_analytics_benchmarks_list(self, client):
        """Test /api/analytics/benchmarks returns benchmarks data"""
        response = client.get("/api/analytics/benchmarks")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "benchmarks" in data


class TestSchedulerEndpoints:
    """Test scheduler endpoints"""

    def test_list_tasks(self, client):
        """Test /api/scheduler/tasks returns tasks data"""
        response = client.get("/api/scheduler/tasks")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "tasks" in data

    def test_due_tasks(self, client):
        """Test /api/scheduler/due returns due tasks data"""
        response = client.get("/api/scheduler/due")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "due_tasks" in data


class TestLibraryEndpoints:
    """Test script library endpoints"""

    def test_library_stats(self, client):
        """Test /api/library/stats returns stats"""
        response = client.get("/api/library/stats")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)

    def test_library_folder_roots(self, client):
        """Test /api/library/folder-roots returns list"""
        response = client.get("/api/library/folder-roots")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_library_scripts_list(self, client):
        """Test /api/library/scripts returns paginated scripts"""
        response = client.get("/api/library/scripts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data

    def test_library_tags(self, client):
        """Test /api/library/tags returns list"""
        response = client.get("/api/library/tags")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_library_duplicates(self, client):
        """Test /api/library/duplicates returns list"""
        response = client.get("/api/library/duplicates")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_invalid_endpoint(self, client):
        """Test request to invalid endpoint returns 404"""
        response = client.get("/api/invalid_endpoint_xyz")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cancel_nonexistent_run(self, client):
        """Test cancelling non-existent run returns 404"""
        response = client.post("/api/runs/nonexistent-xyz/cancel")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_run(self, client):
        """Test deleting non-existent run returns appropriate response"""
        response = client.delete("/api/runs/nonexistent-xyz")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

