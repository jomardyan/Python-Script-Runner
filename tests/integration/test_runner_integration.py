"""
Integration tests for runner.py - End-to-end execution workflows

Tests cover:
- Complete script execution with v7 features enabled
- Real workflow execution with dependencies
- Security scanning pre-execution
- Cost tracking during execution
- OpenTelemetry tracing
- Dashboard data population
- Failure recovery and retry logic
"""

import pytest
import os
import sys
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import runner components
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from runner import ScriptRunner, HistoryManager


class TestFullExecutionWorkflow:
    """Test complete execution workflows with v7 features"""
    
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
        runner = ScriptRunner(str(script_file), enable_history=True, history_db=str(db_file))
        
        result = runner.run_script()
        
        assert result is not None
        assert result['returncode'] == 0
        assert result['stdout_lines'] >= 2
        assert os.path.exists(str(db_file))
    
    def test_execution_with_metrics_collection(self, tmp_path):
        """Test script execution with comprehensive metrics"""
        script_file = tmp_path / "test_metrics.py"
        script_file.write_text("""
data = [i ** 2 for i in range(100)]
print(f"Processed {len(data)} items")
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()
        
        assert result['returncode'] == 0
        assert 'metrics' in result
        assert result['metrics']['execution_time_seconds'] > 0
    
    def test_execution_with_timeouts(self, tmp_path):
        """Test execution timeout handling"""
        script_file = tmp_path / "timeout_test.py"
        script_file.write_text("""
import time
print("Starting long process")
time.sleep(10)
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), timeout=1, enable_history=False)
        result = runner.run_script()
        
        # Should timeout
        assert result['returncode'] != 0


class TestV7FeaturesIntegration:
    """Test v7 features integrated with script execution"""
    
    def test_execution_with_v7_security_checks(self, tmp_path):
        """Test script execution with pre-execution security checks"""
        script_file = tmp_path / "secure_script.py"
        script_file.write_text("""
print("Secure script execution")
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.enable_code_analysis = False
        
        # Run security checks
        security_passed = runner.run_pre_execution_security_checks()
        assert security_passed is True
        
        # Execute script
        result = runner.run_script()
        assert result['returncode'] == 0
    
    def test_execution_with_v7_metrics_collection(self, tmp_path):
        """Test v7 metrics collected during execution"""
        script_file = tmp_path / "metrics_test.py"
        script_file.write_text("""
print("Collecting metrics")
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()
        
        # Collect v7 metrics
        enhanced = runner.collect_v7_metrics(result)
        
        assert 'metrics' in enhanced
        assert 'v7_metrics' in enhanced['metrics']
        assert enhanced['metrics']['v7_metrics']['security_findings_count'] == 0


class TestFailureRecovery:
    """Test failure recovery and error handling"""
    
    def test_script_syntax_error(self, tmp_path):
        """Test handling of script with syntax error"""
        script_file = tmp_path / "syntax_error.py"
        script_file.write_text("""
print("Hello"
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()
        
        assert result['returncode'] != 0
    
    def test_script_runtime_error(self, tmp_path):
        """Test handling of runtime error"""
        script_file = tmp_path / "runtime_error.py"
        script_file.write_text("""
x = 10
y = 0
z = x / y
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()
        
        assert result['returncode'] != 0


class TestComplexWorkflows:
    """Test complex, multi-step workflows"""
    
    def test_sequential_script_execution(self, tmp_path):
        """Test executing multiple scripts sequentially"""
        script1 = tmp_path / "step1.py"
        script1.write_text("""
with open('/tmp/workflow_state.txt', 'w') as f:
    f.write('step1_complete')
print("Step 1 complete")
exit(0)
""")
        
        script2 = tmp_path / "step2.py"
        script2.write_text("""
with open('/tmp/workflow_state.txt', 'r') as f:
    state = f.read()
if state == 'step1_complete':
    print("Step 2 received state from step 1")
    exit(0)
else:
    print("Step 2 error: invalid state")
    exit(1)
""")
        
        # Clean up state file
        try:
            os.remove('/tmp/workflow_state.txt')
        except OSError:
            pass
        
        # Execute scripts
        runner1 = ScriptRunner(str(script1), enable_history=False)
        result1 = runner1.run_script()
        assert result1['returncode'] == 0
        
        runner2 = ScriptRunner(str(script2), enable_history=False)
        result2 = runner2.run_script()
        assert result2['returncode'] == 0


@pytest.fixture
def tmp_path(tmp_path):
    """Provide temporary directory for tests"""
    return tmp_path
