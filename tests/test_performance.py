"""
Performance and Benchmark Tests - test_performance.py

Performance, load, and stress tests covering:
- Execution overhead measurement
- Memory usage patterns
- CPU utilization efficiency
- Concurrent execution performance
- Large workload handling
- Baseline metrics
"""

import pytest
import os
import sys
import tempfile
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from runner import ScriptRunner


@pytest.mark.performance
class TestExecutionOverhead:
    """Test runner overhead and efficiency"""
    
    def test_overhead_calculation(self, tmp_path):
        """Test that runner overhead is minimal"""
        script_file = tmp_path / "overhead_test.py"
        script_file.write_text("""
import time
start = time.time()
time.sleep(0.1)
end = time.time()
print(f"Sleep duration: {end - start:.3f}s")
""")
        
        runner = ScriptRunner(str(script_file))
        
        start_total = time.time()
        result = runner.run_script()
        total_time = time.time() - start_total
        
        script_time = result['metrics']['execution_time_seconds']
        overhead = (total_time - script_time) / total_time * 100
        
        # Overhead should be less than 50% for simple scripts
        assert overhead < 50
    
    def test_quick_script_execution(self, tmp_path):
        """Test execution of very quick scripts"""
        script_file = tmp_path / "quick.py"
        script_file.write_text("print('quick')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['metrics']['execution_time_seconds'] < 1.0
    
    def test_baseline_metrics_collection(self, tmp_path):
        """Test baseline metrics are properly collected"""
        script_file = tmp_path / "baseline.py"
        script_file.write_text("""
import time
time.sleep(0.05)
print("Baseline measurement")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        # Check all baseline metrics exist
        metrics = result['metrics']
        baseline_metrics = [
            'execution_time_seconds',
            'cpu_max',
            'cpu_avg',
            'memory_max_mb',
            'memory_avg_mb',
            'stdout_lines',
            'stderr_lines'
        ]
        
        for metric in baseline_metrics:
            assert metric in metrics


@pytest.mark.performance
class TestCPUUtilization:
    """Test CPU utilization and efficiency"""
    
    def test_cpu_bound_workload(self, tmp_path):
        """Test CPU metrics for CPU-bound workload"""
        script_file = tmp_path / "cpu_bound.py"
        script_file.write_text("""
import time
start = time.time()
while time.time() - start < 0.15:
    _ = [x**2 for x in range(10000)]
print("CPU work complete")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        assert metrics['cpu_max'] > 0
        assert metrics['cpu_avg'] >= 0
        assert metrics['cpu_max'] >= metrics['cpu_avg']
    
    def test_cpu_metrics_range(self, tmp_path):
        """Test CPU metrics are within valid range"""
        script_file = tmp_path / "cpu_range.py"
        script_file.write_text("""
import time
import math
start = time.time()
while time.time() - start < 0.1:
    _ = [math.sqrt(x) for x in range(5000)]
print("Done")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        # CPU percentage should be 0-100
        assert 0 <= metrics['cpu_max'] <= 100
        assert 0 <= metrics['cpu_avg'] <= 100


@pytest.mark.performance
class TestMemoryUtilization:
    """Test memory usage and patterns"""
    
    def test_memory_bound_workload(self, tmp_path):
        """Test memory metrics for memory-intensive workload"""
        script_file = tmp_path / "mem_bound.py"
        script_file.write_text("""
data = []
for i in range(100):
    data.append([0] * 10000)
print(f"Allocated {len(data)} arrays")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        assert metrics['memory_max_mb'] > 0
        assert metrics['memory_avg_mb'] >= 0
    
    def test_memory_efficiency(self, tmp_path):
        """Test memory is properly measured"""
        script_file = tmp_path / "mem_eff.py"
        script_file.write_text("""
import time
small_data = [0] * 1000
time.sleep(0.1)
print("Memory test")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result['metrics']
        # Memory should be positive and reasonable
        assert metrics['memory_max_mb'] > 0.1
        assert metrics['memory_avg_mb'] > 0


@pytest.mark.performance
@pytest.mark.slow
class TestHighConcurrency:
    """Test performance under concurrent load"""
    
    def test_10_concurrent_executions(self, tmp_path):
        """Test 10 concurrent script executions"""
        script_file = tmp_path / "concurrent_10.py"
        script_file.write_text("""
import time
import random
time.sleep(random.uniform(0.01, 0.05))
print("Task complete")
""")
        
        results = []
        errors = []
        
        def run_script():
            try:
                runner = ScriptRunner(str(script_file))
                result = runner.run_script()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=run_script) for _ in range(10)]
        start = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        duration = time.time() - start
        
        assert len(errors) == 0
        assert len(results) == 10
        assert all(r['success'] for r in results)
        # Should complete in reasonable time (less than 10 seconds for 10 tasks with 0.05s each)
        assert duration < 10
    
    @pytest.mark.very_slow
    def test_20_concurrent_executions(self, tmp_path):
        """Test 20 concurrent script executions"""
        script_file = tmp_path / "concurrent_20.py"
        script_file.write_text("""
import time
time.sleep(0.02)
print("Done")
""")
        
        results = []
        errors = []
        
        def run_script():
            try:
                runner = ScriptRunner(str(script_file))
                result = runner.run_script()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        threads = [threading.Thread(target=run_script) for _ in range(20)]
        start = time.time()
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        duration = time.time() - start
        
        assert len(errors) == 0
        assert len(results) == 20


@pytest.mark.performance
class TestLargeOutput:
    """Test handling of large output"""
    
    def test_1000_lines_output(self, tmp_path):
        """Test handling 1000 lines of output"""
        script_file = tmp_path / "large_output.py"
        script_file.write_text("""
for i in range(1000):
    print(f"Line {i}: " + "x" * 50)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['metrics']['stdout_lines'] == 1000
    
    def test_large_line_length(self, tmp_path):
        """Test handling lines with large length"""
        script_file = tmp_path / "large_lines.py"
        script_file.write_text("""
for i in range(100):
    print("X" * 10000)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['metrics']['stdout_lines'] == 100


@pytest.mark.performance
class TestExecutionTimeVariance:
    """Test consistency and variance in execution time"""
    
    def test_time_consistency(self, tmp_path):
        """Test execution time consistency"""
        script_file = tmp_path / "consistent_time.py"
        script_file.write_text("""
import time
time.sleep(0.05)
print("Done")
""")
        
        runner = ScriptRunner(str(script_file))
        
        times = []
        for _ in range(3):
            result = runner.run_script()
            times.append(result['metrics']['execution_time_seconds'])
        
        # All times should be roughly similar (within 50ms)
        assert max(times) - min(times) < 0.05
    
    def test_execution_time_accuracy(self, tmp_path):
        """Test execution time accuracy"""
        script_file = tmp_path / "accurate_time.py"
        script_file.write_text("""
import time
start = time.time()
time.sleep(0.1)
actual = time.time() - start
print(f"Actual sleep: {actual:.3f}")
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        # Should be at least 0.1 seconds
        assert result['metrics']['execution_time_seconds'] >= 0.09


@pytest.mark.performance
class TestStressScenarios:
    """Test various stress scenarios"""
    
    def test_rapid_fire_executions(self, tmp_path):
        """Test rapid consecutive executions"""
        script_file = tmp_path / "rapid.py"
        script_file.write_text("print('quick'); exit(0)")
        
        runner = ScriptRunner(str(script_file))
        
        start = time.time()
        for _ in range(20):
            result = runner.run_script()
            assert result['success'] is True
        duration = time.time() - start
        
        # 20 quick executions should complete quickly
        assert duration < 10
    
    def test_very_long_running_script(self, tmp_path):
        """Test handling long-running script"""
        script_file = tmp_path / "long.py"
        script_file.write_text("""
import time
for i in range(3):
    time.sleep(0.1)
    print(f"Iteration {i}")
print("Complete")
""")
        
        runner = ScriptRunner(str(script_file), timeout=10)
        result = runner.run_script()
        
        assert result['success'] is True
        assert result['metrics']['execution_time_seconds'] >= 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
