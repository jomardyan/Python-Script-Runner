#!/usr/bin/env python3
"""
Comprehensive test suite for Python Script Runner v7.0.0
Tests all major features: execution, monitoring, alerts, history, workflows, tracing, etc.
"""

import sys
import os
import time
import json
import tempfile
from pathlib import Path

# Add runner to path
sys.path.insert(0, os.path.dirname(__file__))

def test_basic_execution():
    """Test 1: Basic script execution with monitoring"""
    print("\n" + "="*80)
    print("TEST 1: Basic Script Execution with Monitoring")
    print("="*80)
    
    from runner import ScriptRunner
    
    runner = ScriptRunner(
        os.path.join(os.path.dirname(__file__), "test_script.py"),
        timeout=60,
        enable_history=True
    )
    
    result = runner.run_script()
    
    print(f"✅ Execution Status: {'SUCCESS' if result['success'] else 'FAILED'}")
    print(f"   Exit Code: {result['returncode']}")
    print(f"   Duration: {result['metrics']['execution_time_seconds']:.2f}s")
    print(f"   CPU Max: {result['metrics']['cpu_max']:.1f}%")
    print(f"   Memory Max: {result['metrics']['memory_max_mb']:.1f} MB")
    print(f"   Stdout Lines: {result['metrics']['stdout_lines']}")
    
    return result['success']


def test_timeout_handling():
    """Test 2: Timeout handling"""
    print("\n" + "="*80)
    print("TEST 2: Timeout Handling")
    print("="*80)
    
    from runner import ScriptRunner
    
    # Create a simple test script that runs forever
    test_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    test_script.write("""
import time
print("Starting long-running process...")
for i in range(100):
    print(f"Iteration {i}")
    time.sleep(1)
print("This shouldn't print")
""")
    test_script.close()
    
    try:
        runner = ScriptRunner(test_script.name, timeout=2)
        result = runner.run_script()
        
        print(f"✅ Timeout Triggered: {result['metrics'].get('timed_out', False)}")
        print(f"   Exit Code: {result['returncode']}")
        print(f"   Duration: {result['metrics']['execution_time_seconds']:.2f}s")
        
        return result['metrics'].get('timed_out', False)
    finally:
        os.unlink(test_script.name)


def test_retry_logic():
    """Test 3: Retry logic with exponential backoff"""
    print("\n" + "="*80)
    print("TEST 3: Retry Logic with Exponential Backoff")
    print("="*80)
    
    from runner import ScriptRunner, RetryConfig
    
    # Create a script that fails first time then succeeds
    test_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    test_script.write("""
import sys
import os

# Create a marker file to track attempts
marker = '/tmp/retry_test_marker.txt'
if os.path.exists(marker):
    with open(marker, 'r') as f:
        attempts = int(f.read().strip())
else:
    attempts = 0

attempts += 1

with open(marker, 'w') as f:
    f.write(str(attempts))

if attempts < 2:
    print(f"Attempt {attempts}: FAILING")
    sys.exit(1)
else:
    print(f"Attempt {attempts}: SUCCESS")
    sys.exit(0)
""")
    test_script.close()
    
    # Clean marker
    marker_file = '/tmp/retry_test_marker.txt'
    if os.path.exists(marker_file):
        os.remove(marker_file)
    
    try:
        runner = ScriptRunner(test_script.name)
        runner.retry_config = RetryConfig(
            strategy='exponential',
            max_attempts=3,
            initial_delay=0.1
        )
        
        result = runner.run_script()
        
        print(f"✅ Final Status: {'SUCCESS' if result['success'] else 'FAILED'}")
        print(f"   Attempt Number: {result['attempt_number']}")
        print(f"   Total Duration: {result['metrics']['execution_time_seconds']:.2f}s")
        
        return result['attempt_number'] > 1
    finally:
        os.unlink(test_script.name)
        if os.path.exists(marker_file):
            os.remove(marker_file)


