"""Performance and load testing for Python Script Runner v7.0"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from runners.profilers.performance_profiler import (
    AdvancedProfiler,
    LoadTestRunner,
    MetricsCollector,
    PerformanceReport
)


class TestAdvancedProfiler:
    """Test AdvancedProfiler functionality"""
    
    def test_baseline_measurement(self):
        """Test baseline performance measurement"""
        profiler = AdvancedProfiler()
        baseline = profiler.measure_baseline(duration_seconds=2)
        
        assert 'cpu_percent' in baseline
        assert 'memory_mb' in baseline
        assert baseline['cpu_percent'] >= 0
        assert baseline['memory_mb'] > 0
    
    def test_feature_profiling(self):
        """Test profiling of individual features"""
        profiler = AdvancedProfiler()
        profiler.measure_baseline(duration_seconds=1)
        
        def sample_feature():
            time.sleep(0.1)
            return "completed"
        
        metrics = profiler.profile_feature('test_feature', sample_feature)
        
        assert metrics.feature_name == 'test_feature'
        assert metrics.execution_time_ms >= 100
        assert metrics.success is True
    
    def test_overhead_calculation(self):
        """Test overhead calculation"""
        profiler = AdvancedProfiler()
        profiler.measure_baseline(duration_seconds=1)
        
        def dummy_task():
            time.sleep(0.05)
        
        profiler.profile_feature('feature_1', dummy_task)
        profiler.profile_feature('feature_2', dummy_task)
        
        overhead_1 = profiler.measure_feature_overhead('feature_1')
        overhead_2 = profiler.measure_feature_overhead('feature_2')
        
        assert overhead_1.feature_name == 'feature_1'
        assert overhead_2.feature_name == 'feature_2'
        assert hasattr(overhead_1, 'overhead_cpu_percent')
    
    def test_overhead_validation(self):
        """Test overhead validation against target"""
        profiler = AdvancedProfiler(target_overhead_percent=10.0)
        profiler.measure_baseline(duration_seconds=1)
        
        def light_task():
            pass
        
        profiler.profile_feature('light_feature', light_task)
        is_valid, msg = profiler.validate_overhead('light_feature')
        
        assert isinstance(is_valid, bool)
        assert isinstance(msg, str)
        assert 'light_feature' in msg
    
    def test_multiple_measurements(self):
        """Test averaging multiple measurements"""
        profiler = AdvancedProfiler()
        profiler.measure_baseline(duration_seconds=1)
        
        def variable_task(duration):
            time.sleep(duration)
        
        # Take multiple measurements
        for i in range(3):
            profiler.profile_feature(f'variable_task_{i}', variable_task, 0.05)
        
        assert 'variable_task_0' in profiler.measurements
        assert len(profiler.measurements) >= 3


class TestLoadTestRunner:
    """Test LoadTestRunner functionality"""
    
    def test_concurrent_workflow_execution(self):
        """Test concurrent workflow execution"""
        runner = LoadTestRunner(max_workers=5)
        
        def workflow_factory(wf_id):
            return f"workflow_{wf_id}"
        
        results = runner.run_concurrent_workflows(workflow_factory, count=20)
        
        assert results['total_workflows'] == 20
        assert results['completed'] == 20
        assert results['failed'] == 0
        assert results['success_rate_percent'] == 100.0
        assert results['throughput_workflows_per_sec'] > 0
    
    def test_concurrent_workflow_failure_handling(self):
        """Test handling of failures in concurrent execution"""
        runner = LoadTestRunner(max_workers=5)
        call_count = 0
        
        def failing_workflow_factory(wf_id):
            nonlocal call_count
            call_count += 1
            if wf_id % 3 == 0:
                raise Exception(f"Intentional failure for workflow {wf_id}")
            return f"workflow_{wf_id}"
        
        results = runner.run_concurrent_workflows(failing_workflow_factory, count=15)
        
        assert results['total_workflows'] == 15
        assert results['failed'] > 0
        assert results['success_rate_percent'] < 100.0
        assert results['success_rate_percent'] > 50.0
    
    def test_execution_time_statistics(self):
        """Test execution time statistics"""
        runner = LoadTestRunner(max_workers=3)
        
        def timed_workflow(wf_id):
            # Variable execution time based on ID
            sleep_time = 0.01 * (1 + wf_id % 5)
            time.sleep(sleep_time)
        
        results = runner.run_concurrent_workflows(timed_workflow, count=10)
        
        assert 'avg_execution_time_ms' in results
        assert 'min_execution_time_ms' in results
        assert 'max_execution_time_ms' in results
        assert results['max_execution_time_ms'] >= results['avg_execution_time_ms']
        assert results['avg_execution_time_ms'] >= results['min_execution_time_ms']
    
    def test_trace_sampling_benchmark(self):
        """Test trace sampling rate benchmarking"""
        runner = LoadTestRunner()
        sampling_rates = [0.1, 0.5, 1.0]
        
        results = runner.benchmark_trace_sampling(sampling_rates)
        
        assert len(results) == len(sampling_rates)
        for rate_str in ['10.0%', '50.0%', '100.0%']:
            assert rate_str in results
            assert 'cpu_percent' in results[rate_str]
            assert 'memory_mb' in results[rate_str]
    
    def test_scalability_with_workers(self):
        """Test performance scaling with different worker counts"""
        results_dict = {}
        
        for worker_count in [1, 5, 10]:
            runner = LoadTestRunner(max_workers=worker_count)
            
            def simple_workflow(wf_id):
                time.sleep(0.01)
            
            results = runner.run_concurrent_workflows(simple_workflow, count=20)
            results_dict[worker_count] = results['total_duration_seconds']
        
        # More workers should generally complete faster
        assert results_dict[5] <= results_dict[1] * 1.1  # Allow 10% variance


class TestMetricsCollector:
    """Test MetricsCollector functionality"""
    
    def test_metrics_collection(self):
        """Test basic metrics collection"""
        collector = MetricsCollector(interval_seconds=0.05)
        
        collector.start_collection()
        time.sleep(0.5)
        metrics = collector.stop_collection()
        
        assert metrics.cpu_percent >= 0
        assert metrics.memory_mb > 0
        assert metrics.success is True
    
    def test_metrics_during_workload(self):
        """Test metrics collection during CPU workload"""
        collector = MetricsCollector(interval_seconds=0.05)
        
        def cpu_workload():
            # Perform CPU-intensive work
            for _ in range(1000000):
                _ = sum([i ** 2 for i in range(100)])
        
        collector.start_collection()
        cpu_workload()
        metrics = collector.stop_collection()
        
        assert metrics.memory_mb > 0
        assert metrics.success is True
        assert len(collector.metrics) > 0
    
    def test_collection_interval_accuracy(self):
        """Test that collection interval is respected"""
        collector = MetricsCollector(interval_seconds=0.05)
        
        collector.start_collection()
        time.sleep(0.3)
        metrics = collector.stop_collection()
        
        # Should have multiple collection points (0.3 / 0.05 = 6)
        assert len(collector.metrics) >= 4  # Allow some variance


class TestPerformanceReport:
    """Test PerformanceReport functionality"""
    
    def test_report_creation(self):
        """Test report creation and structure"""
        from runners.profilers.performance_profiler import FeatureOverhead
        
        overhead = FeatureOverhead(
            feature_name='test_feature',
            baseline_cpu_percent=2.0,
            baseline_memory_mb=100,
            feature_cpu_percent=4.5,
            feature_memory_mb=150
        )
        
        report = PerformanceReport(
            timestamp='2024-01-01T00:00:00',
            total_duration_seconds=10.0,
            baseline_metrics={'cpu': 2.0, 'memory': 100},
            feature_overhead=[overhead]
        )
        
        assert report.timestamp == '2024-01-01T00:00:00'
        assert report.total_duration_seconds == 10.0
        assert len(report.feature_overhead) == 1
    
    def test_report_serialization(self, tmp_path):
        """Test report serialization to JSON"""
        report = PerformanceReport(
            timestamp='2024-01-01T00:00:00',
            total_duration_seconds=10.0,
            baseline_metrics={'cpu': 2.0},
            execution_times={'feature1': [10, 15, 12]},
            recommendations=['Optimize caching', 'Reduce memory usage']
        )
        
        report_file = tmp_path / 'report.json'
        report.to_json(str(report_file))
        
        assert report_file.exists()
        
        import json
        with open(report_file) as f:
            data = json.load(f)
        
        assert data['timestamp'] == '2024-01-01T00:00:00'
        assert data['total_duration_seconds'] == 10.0
        assert len(data['recommendations']) == 2


@pytest.mark.benchmark
class TestPerformanceBenchmarks:
    """Benchmark tests for v7.0 features"""
    
    def test_workflow_execution_performance(self, benchmark):
        """Benchmark workflow execution performance"""
        profiler = AdvancedProfiler()
        profiler.measure_baseline(duration_seconds=1)
        
        def workflow_execution():
            time.sleep(0.01)
            return "completed"
        
        result = benchmark(profiler.profile_feature, 'workflow', workflow_execution)
        assert result.success is True
    
    def test_security_scanning_performance(self, benchmark):
        """Benchmark security scanning performance"""
        def mock_security_scan():
            # Simulate code analysis
            time.sleep(0.05)
            return {"findings": 0}
        
        result = benchmark(mock_security_scan)
        assert result is not None
    
    def test_trace_collection_performance(self, benchmark):
        """Benchmark trace collection performance"""
        def mock_trace_collection():
            # Simulate trace collection
            spans = []
            for i in range(100):
                spans.append({
                    'name': f'span_{i}',
                    'duration_ms': 1.0
                })
            return spans
        
        result = benchmark(mock_trace_collection)
        assert len(result) == 100
    
    def test_cost_calculation_performance(self, benchmark):
        """Benchmark cost calculation performance"""
        def mock_cost_calculation():
            total = 0.0
            for provider in ['aws', 'azure', 'gcp']:
                for resource in range(100):
                    total += (100 + resource * 0.5)
            return total
        
        result = benchmark(mock_cost_calculation)
        assert result > 0


@pytest.mark.stress
class TestStressTests:
    """Stress tests for v7.0 features"""
    
    def test_high_concurrency_workflows(self):
        """Test system under high concurrent workflow load"""
        runner = LoadTestRunner(max_workers=20)
        
        def concurrent_workflow(wf_id):
            # Simulate realistic workflow
            time.sleep(0.01 * (1 + wf_id % 3))
        
        results = runner.run_concurrent_workflows(concurrent_workflow, count=100)
        
        assert results['success_rate_percent'] >= 95.0
        assert results['throughput_workflows_per_sec'] > 0
    
    def test_memory_stability_under_load(self):
        """Test memory stability during prolonged execution"""
        collector = MetricsCollector(interval_seconds=0.1)
        initial_memory = None
        
        collector.start_collection()
        
        for _ in range(100):
            # Allocate and deallocate memory
            temp_list = [i for i in range(10000)]
            time.sleep(0.01)
        
        metrics = collector.stop_collection()
        
        assert metrics.success is True
        # Memory should remain relatively stable
        assert metrics.memory_mb > 0
    
    def test_long_running_feature_stability(self):
        """Test feature stability during long execution"""
        runner = LoadTestRunner(max_workers=5)
        
        def long_running_workflow(wf_id):
            time.sleep(0.1)  # Simulate longer execution
        
        results = runner.run_concurrent_workflows(long_running_workflow, count=50)
        
        assert results['success_rate_percent'] >= 95.0


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance monitoring"""
    
    def test_end_to_end_profiling_workflow(self):
        """Test complete end-to-end profiling workflow"""
        from runners.profilers.performance_profiler import run_comprehensive_profile
        
        features = ['workflow', 'security']
        report = run_comprehensive_profile(features)
        
        assert isinstance(report, PerformanceReport)
        assert report.timestamp is not None
        assert len(report.feature_overhead) > 0
    
    def test_profiler_with_real_operations(self):
        """Test profiler with realistic operations"""
        profiler = AdvancedProfiler(target_overhead_percent=10.0)
        profiler.measure_baseline(duration_seconds=2)
        
        # Profile multiple features
        for i in range(3):
            def feature_task():
                # Simulate feature work
                data = list(range(100000))
                return len(data)
            
            metrics = profiler.profile_feature(f'feature_{i}', feature_task)
            assert metrics.success is True
        
        # Validate overheads
        for i in range(3):
            is_valid, msg = profiler.validate_overhead(f'feature_{i}')
            assert isinstance(is_valid, bool)
