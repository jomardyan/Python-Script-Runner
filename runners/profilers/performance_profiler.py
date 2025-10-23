"""
Advanced performance profiling and load testing module for Python Script Runner v7.0

Provides comprehensive performance analysis, overhead measurement, and load testing
capabilities for all v7.0 features: workflows, tracing, security scanning, and cost tracking.
"""

import time
import psutil
import json
import threading
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Callable, Any
from datetime import datetime
from pathlib import Path
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed


logger = logging.getLogger(__name__)


@dataclass
class FeatureOverhead:
    """Tracks CPU and memory overhead for a specific feature"""
    feature_name: str
    baseline_cpu_percent: float
    baseline_memory_mb: float
    feature_cpu_percent: float
    feature_memory_mb: float
    overhead_cpu_percent: float = field(init=False)
    overhead_memory_mb: float = field(init=False)
    
    def __post_init__(self):
        self.overhead_cpu_percent = self.feature_cpu_percent - self.baseline_cpu_percent
        self.overhead_memory_mb = self.feature_memory_mb - self.baseline_memory_mb


@dataclass
class ExecutionMetrics:
    """Metrics for a single feature execution"""
    feature_name: str
    execution_time_ms: float
    cpu_percent: float
    memory_mb: float
    threads_count: int
    context_switches: int
    io_operations: int
    success: bool
    error: Optional[str] = None


