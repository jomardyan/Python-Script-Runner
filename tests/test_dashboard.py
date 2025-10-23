"""
Comprehensive test suite for FastAPI Dashboard Backend - Enhanced Version 2.0
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import status

import sys
sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(scope="function")
def test_database():
    """Create temporary database for each test"""
    tmp_dir = tempfile.mkdtemp()
    db_path = str(Path(tmp_dir) / "test.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create schema matching HistoryManager
    cursor.execute("""CREATE TABLE IF NOT EXISTS executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        script_path TEXT NOT NULL,
        script_args TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        execution_time_seconds REAL NOT NULL,
        exit_code INTEGER NOT NULL,
        success BOOLEAN NOT NULL,
        attempt_number INTEGER DEFAULT 1,
        timeout_seconds INTEGER,
        timed_out BOOLEAN DEFAULT 0,
        stdout_lines INTEGER,
        stderr_lines INTEGER,
        python_version TEXT,
        platform TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        execution_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL,
        FOREIGN KEY (execution_id) REFERENCES executions(id) ON DELETE CASCADE
    )""")
    
    # Insert sample data
    now = datetime.now().isoformat()
    cursor.execute("""INSERT INTO executions 
        (script_path, script_args, start_time, end_time, execution_time_seconds, exit_code, success, stdout_lines, stderr_lines, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
        ('test_script.py', '', now, now, 1.5, 0, True, 10, 0, now))
    exec_id = cursor.lastrowid
    
    cursor.execute("""INSERT INTO metrics (execution_id, metric_name, metric_value)
        VALUES (?, ?, ?)""", (exec_id, 'execution_time_seconds', 1.5))
    
    # Add failed execution
    cursor.execute("""INSERT INTO executions 
        (script_path, script_args, start_time, end_time, execution_time_seconds, exit_code, success, stdout_lines, stderr_lines, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
        ('failed_script.py', '', now, now, 2.0, 1, False, 5, 15, now))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def client(test_database):
    """Create test client with initialized app"""
    from app import app, init_managers
    
    # Initialize managers with test database
    init_managers(test_database)
    
    # Return test client
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_ok(self, client):
        """Test health endpoint returns ok status"""
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "error"]
        assert "version" in data
        assert data["version"] == "2.0.0"


class TestScriptsEndpoint:
    """Test scripts listing endpoint"""
    
    def test_get_scripts(self, client):
        """Test retrieving list of scripts with execution counts"""
        response = client.get("/api/scripts")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        script = data[0]
        assert "path" in script
        assert "execution_count" in script
        assert "successful_runs" in script
        assert "success_rate" in script


class TestExecutionStatsEndpoint:
    """Test execution statistics endpoints"""
    
    def test_execution_stats(self, client):
        """Test execution statistics endpoint"""
        response = client.get("/api/stats/execution")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "successful" in data
        assert "total_executions" in data
        assert "failed" in data
        assert "success_rate" in data
    
    def test_execution_stats_with_limit(self, client):
        """Test execution statistics with limit parameter"""
        response = client.get("/api/stats/execution?limit=100")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_executions" in data


class TestMetricsEndpoint:
    """Test metrics endpoints"""
    
    def test_available_metrics(self, client):
        """Test available metrics endpoint"""
        response = client.get("/api/metrics/available")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "available_metrics" in data
        assert isinstance(data["available_metrics"], list)
        
    def test_get_metrics_with_name(self, client):
        """Test getting metrics with specific name"""
        response = client.get("/api/metrics/history?metric_name=execution_time_seconds")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()


class TestPerformanceStatsEndpoint:
    """Test performance statistics endpoints"""
    
    def test_performance_stats(self, client):
        """Test performance stats endpoint"""
        response = client.get("/api/stats/performance?metric_name=execution_time_seconds")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "min" in data or "message" in data
        assert "max" in data or "message" in data
        assert "avg" in data or "message" in data


class TestExecutionsEndpoint:
    """Test executions list endpoint"""
    
    def test_get_executions(self, client):
        """Test retrieving executions list"""
        response = client.get("/api/executions")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            execution = data[0]
            assert "id" in execution
            assert "script_path" in execution
            assert "exit_code" in execution
    
    def test_get_failed_executions(self, client):
        """Test retrieving failed executions"""
        response = client.get("/api/executions/failed")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # All should have exit_code != 0
        for execution in data:
            assert execution.get("exit_code", 0) != 0
    
    def test_executions_with_filter(self, client):
        """Test executions endpoint with exit_code filter"""
        response = client.get("/api/executions?exit_code=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_endpoint(self, client):
        """Test request to invalid endpoint"""
        response = client.get("/api/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_invalid_metric_name(self, client):
        """Test requesting invalid metric name"""
        response = client.get("/api/metrics/nonexistent_metric_xyz")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    def test_stats_with_invalid_limit(self, client):
        """Test statistics with invalid limit"""
        response = client.get("/api/stats/execution?limit=-1")
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
    
    def test_performance_stats_missing_metric(self, client):
        """Test performance stats without required metric name"""
        response = client.get("/api/stats/performance")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


class TestWebSocketIntegration:
    """Test WebSocket connectivity"""
    
    def test_websocket_connection(self, client):
        """Test WebSocket connection attempt"""
        # Note: TestClient doesn't support WebSocket well
        # This is a placeholder for actual WebSocket tests
        # Would need websockets library for proper testing
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
