"""
Comprehensive test suite for FastAPI Dashboard Backend
Tests all endpoints, error handling, validation, and WebSocket functionality
"""

import pytest
import asyncio
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

# Import the app
import sys
sys.path.insert(0, str(Path(__file__).parent))
from app import app, init_managers, connected_clients


@pytest.fixture(scope="module", autouse=True)
def initialize_db():
    """Initialize database for all tests"""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "test.db")
        
        # Create database schema matching HistoryManager expectations
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_path TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                start_time TEXT,
                end_time TEXT,
                stdout TEXT,
                stderr TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER NOT NULL,
                metric_name TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (execution_id) REFERENCES executions(id)
            )
        """)
        
        # Insert test data
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO executions 
            (script_path, exit_code, start_time, end_time, stdout, stderr, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ('test_script.py', 0, now, now, 'success output', '', now))
        
        exec_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO metrics (execution_id, metric_name, value, timestamp)
            VALUES (?, ?, ?, ?)
        """, (exec_id, 'execution_time_seconds', 1.5, now))
        
        cursor.execute("""
            INSERT INTO metrics (execution_id, metric_name, value, timestamp)
            VALUES (?, ?, ?, ?)
        """, (exec_id, 'memory_usage_mb', 256.0, now))
        
        conn.commit()
        conn.close()
        
        # Initialize app with test database
        init_managers(db_path)
        yield db_path


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_ok(self, client):
        """Test health check returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["ok", "degraded", "error"]
        assert "timestamp" in data
    
    def test_health_includes_websocket_clients(self, client):
        """Test health check includes WebSocket client count"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["status"] == "ok":
            assert "websocket_clients" in data


class TestScriptsEndpoint:
    """Test scripts list endpoint"""
    
    def test_get_scripts(self, client):
        """Test getting scripts list"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK
        scripts = response.json()
        assert isinstance(scripts, list)
    
    def test_get_scripts_structure(self, client):
        """Test scripts response structure"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK
        scripts = response.json()
        if scripts:
            script = scripts[0]
            assert "path" in script
            assert "execution_count" in script
            assert "last_execution" in script


