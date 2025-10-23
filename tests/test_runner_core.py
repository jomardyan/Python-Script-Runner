"""
Core Runner Tests - test_runner_core.py

Comprehensive unit tests for ScriptRunner core functionality including:
- Script execution with monitoring
- Timeout handling and enforcement
- Retry logic and recovery strategies
- Metrics collection and reporting
- Error handling and edge cases
- Configuration management
"""

import pytest
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
from runner import ScriptRunner, RetryConfig


@pytest.mark.unit
class TestScriptRunnerBasics:
    """Test basic ScriptRunner initialization and configuration"""
    
    def test_runner_initialization(self, tmp_path):
        """Test ScriptRunner basic initialization"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")
        
        runner = ScriptRunner(str(script_file))
        
        assert runner.script_path == str(script_file)
        assert runner.script_args == []
        assert runner.timeout is None
    
    def test_runner_with_arguments(self, tmp_path):
        """Test ScriptRunner with script arguments"""
        script_file = tmp_path / "test.py"
        script_file.write_text("import sys; print(sys.argv[1])")
        
        runner = ScriptRunner(str(script_file), script_args=['arg1', 'arg2'])
        
        assert runner.script_args == ['arg1', 'arg2']
    
    def test_runner_with_timeout(self, tmp_path):
        """Test ScriptRunner with timeout configuration"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")
        
        runner = ScriptRunner(str(script_file), timeout=30)
        
        assert runner.timeout == 30
    
    def test_runner_with_history(self, tmp_path):
        """Test ScriptRunner with history tracking"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('hello')")
        db_file = tmp_path / "history.db"
        
        runner = ScriptRunner(str(script_file), enable_history=True, history_db=str(db_file))
        
        assert runner.enable_history is True


@pytest.mark.unit
class TestScriptExecution:
    """Test basic script execution functionality"""
    
    def test_execute_simple_script(self, tmp_path):
        """Test executing a simple Python script"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello, World!')\nexit(0)")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['returncode'] == 0
        assert result['metrics']['stdout_lines'] >= 1
    
    def test_execute_script_with_args(self, tmp_path):
        """Test executing script with command-line arguments"""
        script_file = tmp_path / "test.py"
        script_file.write_text("""
import sys
for arg in sys.argv[1:]:
    print(f"Arg: {arg}")
""")
        
        runner = ScriptRunner(str(script_file), script_args=['arg1', 'arg2'])
        result = runner.run_script()
        
        assert result['success'] is True
        assert 'Arg: arg1' in result['stdout']
        assert 'Arg: arg2' in result['stdout']
    
    def test_execute_script_with_error(self, tmp_path):
        """Test executing script that raises exception"""
        script_file = tmp_path / "test.py"
        script_file.write_text("raise ValueError('Test error')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is False
        assert result['returncode'] != 0
        assert result['metrics']['stderr_lines'] > 0
    
    def test_execute_script_with_nonzero_exit(self, tmp_path):
        """Test executing script with non-zero exit code"""
        script_file = tmp_path / "test.py"
        script_file.write_text("import sys\nsys.exit(42)")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is False
        assert result['returncode'] == 42


@pytest.mark.unit
class TestTimeoutHandling:
    """Test timeout enforcement and handling"""
    
    def test_timeout_enforcement(self, tmp_path):
        """Test that timeout is enforced"""
        script_file = tmp_path / "slow.py"
        script_file.write_text("""
import time
for i in range(100):
    print(f"Iteration {i}")
    time.sleep(0.5)
""")
        
        runner = ScriptRunner(str(script_file), timeout=2)
        result = runner.run_script()
        
        assert result['metrics']['execution_time_seconds'] < 5
        assert result['metrics'].get('timed_out', False) is True
    
    def test_timeout_with_enough_time(self, tmp_path):
        """Test script completes when enough time is given"""
        script_file = tmp_path / "quick.py"
        script_file.write_text("""
import time
time.sleep(0.5)
print("Completed successfully")
""")
        
        runner = ScriptRunner(str(script_file), timeout=10)
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['metrics'].get('timed_out', False) is False
    
    def test_no_timeout_without_limit(self, tmp_path):
        """Test that script runs without timeout when not configured"""
        script_file = tmp_path / "test.py"
        script_file.write_text("""
import time
time.sleep(0.1)
print("Quick task")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['returncode'] == 0


@pytest.mark.unit
class TestRetryLogic:
    """Test retry configuration and execution"""
    
    def test_retry_config_initialization(self):
        """Test RetryConfig initialization"""
        config = RetryConfig(
            strategy='exponential',
            max_attempts=3,
            initial_delay=1.0
        )
        
        assert config.strategy == 'exponential'
        assert config.max_attempts == 3
        assert config.initial_delay == 1.0
    
    def test_retry_on_failure(self, tmp_path):
        """Test retry on script failure"""
        marker_file = tmp_path / "marker.txt"
        script_file = tmp_path / "test.py"
        script_file.write_text(f"""
import os
import sys

marker = "{marker_file}"
if os.path.exists(marker):
    with open(marker, 'r') as f:
        attempts = int(f.read().strip())
else:
    attempts = 0

attempts += 1
with open(marker, 'w') as f:
    f.write(str(attempts))

if attempts < 2:
    print(f"Attempt {{attempts}}: FAILING")
    sys.exit(1)
else:
    print(f"Attempt {{attempts}}: SUCCESS")
    sys.exit(0)
""")
        
        runner = ScriptRunner(str(script_file))
        runner.retry_config = RetryConfig(
            strategy='exponential',
            max_attempts=3,
            initial_delay=0.1
        )
        
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['attempt_number'] > 1
    
    def test_retry_exhaustion(self, tmp_path):
        """Test when retries are exhausted"""
        script_file = tmp_path / "always_fail.py"
        script_file.write_text("import sys\nsys.exit(1)")
        
        runner = ScriptRunner(str(script_file))
        runner.retry_config = RetryConfig(
            strategy='linear',
            max_attempts=2,
            initial_delay=0.05
        )
        
        result = runner.run_script()
        
        assert result['success'] is False
        assert result['attempt_number'] == 2


@pytest.mark.unit
class TestMetricsCollection:
    """Test comprehensive metrics collection"""
    
    def test_basic_metrics_present(self, tmp_path):
        """Test that all basic metrics are collected"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello, World!')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        required_metrics = [
            'execution_time_seconds',
            'cpu_max',
            'cpu_avg',
            'memory_max_mb',
            'memory_avg_mb',
            'stdout_lines',
            'stderr_lines',
            'exit_code',
            'success'
        ]
        
        for metric in required_metrics:
            assert metric in result['metrics'], f"Missing metric: {metric}"
    
    def test_cpu_metrics_collected(self, tmp_path):
        """Test CPU metrics are collected"""
        script_file = tmp_path / "cpu_work.py"
        script_file.write_text("""
import time
start = time.time()
while time.time() - start < 0.1:
    _ = [x**2 for x in range(1000)]
print("CPU work done")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['metrics']['cpu_max'] > 0
        assert result['metrics']['cpu_avg'] >= 0
    
    def test_memory_metrics_collected(self, tmp_path):
        """Test memory metrics are collected"""
        script_file = tmp_path / "mem_work.py"
        script_file.write_text("""
data = [list(range(1000)) for _ in range(100)]
print(f"Allocated {len(data)} lists")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['metrics']['memory_max_mb'] > 0
        assert result['metrics']['memory_avg_mb'] >= 0
    
    def test_output_line_count(self, tmp_path):
        """Test stdout/stderr line counting"""
        script_file = tmp_path / "output_test.py"
        script_file.write_text("""
for i in range(10):
    print(f"Line {i}")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['metrics']['stdout_lines'] == 10
        assert result['metrics']['stderr_lines'] == 0


@pytest.mark.unit
class TestOutputCapture:
    """Test stdout and stderr capture"""
    
    def test_stdout_capture(self, tmp_path):
        """Test capturing stdout"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Output line 1')\nprint('Output line 2')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert 'Output line 1' in result['stdout']
        assert 'Output line 2' in result['stdout']
    
    def test_stderr_capture(self, tmp_path):
        """Test capturing stderr"""
        script_file = tmp_path / "test.py"
        script_file.write_text("""
import sys
print("Error message 1", file=sys.stderr)
print("Error message 2", file=sys.stderr)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert 'Error message 1' in result['stderr']
        assert 'Error message 2' in result['stderr']
    
    def test_large_output_handling(self, tmp_path):
        """Test handling large output"""
        script_file = tmp_path / "large_output.py"
        script_file.write_text("""
for i in range(1000):
    print(f"Line {i}: " + "x" * 100)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['metrics']['stdout_lines'] == 1000


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling and recovery"""
    
    def test_file_not_found(self):
        """Test handling of non-existent script"""
        runner = ScriptRunner("/nonexistent/path/to/script.py")
        
        with pytest.raises(Exception):
            runner.run_script()
    
    def test_permission_error_handling(self, tmp_path):
        """Test handling of permission errors"""
        script_file = tmp_path / "noperms.py"
        script_file.write_text("print('hello')")
        script_file.chmod(0o000)
        
        try:
            runner = ScriptRunner(str(script_file))
            with pytest.raises(Exception):
                runner.run_script()
        finally:
            script_file.chmod(0o755)
    
    def test_syntax_error_capture(self, tmp_path):
        """Test capturing syntax errors"""
        script_file = tmp_path / "syntax_error.py"
        script_file.write_text("print('hello'\n")  # Missing closing paren
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is False
        assert result['returncode'] != 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
