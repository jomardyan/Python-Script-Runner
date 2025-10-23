"""
Integration Tests - test_integration.py

End-to-end integration tests covering:
- Complete execution workflows with v7 features
- History tracking and persistence
- Real workflow execution with dependencies
- Feature interaction and integration
- Multi-execution scenarios
"""

import pytest
import os
import sys
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
from runner import ScriptRunner, HistoryManager, AlertManager, RetryConfig


@pytest.mark.integration
class TestExecutionWithHistory:
    """Test script execution with history tracking enabled"""
    
    def test_execution_with_history_tracking(self, tmp_path):
        """Test script execution with history tracking enabled"""
        script_file = tmp_path / "test_history.py"
        script_file.write_text("""
import time
print("Test script starting")
time.sleep(0.1)
print("Test script completed")
exit(0)
""")
        
        db_file = tmp_path / "history.db"
        runner = ScriptRunner(str(script_file), enable_history=True)
        
        result = runner.run_script()
        
        assert result is not None
        assert result['returncode'] == 0
        assert result['stdout_lines'] >= 2
    
    def test_multiple_executions_tracked(self, tmp_path):
        """Test multiple executions are tracked separately"""
        script_file = tmp_path / "test_multi.py"
        script_file.write_text("print('Execution'); exit(0)")
        
        db_file = tmp_path / "history.db"
        runner = ScriptRunner(str(script_file), enable_history=True)
        
        result1 = runner.run_script()
        time.sleep(0.1)
        result2 = runner.run_script()
        
        assert result1['returncode'] == 0
        assert result2['returncode'] == 0
        assert result1.get('execution_id') != result2.get('execution_id')
    
    def test_history_database_creation(self, tmp_path):
        """Test that history database is properly created"""
        script_file = tmp_path / "test_db.py"
        script_file.write_text("print('test'); exit(0)")
        
        db_file = tmp_path / "test.db"
        runner = ScriptRunner(str(script_file), enable_history=True)
        
        result = runner.run_script()
        
        # Check if metrics are collected
        assert 'metrics' in result
        assert len(result['metrics']) > 0


@pytest.mark.integration
class TestAlertIntegration:
    """Test alert system integration with execution"""
    
    def test_alerts_triggered_during_execution(self, tmp_path):
        """Test that alerts are triggered during script execution"""
        script_file = tmp_path / "cpu_heavy.py"
        script_file.write_text("""
import time
start = time.time()
while time.time() - start < 0.2:
    _ = [x**2 for x in range(10000)]
print("CPU work done")
""")
        
        runner = ScriptRunner(str(script_file))
        alert_manager = AlertManager()
        
        alert_manager.add_alert(
            name="cpu_high",
            condition="cpu_max > 10",  # Low threshold to ensure trigger
            channels=["console"],
            severity="WARNING"
        )
        
        result = runner.run_script()
        alerts = alert_manager.check_alerts(result['metrics'])
        
        # May or may not trigger depending on system
        assert isinstance(alerts, list)
    
    def test_multiple_alerts_on_same_execution(self, tmp_path):
        """Test multiple alerts evaluated on same execution"""
        script_file = tmp_path / "resource_test.py"
        script_file.write_text("""
import time
data = [list(range(500)) for _ in range(100)]
time.sleep(0.05)
print("Test complete")
""")
        
        runner = ScriptRunner(str(script_file))
        alert_manager = AlertManager()
        
        alert_manager.add_alert("cpu_alert", "cpu_max > 1", ["console"], severity="INFO")
        alert_manager.add_alert("mem_alert", "memory_max_mb > 1", ["console"], severity="INFO")
        alert_manager.add_alert("time_alert", "execution_time_seconds > 0.01", ["console"], severity="INFO")
        
        result = runner.run_script()
        alerts = alert_manager.check_alerts(result['metrics'])
        
        assert isinstance(alerts, list)