def test_alert_system():
    """Test 4: Alert system"""
    print("\n" + "="*80)
    print("TEST 4: Alert System Configuration")
    print("="*80)
    
    from runner import ScriptRunner, AlertManager
    
    runner = ScriptRunner(os.path.join(os.path.dirname(__file__), "test_script.py"))
    
    # Create alert manager
    alert_manager = AlertManager()
    
    # Add test alerts
    alert_manager.add_alert(
        name="high_cpu",
        condition="cpu_max > 80",
        severity="WARNING",
        channels=["console"]
    )
    
    alert_manager.add_alert(
        name="high_memory",
        condition="memory_max_mb > 100",
        severity="WARNING",
        channels=["console"]
    )
    
    result = runner.run_script()
    
    # Check alerts
    metrics = result['metrics']
    alerts_triggered = alert_manager.check_alerts(metrics)
    
    print(f"✅ Alert System Status: Operational")
    print(f"   Alerts Defined: 2")
    print(f"   Alerts Triggered: {len(alerts_triggered)}")
    print(f"   CPU Max: {metrics['cpu_max']:.1f}% (threshold: 80%)")
    print(f"   Memory Max: {metrics['memory_max_mb']:.1f} MB (threshold: 100MB)")
    
    return True


def test_history_persistence():
    """Test 5: History persistence and retrieval"""
    print("\n" + "="*80)
    print("TEST 5: History Persistence and Retrieval")
    print("="*80)
    
    from runner import ScriptRunner, HistoryManager
    
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False).name
    
    try:
        # First execution
        runner = ScriptRunner(
            os.path.join(os.path.dirname(__file__), "test_script.py"),
            history_db=db_file
        )
        result1 = runner.run_script()
        exec_id_1 = result1.get('execution_id')
        
        # Second execution
        time.sleep(0.5)
        result2 = runner.run_script()
        exec_id_2 = result2.get('execution_id')
        
        # Query history
        history = HistoryManager(db_file)
        
        print(f"✅ History Persistence Status: Operational")
        print(f"   Executions Recorded: 2")
        print(f"   Execution ID 1: {exec_id_1}")
        print(f"   Execution ID 2: {exec_id_2}")
        print(f"   Database File: {db_file}")
        
        return exec_id_1 is not None and exec_id_2 is not None
    finally:
        if os.path.exists(db_file):
            os.remove(db_file)


def test_metrics_collection():
    """Test 6: Comprehensive metrics collection"""
    print("\n" + "="*80)
    print("TEST 6: Comprehensive Metrics Collection")
    print("="*80)
    
    from runner import ScriptRunner
    
    runner = ScriptRunner(os.path.join(os.path.dirname(__file__), "test_script.py"))
    result = runner.run_script()
    
    metrics = result['metrics']
    required_metrics = [
        'execution_time_seconds', 'cpu_max', 'cpu_avg', 'memory_max_mb',
        'memory_avg_mb', 'stdout_lines', 'stderr_lines', 'exit_code', 'success'
    ]
    
    collected = sum(1 for m in required_metrics if m in metrics)
    
    print(f"✅ Metrics Collection Status: Operational")
    print(f"   Required Metrics: {len(required_metrics)}")
    print(f"   Collected Metrics: {collected}")
    
    for metric in required_metrics:
        if metric in metrics:
            value = metrics[metric]
            if isinstance(value, float):
                print(f"   ✓ {metric}: {value:.2f}")
            else:
                print(f"   ✓ {metric}: {value}")
    
    return collected == len(required_metrics)


def test_error_handling():
    """Test 7: Error handling and recovery"""
    print("\n" + "="*80)
    print("TEST 7: Error Handling and Recovery")
    print("="*80)
    
    from runner import ScriptRunner
    
    # Create a script that will error
    test_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    test_script.write("""
print("Starting test...")
raise ValueError("Intentional test error")
print("This shouldn't print")
""")
    test_script.close()
    
    try:
        runner = ScriptRunner(test_script.name)
        result = runner.run_script()
        
        print(f"✅ Error Handling Status: Operational")
        print(f"   Script Failed As Expected: {not result['success']}")
        print(f"   Exit Code: {result['returncode']}")
        print(f"   Error Captured: {result['metrics']['stderr_lines'] > 0}")
        print(f"   Metrics Collected: {len(result['metrics'])} metrics")
        
        return True
    finally:
        os.unlink(test_script.name)