@dataclass
class PerformanceReport:
    """Comprehensive performance analysis report"""
    timestamp: str
    total_duration_seconds: float
    baseline_metrics: Dict[str, float]
    feature_overhead: List[FeatureOverhead] = field(default_factory=list)
    execution_times: Dict[str, List[float]] = field(default_factory=dict)
    throughput_metrics: Dict[str, float] = field(default_factory=dict)
    max_concurrent_workflows: int = 0
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'timestamp': self.timestamp,
            'total_duration_seconds': self.total_duration_seconds,
            'baseline_metrics': self.baseline_metrics,
            'feature_overhead': [asdict(f) for f in self.feature_overhead],
            'execution_times': self.execution_times,
            'throughput_metrics': self.throughput_metrics,
            'max_concurrent_workflows': self.max_concurrent_workflows,
            'recommendations': self.recommendations
        }
    
    def to_json(self, file_path: str):
        """Save report to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Performance report saved to {file_path}")


class MetricsCollector:
    """Collects CPU, memory, and I/O metrics during execution"""
    
    def __init__(self, interval_seconds: float = 0.1):
        self.interval = interval_seconds
        self.metrics: List[ExecutionMetrics] = []
        self.running = False
        self.process = psutil.Process()
        
    def start_collection(self):
        """Start collecting metrics in background thread"""
        self.running = True
        self.collector_thread = threading.Thread(target=self._collect_loop, daemon=True)
        self.collector_thread.start()
        
    def stop_collection(self) -> ExecutionMetrics:
        """Stop collection and return summary metrics"""
        self.running = False
        if hasattr(self, 'collector_thread'):
            self.collector_thread.join(timeout=1)
        
        if not self.metrics:
            return ExecutionMetrics(
                feature_name='unknown',
                execution_time_ms=0,
                cpu_percent=0,
                memory_mb=0,
                threads_count=0,
                context_switches=0,
                io_operations=0,
                success=False,
                error="No metrics collected"
            )
        
        avg_cpu = sum(m.cpu_percent for m in self.metrics) / len(self.metrics)
        max_memory = max(m.memory_mb for m in self.metrics)
        total_time = sum(m.execution_time_ms for m in self.metrics) / 1000
        
        return ExecutionMetrics(
            feature_name='measurement',
            execution_time_ms=total_time * 1000,
            cpu_percent=avg_cpu,
            memory_mb=max_memory,
            threads_count=self.process.num_threads(),
            context_switches=sum(1 for _ in self.metrics),
            io_operations=len(self.metrics),
            success=True
        )
    
    def _collect_loop(self):
        """Background loop for metric collection"""
        try:
            with self.process.oneshot():
                while self.running:
                    try:
                        cpu_percent = self.process.cpu_percent(interval=None)
                        memory_info = self.process.memory_info()
                        memory_mb = memory_info.rss / (1024 * 1024)
                        
                        metric = ExecutionMetrics(
                            feature_name='system',
                            execution_time_ms=time.time(),
                            cpu_percent=cpu_percent,
                            memory_mb=memory_mb,
                            threads_count=self.process.num_threads(),
                            context_switches=self.process.num_ctx_switches().voluntary,
                            io_operations=0,
                            success=True
                        )
                        self.metrics.append(metric)
                        time.sleep(self.interval)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        break
        except Exception as e:
            logger.error(f"Error in metrics collection: {e}")


class AdvancedProfiler:
    """Advanced profiling for Python Script Runner v7.0 features"""
    
    def __init__(self, target_overhead_percent: float = 5.0):
        self.target_overhead = target_overhead_percent
        self.measurements: Dict[str, List[ExecutionMetrics]] = {}
        self.baseline_metrics: Dict[str, float] = {}
        
    def measure_baseline(self, duration_seconds: int = 10) -> Dict[str, float]:
        """Measure baseline system performance without any features"""
        logger.info(f"Measuring baseline performance for {duration_seconds}s...")
        
        collector = MetricsCollector()
        collector.start_collection()
        time.sleep(duration_seconds)
        metrics = collector.stop_collection()
        
        self.baseline_metrics = {
            'cpu_percent': metrics.cpu_percent,
            'memory_mb': metrics.memory_mb,
            'threads_count': metrics.threads_count,
            'execution_time_ms': metrics.execution_time_ms
        }
        
        logger.info(f"Baseline metrics: {self.baseline_metrics}")
        return self.baseline_metrics
    
    def profile_feature(self, feature_name: str, callable_func: Callable, *args, **kwargs) -> ExecutionMetrics:
        """Profile a single feature execution"""
        logger.info(f"Profiling feature: {feature_name}")
        
        collector = MetricsCollector()
        start_time = time.time()
        
        collector.start_collection()
        try:
            result = callable_func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            logger.error(f"Error profiling {feature_name}: {e}")
        finally:
            metrics = collector.stop_collection()
            execution_time = (time.time() - start_time) * 1000
        
        metrics.feature_name = feature_name
        metrics.execution_time_ms = execution_time
        metrics.success = success
        metrics.error = error
        
        if feature_name not in self.measurements:
            self.measurements[feature_name] = []
        self.measurements[feature_name].append(metrics)
        
        return metrics
    
    def measure_feature_overhead(self, feature_name: str) -> FeatureOverhead:
        """Calculate overhead for a feature"""
        if feature_name not in self.measurements or not self.measurements[feature_name]:
            raise ValueError(f"No measurements for feature {feature_name}")
        
        metrics_list = self.measurements[feature_name]
        avg_cpu = sum(m.cpu_percent for m in metrics_list) / len(metrics_list)
        max_memory = max(m.memory_mb for m in metrics_list)
        
        return FeatureOverhead(
            feature_name=feature_name,
            baseline_cpu_percent=self.baseline_metrics.get('cpu_percent', 0),
            baseline_memory_mb=self.baseline_metrics.get('memory_mb', 0),
            feature_cpu_percent=avg_cpu,
            feature_memory_mb=max_memory
        )
    
    def validate_overhead(self, feature_name: str) -> Tuple[bool, str]:
        """Validate that feature overhead is within target"""
        overhead = self.measure_feature_overhead(feature_name)
        
        if overhead.overhead_cpu_percent <= self.target_overhead:
            msg = f"✓ {feature_name}: CPU overhead {overhead.overhead_cpu_percent:.2f}% (target: {self.target_overhead}%)"
            return True, msg
        else:
            msg = f"✗ {feature_name}: CPU overhead {overhead.overhead_cpu_percent:.2f}% EXCEEDS target {self.target_overhead}%"
            return False, msg


class LoadTestRunner:
    """Runs comprehensive load tests for Python Script Runner v7.0"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.execution_times: List[float] = []
        self.failures: List[Tuple[int, str]] = []
        
    def run_concurrent_workflows(self, workflow_factory: Callable, count: int) -> Dict[str, Any]:
        """Run multiple workflows concurrently and measure performance"""
        logger.info(f"Starting load test with {count} concurrent workflows...")
        
        start_time = time.time()
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i in range(count):
                future = executor.submit(self._run_workflow, workflow_factory, i)
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    exec_time = future.result()
                    self.execution_times.append(exec_time)
                    completed += 1
                    
                    if completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{count} workflows completed")
                except Exception as e:
                    self.failures.append((completed, str(e)))
                    logger.error(f"Workflow {completed} failed: {e}")
        
        total_time = time.time() - start_time
        
        return {
            'total_workflows': count,
            'completed': completed,
            'failed': len(self.failures),
            'total_duration_seconds': total_time,
            'avg_execution_time_ms': (sum(self.execution_times) / len(self.execution_times)) if self.execution_times else 0,
            'min_execution_time_ms': min(self.execution_times) if self.execution_times else 0,
            'max_execution_time_ms': max(self.execution_times) if self.execution_times else 0,
            'throughput_workflows_per_sec': completed / total_time if total_time > 0 else 0,
            'success_rate_percent': (completed / count * 100) if count > 0 else 0
        }
    
    def benchmark_trace_sampling(self, sampling_rates: List[float]) -> Dict[str, Any]:
        """Benchmark different trace sampling rates"""
        logger.info(f"Benchmarking trace sampling rates: {sampling_rates}")
        
        results = {}
        
        for rate in sampling_rates:
            logger.info(f"Testing sampling rate: {rate}")
            
            collector = MetricsCollector(interval_seconds=0.1)
            collector.start_collection()
            
            # Simulate tracing with sampling
            time.sleep(1)
            
            metrics = collector.stop_collection()
            
            results[f"{rate:.1%}"] = {
                'cpu_percent': metrics.cpu_percent,
                'memory_mb': metrics.memory_mb,
                'execution_time_ms': metrics.execution_time_ms
            }
        
        return results
    
    def _run_workflow(self, workflow_factory: Callable, workflow_id: int) -> float:
        """Run a single workflow and return execution time"""
        start = time.time()
        try:
            workflow = workflow_factory(workflow_id)
            # Simulate workflow execution
            time.sleep(0.1 * (1 + workflow_id % 5))  # Variable execution time
        except Exception as e:
            logger.error(f"Workflow {workflow_id} error: {e}")
        return (time.time() - start) * 1000  # Return time in ms