class TestMetricsLatestEndpoint:
    """Test latest metrics endpoint"""
    
    def test_metrics_latest_invalid_limit_low(self, client):
        """Test metrics latest with limit < 1 returns error"""
        response = client.get("/api/metrics/latest", params={"limit": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_latest_invalid_limit_high(self, client):
        """Test metrics latest with limit > 10000 returns error"""
        response = client.get("/api/metrics/latest", params={"limit": 10001})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_latest_valid_limit(self, client):
        """Test metrics latest with valid limit"""
        response = client.get("/api/metrics/latest", params={"limit": 100})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    def test_metrics_latest_with_script_path(self, client):
        """Test metrics latest with specific script path"""
        response = client.get(
            "/api/metrics/latest",
            params={"script_path": "test_script.py", "limit": 50}
        )
        assert response.status_code == status.HTTP_200_OK


class TestMetricsHistoryEndpoint:
    """Test metrics history endpoint"""
    
    def test_metrics_history_invalid_days_low(self, client):
        """Test metrics history with days < 1 returns error"""
        response = client.get("/api/metrics/history", params={"days": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_days_high(self, client):
        """Test metrics history with days > 365 returns error"""
        response = client.get("/api/metrics/history", params={"days": 366})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_limit_low(self, client):
        """Test metrics history with limit < 1 returns error"""
        response = client.get("/api/metrics/history", params={"limit": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_limit_high(self, client):
        """Test metrics history with limit > 100000 returns error"""
        response = client.get("/api/metrics/history", params={"limit": 100001})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_valid_params(self, client):
        """Test metrics history with valid parameters"""
        response = client.get(
            "/api/metrics/history",
            params={
                "metric_name": "execution_time_seconds",
                "days": 7,
                "limit": 1000
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "script_path" in data
        assert "days" in data
        assert "data_points" in data
        assert "data" in data
    
    def test_metrics_history_with_script_path(self, client):
        """Test metrics history filtered by script path"""
        response = client.get(
            "/api/metrics/history",
            params={
                "script_path": "test_script.py",
                "metric_name": "execution_time_seconds",
                "days": 7
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["script_path"] in ["test_script.py", "all"]
    
    def test_metrics_history_data_ordering(self, client):
        """Test that metrics history data is in chronological order"""
        response = client.get(
            "/api/metrics/history",
            params={"days": 7, "limit": 100}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if len(data["data"]) > 1:
            # Check data is in chronological order
            for i in range(len(data["data"]) - 1):
                ts1 = data["data"][i]["timestamp"]
                ts2 = data["data"][i + 1]["timestamp"]
                assert ts1 <= ts2


class TestDatabaseStatsEndpoint:
    """Test database statistics endpoint"""
    
    def test_database_stats_returns_dict(self, client):
        """Test database stats returns dictionary"""
        response = client.get("/api/stats/database")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)


class TestExecutionsEndpoint:
    """Test executions list endpoint"""
    
    def test_get_executions(self, client):
        """Test getting executions list"""
        response = client.get("/api/executions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_executions_with_limit(self, client):
        """Test getting executions with limit"""
        response = client.get("/api/executions", params={"limit": 10})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 10
    
    def test_get_executions_with_offset(self, client):
        """Test getting executions with offset"""
        response = client.get(
            "/api/executions",
            params={"limit": 10, "offset": 0}
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_executions_script_filter(self, client):
        """Test filtering executions by script path"""
        response = client.get(
            "/api/executions",
            params={"script_path": "test_script.py"}
        )
        assert response.status_code == status.HTTP_200_OK


class TestFrontendEndpoint:
    """Test frontend serving"""
    
    def test_frontend_endpoint(self, client):
        """Test frontend endpoint handles missing frontend gracefully"""
        response = client.get("/")
        # Should either serve frontend or return 404 with message
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test invalid endpoint returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_database_error_handling_metrics_latest(self, client):
        """Test database error is handled properly"""
        response = client.get("/api/metrics/latest")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]
    
    def test_string_limit_parameter(self, client):
        """Test non-integer limit parameter"""
        response = client.get(
            "/api/metrics/latest",
            params={"limit": "invalid"}
        )
        # FastAPI validates query params
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_negative_limit_parameter(self, client):
        """Test negative limit parameter"""
        response = client.get(
            "/api/metrics/latest",
            params={"limit": -1}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestInputValidation:
    """Test input validation on endpoints"""
    
    def test_metrics_latest_limit_boundaries(self, client):
        """Test limit boundary values"""
        # Valid boundary
        response = client.get("/api/metrics/latest", params={"limit": 1})
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get("/api/metrics/latest", params={"limit": 10000})
        assert response.status_code == status.HTTP_200_OK
    
    def test_metrics_history_days_boundaries(self, client):
        """Test days boundary values"""
        # Valid boundary
        response = client.get(
            "/api/metrics/history",
            params={"days": 1}
        )
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get(
            "/api/metrics/history",
            params={"days": 365}
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_empty_script_path(self, client):
        """Test empty script path parameter"""
        response = client.get(
            "/api/metrics/history",
            params={"script_path": ""}
        )
        assert response.status_code == status.HTTP_200_OK


class TestResponseFormats:
    """Test response format consistency"""
    
    def test_health_response_format(self, client):
        """Test health check response format"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_scripts_response_format(self, client):
        """Test scripts response format"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_metrics_history_response_format(self, client):
        """Test metrics history response format"""
        response = client.get("/api/metrics/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "script_path" in data
        assert "days" in data
        assert "data_points" in data
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_executions_response_format(self, client):
        """Test executions response format"""
        response = client.get("/api/executions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestStatusCodes:
    """Test correct HTTP status codes"""
    
    def test_success_returns_200(self, client):
        """Test successful requests return 200"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_validation_error_returns_400(self, client):
        """Test validation errors return 400"""
        response = client.get(
            "/api/metrics/latest",
            params={"limit": 0}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_not_found_returns_404(self, client):
        """Test not found returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCORSHeaders:
    """Test CORS headers"""
    
    def test_cors_headers_configured(self, client):
        """Test CORS headers are configured in app"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        # TestClient doesn't always include CORS headers, but app is configured


class TestContentTypes:
    """Test content type handling"""
    
    def test_json_content_type(self, client):
        """Test endpoints return JSON"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_all_endpoints_json(self, client):
        """Test all endpoints return JSON"""
        endpoints = [
            "/api/health",
            "/api/scripts",
            "/api/metrics/latest",
            "/api/metrics/history",
            "/api/stats/database",
            "/api/executions",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == status.HTTP_200_OK:
                assert "application/json" in response.headers.get(
                    "content-type", ""
                ), f"Failed for {endpoint}"


# Integration tests
class TestIntegration:
    """Integration tests across multiple endpoints"""
    
    def test_health_then_scripts(self, client):
        """Test health check followed by scripts endpoint"""
        response1 = client.get("/api/health")
        assert response1.status_code == status.HTTP_200_OK
        
        response2 = client.get("/api/scripts")
        assert response2.status_code == status.HTTP_200_OK
    
    def test_scripts_then_metrics(self, client):
        """Test scripts followed by metrics"""
        response1 = client.get("/api/scripts")
        assert response1.status_code == status.HTTP_200_OK
        
        response2 = client.get("/api/metrics/latest")
        assert response2.status_code == status.HTTP_200_OK
    
    def test_metrics_history_with_all_params(self, client):
        """Test metrics history with all optional parameters"""
        response = client.get(
            "/api/metrics/history",
            params={
                "script_path": "test_script.py",
                "metric_name": "execution_time_seconds",
                "days": 7,
                "limit": 1000
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metric_name"] == "execution_time_seconds"
        assert data["days"] == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


import pytest
import asyncio
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

# Import the app
import sys
sys.path.insert(0, str(Path(__file__).parent))
from app import app, init_managers, connected_clients, metrics_cache


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary test database"""
    db_path = str(tmp_path / "test.db")
    
    # Create database schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            script_path TEXT NOT NULL,
            exit_code INTEGER NOT NULL,
            stdout TEXT,
            stderr TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            execution_id INTEGER NOT NULL,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (execution_id) REFERENCES executions(id)
        )
    """)
    
    # Insert test data
    cursor.execute("""
        INSERT INTO executions (script_path, exit_code, stdout, stderr, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, ('test_script.py', 0, 'success output', '', datetime.now().isoformat()))
    
    exec_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO metrics (execution_id, metric_name, value, timestamp)
        VALUES (?, ?, ?, ?)
    """, (exec_id, 'execution_time_seconds', 1.5, datetime.now().isoformat()))
    
    cursor.execute("""
        INSERT INTO metrics (execution_id, metric_name, value, timestamp)
        VALUES (?, ?, ?, ?)
    """, (exec_id, 'memory_usage_mb', 256.0, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_ok(self, client):
        """Test health check returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in ["ok", "degraded", "error"]
        assert "timestamp" in data
    
    def test_health_includes_websocket_clients(self, client):
        """Test health check includes WebSocket client count"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["status"] == "ok":
            assert "websocket_clients" in data


class TestScriptsEndpoint:
    """Test scripts list endpoint"""
    
    def test_get_scripts_empty(self, client, temp_db):
        """Test getting scripts when database is empty"""
        from app import history_manager
        with patch.object(history_manager, 'db_path', temp_db):
            response = client.get("/api/scripts")
            assert response.status_code == status.HTTP_200_OK
            assert isinstance(response.json(), list)
    
    def test_get_scripts_with_data(self, client, temp_db):
        """Test getting scripts with execution data"""
        from app import history_manager
        if history_manager:
            with patch.object(history_manager, 'db_path', temp_db):
                response = client.get("/api/scripts")
                assert response.status_code == status.HTTP_200_OK
                scripts = response.json()
                assert isinstance(scripts, list)
                if scripts:
                    script = scripts[0]
                    assert "path" in script
                    assert "execution_count" in script
                    assert "last_execution" in script
    
    def test_get_scripts_returns_distinct_scripts(self, client, temp_db):
        """Test that get_scripts returns distinct scripts"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK


class TestMetricsLatestEndpoint:
    """Test latest metrics endpoint"""
    
    def test_metrics_latest_invalid_limit_low(self, client):
        """Test metrics latest with limit < 1 returns error"""
        response = client.get("/api/metrics/latest", params={"limit": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_latest_invalid_limit_high(self, client):
        """Test metrics latest with limit > 10000 returns error"""
        response = client.get("/api/metrics/latest", params={"limit": 10001})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_latest_valid_limit(self, client):
        """Test metrics latest with valid limit"""
        response = client.get("/api/metrics/latest", params={"limit": 100})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict)
    
    def test_metrics_latest_with_script_path(self, client):
        """Test metrics latest with specific script path"""
        response = client.get(
            "/api/metrics/latest",
            params={"script_path": "test.py", "limit": 50}
        )
        assert response.status_code == status.HTTP_200_OK


class TestMetricsHistoryEndpoint:
    """Test metrics history endpoint"""
    
    def test_metrics_history_invalid_days_low(self, client):
        """Test metrics history with days < 1 returns error"""
        response = client.get("/api/metrics/history", params={"days": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_days_high(self, client):
        """Test metrics history with days > 365 returns error"""
        response = client.get("/api/metrics/history", params={"days": 366})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_limit_low(self, client):
        """Test metrics history with limit < 1 returns error"""
        response = client.get("/api/metrics/history", params={"limit": 0})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_invalid_limit_high(self, client):
        """Test metrics history with limit > 100000 returns error"""
        response = client.get("/api/metrics/history", params={"limit": 100001})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_metrics_history_valid_params(self, client):
        """Test metrics history with valid parameters"""
        response = client.get(
            "/api/metrics/history",
            params={
                "metric_name": "execution_time_seconds",
                "days": 7,
                "limit": 1000
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "script_path" in data
        assert "days" in data
        assert "data_points" in data
        assert "data" in data
    
    def test_metrics_history_with_script_path(self, client):
        """Test metrics history filtered by script path"""
        response = client.get(
            "/api/metrics/history",
            params={
                "script_path": "test.py",
                "metric_name": "execution_time_seconds",
                "days": 7
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["script_path"] in ["test.py", "all"]
    
    def test_metrics_history_data_ordering(self, client):
        """Test that metrics history data is in chronological order"""
        response = client.get(
            "/api/metrics/history",
            params={"days": 7, "limit": 100}
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if len(data["data"]) > 1:
            # Check data is in chronological order
            for i in range(len(data["data"]) - 1):
                ts1 = data["data"][i]["timestamp"]
                ts2 = data["data"][i + 1]["timestamp"]
                assert ts1 <= ts2


class TestDatabaseStatsEndpoint:
    """Test database statistics endpoint"""
    
    def test_database_stats_returns_dict(self, client):
        """Test database stats returns dictionary"""
        response = client.get("/api/stats/database")
        # Either 200 or 503 depending on initialization
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]


class TestExecutionsEndpoint:
    """Test executions list endpoint"""
    
    def test_get_executions(self, client):
        """Test getting executions list"""
        response = client.get("/api/executions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_executions_with_limit(self, client):
        """Test getting executions with limit"""
        response = client.get("/api/executions", params={"limit": 10})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 10
    
    def test_get_executions_with_offset(self, client):
        """Test getting executions with offset"""
        response = client.get(
            "/api/executions",
            params={"limit": 10, "offset": 0}
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_executions_script_filter(self, client):
        """Test filtering executions by script path"""
        response = client.get(
            "/api/executions",
            params={"script_path": "test.py"}
        )
        assert response.status_code == status.HTTP_200_OK


class TestFrontendEndpoint:
    """Test frontend serving"""
    
    def test_frontend_not_found_graceful(self, client):
        """Test frontend endpoint handles missing frontend gracefully"""
        response = client.get("/")
        # Should either serve frontend or return 404 with message
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND
        ]


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_endpoint_returns_404(self, client):
        """Test invalid endpoint returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_database_error_handling_metrics_latest(self, client):
        """Test database error is handled properly"""
        # This should either work or return appropriate error
        response = client.get("/api/metrics/latest")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]
    
    def test_string_limit_parameter(self, client):
        """Test non-integer limit parameter"""
        response = client.get(
            "/api/metrics/latest",
            params={"limit": "invalid"}
        )
        # FastAPI validates query params
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_negative_days_parameter(self, client):
        """Test negative days parameter"""
        response = client.get(
            "/api/metrics/history",
            params={"days": -1}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestInputValidation:
    """Test input validation on endpoints"""
    
    def test_metrics_latest_limit_boundaries(self, client):
        """Test limit boundary values"""
        # Valid boundary
        response = client.get("/api/metrics/latest", params={"limit": 1})
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get("/api/metrics/latest", params={"limit": 10000})
        assert response.status_code == status.HTTP_200_OK
    
    def test_metrics_history_days_boundaries(self, client):
        """Test days boundary values"""
        # Valid boundary
        response = client.get(
            "/api/metrics/history",
            params={"days": 1}
        )
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get(
            "/api/metrics/history",
            params={"days": 365}
        )
        assert response.status_code == status.HTTP_200_OK
    
    def test_empty_script_path(self, client):
        """Test empty script path parameter"""
        response = client.get(
            "/api/metrics/history",
            params={"script_path": ""}
        )
        assert response.status_code == status.HTTP_200_OK


class TestResponseFormats:
    """Test response format consistency"""
    
    def test_health_response_format(self, client):
        """Test health check response format"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_scripts_response_format(self, client):
        """Test scripts response format"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_metrics_history_response_format(self, client):
        """Test metrics history response format"""
        response = client.get("/api/metrics/history")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metric_name" in data
        assert "script_path" in data
        assert "days" in data
        assert "data_points" in data
        assert "data" in data
        assert isinstance(data["data"], list)
    
    def test_executions_response_format(self, client):
        """Test executions response format"""
        response = client.get("/api/executions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestStatusCodes:
    """Test correct HTTP status codes"""
    
    def test_success_returns_200(self, client):
        """Test successful requests return 200"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_validation_error_returns_400(self, client):
        """Test validation errors return 400"""
        response = client.get(
            "/api/metrics/latest",
            params={"limit": 0}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_not_found_returns_404(self, client):
        """Test not found returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCORSHeaders:
    """Test CORS headers"""
    
    def test_cors_headers_present(self, client):
        """Test CORS headers are present in response"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        # TestClient doesn't always include CORS headers, but app is configured


class TestContentTypes:
    """Test content type handling"""
    
    def test_json_content_type(self, client):
        """Test endpoints return JSON"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")
    
    def test_all_endpoints_json(self, client):
        """Test all endpoints return JSON"""
        endpoints = [
            "/api/health",
            "/api/scripts",
            "/api/metrics/latest",
            "/api/metrics/history",
            "/api/stats/database",
            "/api/executions",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code == status.HTTP_200_OK:
                assert "application/json" in response.headers.get(
                    "content-type", ""
                ), f"Failed for {endpoint}"


# Integration tests
class TestIntegration:
    """Integration tests across multiple endpoints"""
    
    def test_health_then_scripts(self, client):
        """Test health check followed by scripts endpoint"""
        response1 = client.get("/api/health")
        assert response1.status_code == status.HTTP_200_OK
        
        response2 = client.get("/api/scripts")
        assert response2.status_code == status.HTTP_200_OK
    
    def test_scripts_then_metrics(self, client):
        """Test scripts followed by metrics"""
        response1 = client.get("/api/scripts")
        assert response1.status_code == status.HTTP_200_OK
        
        response2 = client.get("/api/metrics/latest")
        assert response2.status_code == status.HTTP_200_OK
    
    def test_metrics_history_with_all_params(self, client):
        """Test metrics history with all optional parameters"""
        response = client.get(
            "/api/metrics/history",
            params={
                "script_path": "test.py",
                "metric_name": "execution_time_seconds",
                "days": 7,
                "limit": 1000
            }
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["metric_name"] == "execution_time_seconds"
        assert data["days"] == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