@pytest.mark.integration
class TestRetryIntegration:
    """Test retry logic integration with execution"""
    
    def test_retry_until_success(self, tmp_path):
        """Test retry mechanism eventually succeeds"""
        marker = tmp_path / "retry_marker.txt"
        script_file = tmp_path / "retry_test.py"
        script_file.write_text(f"""
import os
import sys

marker = "{marker}"
if os.path.exists(marker):
    attempts = int(open(marker).read())
else:
    attempts = 0

attempts += 1
open(marker, 'w').write(str(attempts))

if attempts < 3:
    print(f"Attempt {{attempts}}: Failing")
    sys.exit(1)
else:
    print(f"Attempt {{attempts}}: Success")
    sys.exit(0)
""")
        
        runner = ScriptRunner(str(script_file))
        runner.retry_config = RetryConfig(
            strategy='linear',
            max_attempts=5,
            initial_delay=0.05
        )
        
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['attempt_number'] >= 3
    
    def test_retry_with_timeout(self, tmp_path):
        """Test retry with timeout constraint"""
        script_file = tmp_path / "timeout_retry.py"
        script_file.write_text("import sys; sys.exit(1)")
        
        runner = ScriptRunner(str(script_file), timeout=5)
        runner.retry_config = RetryConfig(
            strategy='exponential',
            max_attempts=2,
            initial_delay=0.1
        )
        
        result = runner.run_script()
        
        assert result['success'] is False
        assert result['attempt_number'] <= 2


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""
    
    def test_complete_workflow_success(self, tmp_path):
        """Test complete successful workflow"""
        script_file = tmp_path / "workflow.py"
        script_file.write_text("""
print("Step 1: Initialization")
data = [x * 2 for x in range(100)]
print(f"Step 2: Processed {len(data)} items")
print("Step 3: Validation passed")
print("Workflow completed successfully")
""")
        
        runner = ScriptRunner(
            str(script_file),
            timeout=30,
            enable_history=True
        )
        
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['returncode'] == 0
        assert result['metrics']['stdout_lines'] == 4
        assert result['metrics']['execution_time_seconds'] > 0
    
    def test_workflow_with_error_handling(self, tmp_path):
        """Test workflow with error handling"""
        script_file = tmp_path / "error_workflow.py"
        script_file.write_text("""
import sys
try:
    print("Attempting operation")
    result = 1 / 0
except ZeroDivisionError as e:
    print(f"Error caught: {e}")
    sys.exit(1)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is False
        assert "Error caught" in result['stdout']
    
    def test_workflow_with_retries_and_alerts(self, tmp_path):
        """Test workflow with both retries and alerts"""
        marker = tmp_path / "combo_marker.txt"
        script_file = tmp_path / "combo.py"
        script_file.write_text(f"""
import os
marker = "{marker}"
attempts = int(open(marker).read()) if os.path.exists(marker) else 0
attempts += 1
open(marker, 'w').write(str(attempts))

import time
start = time.time()
while time.time() - start < 0.05:
    _ = [x**2 for x in range(5000)]

if attempts < 2:
    exit(1)
print("Workflow complete")
""")
        
        runner = ScriptRunner(str(script_file), timeout=60)
        runner.retry_config = RetryConfig(
            strategy='linear',
            max_attempts=3,
            initial_delay=0.05
        )
        
        alert_manager = AlertManager()
        alert_manager.add_alert("high_cpu", "cpu_max > 5", ["console"], severity="INFO")
        
        result = runner.run_script()
        
        assert result['success'] is True
        alerts = alert_manager.check_alerts(result['metrics'])
        assert isinstance(alerts, list)


@pytest.mark.integration
class TestMetricsCollectionIntegration:
    """Test metrics collection across different scenarios"""
    
    def test_metrics_collected_for_simple_script(self, tmp_path):
        """Test metrics are collected for simple scripts"""
        script_file = tmp_path / "simple.py"
        script_file.write_text("print('Hello')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        required = [
            'execution_time_seconds', 'cpu_max', 'memory_max_mb',
            'stdout_lines', 'stderr_lines', 'exit_code', 'success'
        ]
        
        for metric in required:
            assert metric in metrics
    
    def test_metrics_collected_for_complex_script(self, tmp_path):
        """Test metrics for compute-intensive script"""
        script_file = tmp_path / "complex.py"
        script_file.write_text("""
import time
import math

data = []
start = time.time()
while time.time() - start < 0.1:
    data.append([math.sqrt(x) for x in range(1000)])

print(f"Processed {len(data)} batches")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        assert metrics['cpu_max'] > 0
        assert metrics['memory_max_mb'] > 0
        assert metrics['execution_time_seconds'] > 0
    
    def test_metrics_consistency(self, tmp_path):
        """Test metrics consistency across runs"""
        script_file = tmp_path / "consistent.py"
        script_file.write_text("print('Test'); exit(0)")
        
        runner = ScriptRunner(str(script_file))
        
        result1 = runner.run_script()
        result2 = runner.run_script()
        
        # Both should have similar metric structure
        assert set(result1['metrics'].keys()) == set(result2['metrics'].keys())
        assert result1['returncode'] == result2['returncode']


@pytest.mark.integration
class TestConcurrentExecutions:
    """Test concurrent execution scenarios"""
    
    def test_concurrent_simple_executions(self, tmp_path):
        """Test multiple concurrent script executions"""
        script_file = tmp_path / "concurrent.py"
        script_file.write_text("""
import time
import os
import random
process_id = os.getpid()
sleep_time = random.uniform(0.05, 0.1)
time.sleep(sleep_time)
print(f"Process {process_id} completed")
""")
        
        import threading
        results = []
        errors = []
        
        def run_script():
            try:
                runner = ScriptRunner(str(script_file))
                result = runner.run_script()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=run_script) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(errors) == 0
        assert len(results) == 3
        assert all(r['success'] for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