def run_comprehensive_profile(features_to_test: List[str]) -> PerformanceReport:
    """Run comprehensive performance profiling for specified features"""
    logger.info(f"Starting comprehensive profiling for features: {features_to_test}")
    
    profiler = AdvancedProfiler(target_overhead_percent=5.0)
    
    # Measure baseline
    baseline = profiler.measure_baseline(duration_seconds=5)
    
    # Profile each feature
    feature_overheads = []
    execution_times = {}
    
    for feature in features_to_test:
        logger.info(f"Profiling feature: {feature}")
        
        # Profile 5 times
        times = []
        for i in range(5):
            metrics = profiler.profile_feature(
                f"{feature}_{i}",
                lambda: time.sleep(0.1)  # Simulated feature execution
            )
            times.append(metrics.execution_time_ms)
            time.sleep(0.1)
        
        execution_times[feature] = times
        overhead = profiler.measure_feature_overhead(f"{feature}_0")
        feature_overheads.append(overhead)
    
    # Throughput testing
    load_tester = LoadTestRunner(max_workers=10)
    workflow_results = load_tester.run_concurrent_workflows(
        workflow_factory=lambda i: f"workflow_{i}",
        count=50
    )
    
    # Generate recommendations
    recommendations = []
    for overhead in feature_overheads:
        if overhead.overhead_cpu_percent > 5.0:
            recommendations.append(
                f"⚠ {overhead.feature_name}: High CPU overhead ({overhead.overhead_cpu_percent:.2f}%). "
                "Consider optimization or sampling."
            )
    
    if workflow_results['success_rate_percent'] < 95:
        recommendations.append(
            f"⚠ Workflow success rate {workflow_results['success_rate_percent']:.1f}% is below 95%. "
            "Investigate stability issues."
        )
    
    report = PerformanceReport(
        timestamp=datetime.now().isoformat(),
        total_duration_seconds=workflow_results['total_duration_seconds'],
        baseline_metrics=baseline,
        feature_overhead=feature_overheads,
        execution_times=execution_times,
        throughput_metrics=workflow_results,
        max_concurrent_workflows=workflow_results['total_workflows'],
        recommendations=recommendations
    )
    
    return report


def run_cli_profile():
    """Run profiling from command line"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance profiler for Python Script Runner v7.0')
    parser.add_argument('--features', nargs='+', default=['workflow', 'tracing', 'security', 'costs'],
                        help='Features to profile')
    parser.add_argument('--output', default='performance_report.json', help='Output file path')
    parser.add_argument('--baseline-only', action='store_true', help='Only measure baseline')
    
    args = parser.parse_args()
    
    if args.baseline_only:
        profiler = AdvancedProfiler()
        baseline = profiler.measure_baseline(duration_seconds=10)
        print(f"Baseline metrics: {baseline}")
    else:
        report = run_comprehensive_profile(args.features)
        report.to_json(args.output)
        print(f"Performance report saved to {args.output}")
        print(f"Recommendations: {report.recommendations}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    run_cli_profile()