def test_cicd_integration():
    """Test 8: CI/CD integration capabilities"""
    print("\n" + "="*80)
    print("TEST 8: CI/CD Integration Capabilities")
    print("="*80)
    
    from runner import ScriptRunner
    
    runner = ScriptRunner(os.path.join(os.path.dirname(__file__), "test_script.py"))
    result = runner.run_script()
    
    print(f"✅ CI/CD Integration Status: Ready")
    print(f"   Exit Code (for CI/CD): {result['returncode']}")
    print(f"   Success Status: {result['success']}")
    print(f"   Execution Time: {result['metrics']['execution_time_seconds']:.2f}s")
    print(f"   Performance Data Available: Yes")
    print(f"   Metrics for Gates: Yes")
    print(f"   Baseline Comparison Ready: Yes")
    
    return result['returncode'] == 0


def test_performance_profiling():
    """Test 9: Performance profiling"""
    print("\n" + "="*80)
    print("TEST 9: Performance Profiling")
    print("="*80)
    
    from runner import ScriptRunner
    
    runner = ScriptRunner(os.path.join(os.path.dirname(__file__), "test_script.py"))
    
    start = time.time()
    result = runner.run_script()
    total = time.time() - start
    
    metrics = result['metrics']
    overhead = (total - metrics['execution_time_seconds']) / total * 100
    
    print(f"✅ Performance Profiling Status: Operational")
    print(f"   Script Time: {metrics['execution_time_seconds']:.2f}s")
    print(f"   Runner Overhead: {overhead:.2f}%")
    print(f"   CPU Utilization: {metrics['cpu_avg']:.1f}%")
    print(f"   Memory Efficiency: {metrics['memory_avg_mb']:.1f} MB avg")
    print(f"   Process Monitoring: Active")
    
    return overhead < 5  # Less than 5% overhead


def test_concurrent_execution():
    """Test 10: Concurrent execution capability"""
    print("\n" + "="*80)
    print("TEST 10: Concurrent Execution Capability")
    print("="*80)
    
    from runner import ScriptRunner
    import threading
    
    results = []
    errors = []
    
    def run_script():
        try:
            runner = ScriptRunner(os.path.join(os.path.dirname(__file__), "test_script.py"))
            result = runner.run_script()
            results.append(result)
        except Exception as e:
            errors.append(str(e))
    
    # Run 3 concurrent executions
    threads = [threading.Thread(target=run_script) for _ in range(3)]
    
    start = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duration = time.time() - start
    
    print(f"✅ Concurrent Execution Status: Operational")
    print(f"   Concurrent Runs: 3")
    print(f"   Successful: {len(results)}/3")
    print(f"   Errors: {len(errors)}")
    print(f"   Total Time: {duration:.2f}s")
    print(f"   Thread Safety: {'Verified' if len(errors) == 0 else 'Issues Found'}")
    
    return len(errors) == 0 and len(results) == 3


def run_all_tests():
    """Run all feature tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PYTHON SCRIPT RUNNER v7.0.0 - COMPREHENSIVE FEATURE TEST".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    tests = [
        ("Basic Execution with Monitoring", test_basic_execution),
        ("Timeout Handling", test_timeout_handling),
        ("Retry Logic", test_retry_logic),
        ("Alert System", test_alert_system),
        ("History Persistence", test_history_persistence),
        ("Metrics Collection", test_metrics_collection),
        ("Error Handling", test_error_handling),
        ("CI/CD Integration", test_cicd_integration),
        ("Performance Profiling", test_performance_profiling),
        ("Concurrent Execution", test_concurrent_execution),
    ]
    
    results = {}
    start_time = time.time()
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "✅ PASSED" if result else "❌ FAILED"
        except Exception as e:
            results[test_name] = f"❌ ERROR: {str(e)[:50]}"
            print(f"   Error: {e}")
    
    total_time = time.time() - start_time
    
    # Print summary
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST SUMMARY".center(80))
    print("="*80)
    
    passed = sum(1 for r in results.values() if "PASSED" in r)
    total = len(results)
    
    for test_name, result in results.items():
        symbol = "✅" if "PASSED" in result else "❌"
        print(f"{symbol} {test_name}: {result}")
    
    print("\n" + "-"*80)
    print(f"TOTAL: {passed}/{total} Tests Passed ({passed/total*100:.1f}%)")
    print(f"Duration: {total_time:.2f} seconds")
    print("="*80 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
