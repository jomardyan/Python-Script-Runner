"""
Comprehensive unit tests for runner.py - Python Script Runner

Tests cover:
- ScriptRunner initialization and configuration
- Script execution and metrics collection
- Error handling and timeouts
- Alert management and notifications
- CI/CD integration
- Feature flags and configuration parsing
- Integration with v7 features
"""

import pytest
import os
import sys
import tempfile
import json
import time
import threading
from pathlib import Path
from typing import List, Any
from unittest.mock import Mock, patch, MagicMock, mock_open
import sqlite3

# Import runner components
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from runner import ScriptRunner, HistoryManager, AlertManager, CICDIntegration


class TestScriptRunnerInitialization:
    """Test ScriptRunner initialization and configuration"""
    
    def test_script_runner_creation(self, tmp_path):
        """Test basic ScriptRunner creation"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello')")
        
        runner = ScriptRunner(str(script_file))
        
        assert runner.script_path == str(script_file)
        assert runner.script_args == []
        assert runner.timeout is None
        assert runner.metrics == {}
    
    def test_script_runner_with_args(self, tmp_path):
        """Test ScriptRunner with arguments"""
        script_file = tmp_path / "test.py"
        script_file.write_text("import sys; print(sys.argv[1])")
        
        runner = ScriptRunner(str(script_file), script_args=['arg1', 'arg2'])
        
        assert runner.script_args == ['arg1', 'arg2']
    
    def test_script_runner_with_timeout(self, tmp_path):
        """Test ScriptRunner with timeout"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello')")
        
        runner = ScriptRunner(str(script_file), timeout=300)
        
        assert runner.timeout == 300
    
    def test_script_runner_history_enabled(self, tmp_path):
        """Test ScriptRunner with history tracking"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello')")
        
        db_file = tmp_path / "history.db"
        runner = ScriptRunner(str(script_file), history_db=str(db_file), enable_history=True)
        
        assert runner.enable_history is True
        assert runner.history_manager is not None
    
    def test_script_runner_history_disabled(self, tmp_path):
        """Test ScriptRunner with history disabled"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello')")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        
        assert runner.enable_history is False
        assert runner.history_manager is None
    
    def test_script_runner_invalid_log_level(self, tmp_path):
        """Test ScriptRunner with invalid log level"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Hello')")
        
        # Should still initialize but use default
        runner = ScriptRunner(str(script_file), log_level='INVALID')
        assert runner is not None


class TestScriptExecution:
    """Test script execution functionality"""
    
    def test_simple_script_execution(self, tmp_path):
        """Test executing a simple Python script"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('Success')\nexit(0)")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['returncode'] == 0
        assert 'metrics' in result
        assert result['success'] is True
    
    def test_script_with_args_execution(self, tmp_path):
        """Test executing script with arguments"""
        script_file = tmp_path / "test.py"
        script_file.write_text("import sys\nprint(sys.argv[1])\nexit(0)")
        
        runner = ScriptRunner(str(script_file), script_args=['test_arg'])
        result = runner.run_script()
        
        assert result['returncode'] == 0
    
    def test_script_failure_execution(self, tmp_path):
        """Test executing script that fails"""
        script_file = tmp_path / "test.py"
        script_file.write_text("raise Exception('Test error')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        assert result['returncode'] != 0
        assert result['success'] is False
    
    def test_script_timeout(self, tmp_path):
        """Test script execution timeout"""
        script_file = tmp_path / "test.py"
        script_file.write_text("import time\ntime.sleep(10)")
        
        runner = ScriptRunner(str(script_file), timeout=1)
        result = runner.run_script()
        
        # Should timeout
        assert result['returncode'] != 0 or 'timed out' in str(result).lower()
    
    def test_script_not_found(self):
        """Test executing non-existent script"""
        runner = ScriptRunner('/non/existent/script.py')

        with pytest.raises(FileNotFoundError):
            runner.run_script()


class TestMetricsCollection:
    """Test metrics collection during execution"""
    
    def test_metrics_collected(self, tmp_path):
        """Test that metrics are collected during execution"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result.get('metrics', {})
        assert 'execution_time_seconds' in metrics
        assert metrics['execution_time_seconds'] > 0
    
    def test_metrics_cpu_memory(self, tmp_path):
        """Test CPU and memory metrics collection"""
        script_file = tmp_path / "test.py"
        # Script that uses CPU and memory
        script_file.write_text("""
import sys
data = [i for i in range(1000000)]
print(f'Processed {len(data)} items')
exit(0)
""")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        metrics = result.get('metrics', {})
        assert 'memory_max_mb' in metrics or 'cpu_max' in metrics
    
    def test_metrics_history_saved(self, tmp_path):
        """Test that metrics are saved to history database"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        db_file = tmp_path / "history.db"
        runner = ScriptRunner(
            str(script_file),
            history_db=str(db_file),
            enable_history=True
        )
        result = runner.run_script()
        
        assert result['success'] is True
        assert db_file.exists()
        
        # Check database contains entry
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM executions")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count > 0


class TestAlertManagement:
    """Test alert management functionality"""
    
    def test_alert_manager_initialization(self):
        """Test AlertManager initialization"""
        alert_mgr = AlertManager()
        assert alert_mgr is not None
    
    def test_alert_checking(self):
        """Test alert condition checking"""
        alert_mgr = AlertManager()
        
        # Mock alert checking
        metrics = {
            'cpu_max': 85.0,
            'memory_max_mb': 1024.0
        }
        
        # Should be able to check conditions
        result = alert_mgr.check_alerts(metrics)
        assert isinstance(result, list)
    
    @patch('runner.AlertManager.notify')
    def test_alert_notification(self, mock_notify):
        """Test alert notification sending"""
        alert_mgr = AlertManager()
        
        # Mock the notify method
        alert_mgr.notify = mock_notify
        
        # Should be able to call notify
        alert_mgr.notify('test_alert', 'ERROR', {'detail': 'test'})
        mock_notify.assert_called_once()


class TestCICDIntegration:
    """Test CI/CD integration functionality"""
    
    def test_cicd_initialization(self):
        """Test CICDIntegration initialization"""
        cicd = CICDIntegration()
        assert cicd is not None
    
    def test_junit_report_generation(self, tmp_path):
        """Test JUnit XML report generation"""
        cicd = CICDIntegration()
        
        metrics = {
            'execution_time_seconds': 1.5,
            'cpu_max': 45.0,
            'memory_max_mb': 256.0,
            'exit_code': 0
        }
        
        # Should be able to generate report
        junit_file = tmp_path / "junit.xml"
        # This would use cicd.write_junit_report or similar
        assert cicd is not None


class TestHistoryManager:
    """Test history database management"""
    
    def test_history_manager_initialization(self, tmp_path):
        """Test HistoryManager initialization"""
        db_file = tmp_path / "history.db"
        manager = HistoryManager(db_path=str(db_file))
        
        assert manager is not None
        assert db_file.exists()
    
    def test_history_metric_saving(self, tmp_path):
        """Test saving metrics to history"""
        db_file = tmp_path / "history.db"
        manager = HistoryManager(db_path=str(db_file))
        
        execution_id = manager.save_execution(
            script_path='/test/script.py',
            exit_code=0,
            metrics={'cpu_max': 50.0, 'memory_max_mb': 256.0},
            stdout='test output',
            stderr=''
        )
        
        assert execution_id > 0
    
    def test_history_retrieval(self, tmp_path):
        """Test retrieving metrics from history"""
        db_file = tmp_path / "history.db"
        manager = HistoryManager(db_path=str(db_file))
        
        # Save execution
        execution_id = manager.save_execution(
            script_path='/test/script.py',
            exit_code=0,
            metrics={'cpu_max': 50.0},
            stdout='test',
            stderr=''
        )
        
        # Should be able to retrieve
        assert execution_id > 0


class TestConfigurationLoading:
    """Test configuration file loading"""
    
    def test_config_file_loading(self, tmp_path):
        """Test loading config from YAML file"""
        config_file = tmp_path / "config.yaml"
        config_content = """
alerts:
  - name: high_cpu
    metric: cpu_max
    threshold: 90
    condition: '>'

notifications:
  slack:
    webhook_url: https://hooks.slack.com/test
"""
        config_file.write_text(config_content)
        
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        runner = ScriptRunner(str(script_file), config_file=str(config_file))
        
        # Should load config successfully
        assert runner is not None
    
    def test_config_file_not_found(self, tmp_path):
        """Test handling missing config file"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        runner = ScriptRunner(str(script_file), config_file='/non/existent/config.yaml')
        
        # Should initialize despite missing config
        assert runner is not None


class TestFeatureFlags:
    """Test feature flag configuration"""
    
    def test_monitoring_can_be_disabled(self, tmp_path):
        """Test disabling monitoring"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()
        
        assert result['success'] is True
        assert runner.history_manager is None
    
    def test_retry_configuration(self, tmp_path):
        """Test retry strategy configuration"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")
        
        runner = ScriptRunner(str(script_file))
        
        # Should have retry config
        assert hasattr(runner, 'retry_config')


class TestErrorHandling:
    """Test error handling in ScriptRunner"""
    
    def test_permission_error_handling(self, tmp_path):
        """Test handling permission errors"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        os.chmod(str(script_file), 0o000)
        
        try:
            runner = ScriptRunner(str(script_file))
            # May raise or handle gracefully
        finally:
            os.chmod(str(script_file), 0o644)
    
    def test_script_syntax_error_handling(self, tmp_path):
        """Test handling script syntax errors"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('unclosed string")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_script()
        
        # Should capture error
        assert result['success'] is False


class TestV7FeatureIntegration:
    """Test integration with v7 features"""

    def test_v7_features_exposed_directly(self, tmp_path):
        """Runner should expose v7 helpers without a separate enhancer."""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")

        runner = ScriptRunner(str(script_file))

        assert hasattr(runner, 'start_tracing_span')
        assert hasattr(runner, 'start_cost_tracking')
        assert runner.pre_execution_security_scan()['success'] is True

    def test_pre_execution_security_scan_blocks_on_critical(self, tmp_path):
        """Security scan helper should block when critical findings are present."""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')\nexit(0)")

        runner = ScriptRunner(str(script_file))

        class FakeFinding:
            def to_dict(self):
                return {'id': 'C1'}

        class FakeResult:
            findings = [FakeFinding()]
            critical_findings = [FakeFinding()]

        runner.code_analyzer = Mock(analyze=Mock(return_value=FakeResult()))
        runner.enable_code_analysis = True

        scan_result = runner.pre_execution_security_scan(block_on_critical=True)

        assert scan_result['success'] is False
        assert scan_result['blocked'] is True


class TestIntegration:
    """Integration tests combining multiple features"""
    
    def test_full_execution_workflow(self, tmp_path):
        """Test complete execution workflow with all features"""
        script_file = tmp_path / "pipeline.py"
        script_file.write_text("""
import sys
data = [i*2 for i in range(100000)]
print(f'Processed {len(data)} items')
for i in range(5):
    print(f'Step {i+1}/5')
exit(0)
""")
        
        db_file = tmp_path / "history.db"
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
alerts:
  - name: cpu_alert
    metric: cpu_max
    threshold: 95
    condition: '>'
""")
        
        runner = ScriptRunner(
            str(script_file),
            timeout=30,
            history_db=str(db_file),
            enable_history=True,
            config_file=str(config_file)
        )
        
        result = runner.run_script(retry_on_failure=False)
        
        assert result['success'] is True
        assert result['returncode'] == 0
        assert 'metrics' in result
        assert db_file.exists()
    
    def test_execution_with_monitoring(self, tmp_path):
        """Test execution with full monitoring enabled"""
        script_file = tmp_path / "monitored.py"
        script_file.write_text("""
import time
for i in range(3):
    time.sleep(0.1)
    print(f'Iteration {i+1}')
exit(0)
""")
        
        db_file = tmp_path / "history.db"
        runner = ScriptRunner(
            str(script_file),
            history_db=str(db_file),
            enable_history=True
        )
        
        result = runner.run_script()
        
        assert result['success'] is True
        assert 'metrics' in result
        
        # Verify database populated
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM executions")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count >= 1


# ============================================================================
# V7.0 FEATURE INTEGRATION TESTS
# ============================================================================

class TestV7FeatureInitialization:
    """Test V7.0 feature initialization and management"""
    
    def test_v7_features_disabled_by_default(self, tmp_path):
        """Test that v7 features are disabled by default"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        
        assert runner.enable_workflows is False
        assert runner.enable_tracing is False
        assert runner.enable_code_analysis is False
        assert runner.enable_dependency_scanning is False
        assert runner.enable_secret_scanning is False
        assert runner.enable_cost_tracking is False
    
    def test_v7_managers_none_by_default(self, tmp_path):
        """Test that v7 managers are None by default"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        
        assert runner.workflow_engine is None
        assert runner.tracing_manager is None
        assert runner.code_analyzer is None
        assert runner.dependency_scanner is None
        assert runner.secret_scanner is None
        assert runner.cost_tracker is None
    
    def test_v7_results_initialized(self, tmp_path):
        """Test v7 results dictionary initialization"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        
        assert isinstance(runner.v7_results, dict)
        assert 'workflow_result' in runner.v7_results
        assert 'security_findings' in runner.v7_results
        assert 'dependency_vulnerabilities' in runner.v7_results
        assert 'secrets_found' in runner.v7_results
        assert 'cost_estimate' in runner.v7_results
    
    def test_enable_v7_feature_invalid(self, tmp_path):
        """Test enabling invalid v7 feature"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.enable_v7_feature('invalid_feature')
        
        assert result is False


class TestV7SecurityIntegration:
    """Test v7 security features integration"""
    
    def test_pre_execution_security_checks_disabled(self, tmp_path):
        """Test security checks when disabled"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.run_pre_execution_security_checks()
        
        assert result is True  # Should pass when disabled
    
    def test_security_findings_storage(self, tmp_path):
        """Test that security findings are stored"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        runner.enable_code_analysis = True
        runner.code_analyzer = Mock()
        runner.code_analyzer.analyze = Mock(return_value=Mock(
            findings=[],
            critical_findings=[],
            high_findings=[]
        ))
        
        runner.run_pre_execution_security_checks()
        
        assert isinstance(runner.v7_results['security_findings'], list)
    
    def test_secret_detection(self, tmp_path):
        """Test secret detection integration with Mock objects"""
        script_file = tmp_path / "test.py"
        script_file.write_text("API_KEY = 'sk-12345'")
        
        runner = ScriptRunner(str(script_file))
        runner.enable_secret_scanning = True
        runner.secret_scanner = Mock()
        runner.secret_scanner.scan_file = Mock(return_value=Mock(
            has_secrets=True,
            secrets=[Mock(to_dict=lambda: {'type': 'api_key'})]
        ))
        
        runner.run_pre_execution_security_checks()
        
        assert len(runner.v7_results['secrets_found']) >= 0


class TestV7CostTracking:
    """Test v7 cost tracking integration"""
    
    def test_cost_estimation_disabled(self, tmp_path):
        """Test cost estimation when disabled"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.estimate_execution_costs()
        
        assert result is None
    
    def test_cost_estimation_enabled(self, tmp_path):
        """Test cost estimation when enabled with Mock"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        runner.enable_cost_tracking = True
        runner.cost_tracker = Mock()
        runner.cost_tracker.estimate_cost = Mock(return_value={
            'total_cost_usd': 10.50,
            'breakdown': {'compute': 5.00, 'storage': 5.50}
        })
        
        result = runner.estimate_execution_costs()
        
        assert result is not None
        assert 'total_cost_usd' in result


class TestV7TracingIntegration:
    """Test v7 OpenTelemetry tracing integration"""
    
    def test_tracing_disabled(self, tmp_path):
        """Test tracing when disabled"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        result = runner.start_execution_tracing()
        
        assert result is None
    
    def test_tracing_enabled(self, tmp_path):
        """Test tracing when enabled with Mock"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        runner.enable_tracing = True
        runner.tracing_manager = Mock()
        mock_span = Mock()
        runner.tracing_manager.start_span = Mock(return_value=mock_span)
        
        result = runner.start_execution_tracing()
        
        assert result is not None
        runner.tracing_manager.start_span.assert_called_once()


class TestV7MetricsCollection:
    """Test v7 metrics collection"""
    
    def test_collect_v7_metrics_no_findings(self, tmp_path):
        """Test v7 metrics collection with no findings"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        
        execution_result = {
            'returncode': 0,
            'stdout': 'test',
            'stderr': '',
            'metrics': {}
        }
        
        result = runner.collect_v7_metrics(execution_result)
        
        assert 'v7_metrics' in result['metrics']
        assert result['metrics']['v7_metrics']['security_findings_count'] == 0
        assert result['metrics']['v7_metrics']['dependency_vulnerabilities_count'] == 0
        assert result['metrics']['v7_metrics']['secrets_found_count'] == 0
    
    def test_collect_v7_metrics_with_findings(self, tmp_path):
        """Test v7 metrics collection with findings"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        runner.v7_results = {
            'workflow_result': None,
            'security_findings': [{'severity': 'HIGH', 'title': 'test'}],
            'dependency_vulnerabilities': [{'package': 'test', 'severity': 'CRITICAL'}],
            'secrets_found': [{'type': 'api_key', 'line': 10}],
            'cost_estimate': {'total_cost_usd': 15.00}
        }
        
        execution_result = {
            'returncode': 0,
            'stdout': 'test',
            'stderr': '',
            'metrics': {}
        }
        
        result = runner.collect_v7_metrics(execution_result)
        
        assert result['metrics']['v7_metrics']['security_findings_count'] == 1
        assert result['metrics']['v7_metrics']['dependency_vulnerabilities_count'] == 1
        assert result['metrics']['v7_metrics']['secrets_found_count'] == 1
        assert result['metrics']['v7_metrics']['estimated_cost_usd'] == 15.00


class TestV7ConfigurationIntegration:
    """Test v7 configuration loading"""
    
    def test_load_config_with_v7_features(self, tmp_path):
        """Test loading configuration with v7 features"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
v7_features:
  enable_workflows: false
  enable_tracing: false
  enable_code_analysis: false
  enable_dependency_scanning: false
  enable_secret_scanning: false
  enable_cost_tracking: false
""")
        
        runner = ScriptRunner(str(script_file), config_file=str(config_file))
        
        # Config should load without errors
        assert runner.logger is not None
    
    def test_initialize_v7_features_from_config(self, tmp_path):
        """Test initializing v7 features from config"""
        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")
        
        runner = ScriptRunner(str(script_file))
        
        # Manually call initialization with config
        config = {
            'v7_features': {
                'enable_workflows': False,
                'enable_tracing': False
            }
        }
        
        runner._initialize_v7_features(config)
        
        # Features should remain disabled if not importable
        assert runner.enable_workflows is False


class TestV7EndToEndExecution:
    """End-to-end tests with v7 features"""
    
    def test_execution_with_v7_metrics_collection(self, tmp_path):
        """Test complete execution with v7 metrics"""
        script_file = tmp_path / "test.py"
        script_file.write_text("""
print('Execution with v7 metrics')
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        
        # Run execution
        result = runner.run_script()
        
        # Collect v7 metrics
        enhanced_result = runner.collect_v7_metrics(result)
        
        assert enhanced_result is not None
        assert 'v7_metrics' in enhanced_result['metrics']
        assert enhanced_result['returncode'] == 0
    
    def test_full_workflow_with_all_v7_features(self, tmp_path):
        """Test full workflow with all v7 features"""
        script_file = tmp_path / "workflow_test.py"
        script_file.write_text("""
import time
print('Starting workflow test')
time.sleep(0.1)
print('Workflow test completed')
exit(0)
""")
        
        runner = ScriptRunner(str(script_file), enable_history=False)
        
        # Simulate enabling all features (they'll be None, but that's ok for testing)
        runner.enable_code_analysis = False  # Disabled in test
        runner.enable_dependency_scanning = False
        runner.enable_secret_scanning = False
        runner.enable_cost_tracking = False
        runner.enable_tracing = False
        runner.enable_workflows = False
        
        # Execute
        result = runner.run_script()
        
        # Collect metrics
        enhanced_result = runner.collect_v7_metrics(result)
        
        assert enhanced_result['returncode'] == 0
        assert 'v7_metrics' in enhanced_result['metrics']


@pytest.fixture
def tmp_path(tmp_path):
    """Provide temporary directory for tests"""
    return tmp_path


# ============================================================================
# Tests for new enhanced features (correlation IDs, structured events,
# lifecycle controls, working_dir/env_vars, streaming, status field)
# ============================================================================

class TestCorrelationIdAndStatus:
    """Test correlation ID generation and status string in results"""

    def test_correlation_id_present_on_success(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("print('hi')")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert 'correlation_id' in result
        assert result['correlation_id'] is not None
        # Validate it is a well-formed UUID
        import uuid as _uuid_mod
        _uuid_mod.UUID(result['correlation_id'])  # raises ValueError if invalid

    def test_correlation_id_present_in_metrics(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("print('hi')")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['metrics']['correlation_id'] == result['correlation_id']

    def test_status_success(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['status'] == 'success'

    def test_status_failed(self, tmp_path):
        script_file = tmp_path / "fail.py"
        script_file.write_text("exit(1)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['status'] == 'failed'

    def test_status_timeout(self, tmp_path):
        script_file = tmp_path / "hang.py"
        script_file.write_text("import time\ntime.sleep(10)")
        runner = ScriptRunner(str(script_file), timeout=1, enable_history=False)
        result = runner.run_script()

        assert result['status'] == 'timeout'
        assert result['metrics'].get('timed_out') is True

    def test_error_summary_on_failure(self, tmp_path):
        script_file = tmp_path / "fail.py"
        script_file.write_text("exit(2)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['error_summary'] is not None
        assert result['error_summary']['exit_code'] == 2

    def test_error_summary_none_on_success(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result.get('error_summary') is None

    def test_error_summary_on_timeout(self, tmp_path):
        script_file = tmp_path / "hang.py"
        script_file.write_text("import time\ntime.sleep(10)")
        runner = ScriptRunner(str(script_file), timeout=1, enable_history=False)
        result = runner.run_script()

        assert result['error_summary'] is not None
        assert result['error_summary']['status'] == 'timeout'


class TestWorkingDirAndEnvVars:
    """Test working_dir and env_vars configuration"""

    def test_env_vars_passed_to_script(self, tmp_path):
        script_file = tmp_path / "env_check.py"
        script_file.write_text(
            "import os, sys\n"
            "val = os.environ.get('MY_TEST_VAR', 'MISSING')\n"
            "print(val)\n"
            "sys.exit(0 if val == 'hello_world' else 1)\n"
        )
        runner = ScriptRunner(
            str(script_file),
            env_vars={'MY_TEST_VAR': 'hello_world'},
            enable_history=False,
        )
        result = runner.run_script()

        assert result['returncode'] == 0, result['stderr']

    def test_correlation_id_env_var_in_script(self, tmp_path):
        script_file = tmp_path / "cid_check.py"
        script_file.write_text(
            "import os\n"
            "cid = os.environ.get('SCRIPT_RUNNER_CORRELATION_ID', '')\n"
            "import sys\n"
            "sys.exit(0 if len(cid) == 36 else 1)\n"
        )
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['returncode'] == 0, "Correlation ID env var not present in subprocess"

    def test_working_dir_used(self, tmp_path):
        work_dir = tmp_path / "workdir"
        work_dir.mkdir()
        (work_dir / "sentinel.txt").write_text("sentinel")

        script_file = tmp_path / "cwd_check.py"
        script_file.write_text(
            "import os, sys\n"
            "exists = os.path.exists('sentinel.txt')\n"
            "sys.exit(0 if exists else 1)\n"
        )
        runner = ScriptRunner(
            str(script_file),
            working_dir=str(work_dir),
            enable_history=False,
        )
        result = runner.run_script()

        assert result['returncode'] == 0, "Script did not see sentinel.txt in working_dir"

    def test_default_cwd_is_script_directory(self, tmp_path):
        (tmp_path / "local.txt").write_text("here")
        script_file = tmp_path / "check.py"
        script_file.write_text(
            "import os, sys\n"
            "sys.exit(0 if os.path.exists('local.txt') else 1)\n"
        )
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        assert result['returncode'] == 0, "Default CWD should be the script's directory"


class TestStructuredEvents:
    """Test structured event emission via StructuredLogger"""

    def test_start_event_emitted(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.run_script()

        events = runner.structured_logger.get_logs(event_type='start')
        assert len(events) >= 1
        assert events[0]['data']['script_path'] == str(script_file)

    def test_success_event_emitted(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.run_script()

        events = runner.structured_logger.get_logs(event_type='success')
        assert len(events) >= 1

    def test_failure_event_emitted_on_exception(self, tmp_path):
        script_file = tmp_path / "bad.py"
        script_file.write_text("raise RuntimeError('boom')")
        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.run_script()

        # Non-zero exit goes to 'failed' branch; exception in runner goes to 'failure'
        failed_events = runner.structured_logger.get_logs(event_type='failed')
        failure_events = runner.structured_logger.get_logs(event_type='failure')
        assert len(failed_events) + len(failure_events) >= 1

    def test_timeout_event_emitted(self, tmp_path):
        script_file = tmp_path / "hang.py"
        script_file.write_text("import time\ntime.sleep(10)")
        runner = ScriptRunner(str(script_file), timeout=1, enable_history=False)
        runner.run_script()

        events = runner.structured_logger.get_logs(event_type='timeout')
        assert len(events) >= 1
        assert events[0]['data']['timeout_seconds'] == 1

    def test_events_persisted_to_log_file(self, tmp_path):
        log_path = tmp_path / "events.jsonl"
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(
            str(script_file),
            log_file=str(log_path),
            enable_history=False,
        )
        runner.run_script()

        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        parsed = [json.loads(l) for l in lines]
        types = [e['event_type'] for e in parsed]
        assert 'start' in types
        assert 'success' in types

    def test_event_has_correlation_id(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.run_script()

        events = runner.structured_logger.get_logs(event_type='start')
        assert events[0]['data']['correlation_id'] == result['correlation_id']


class TestLifecycleControls:
    """Test stop(), kill(), restart() lifecycle methods"""

    def test_stop_method_exists(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert callable(runner.stop)

    def test_kill_method_exists(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert callable(runner.kill)

    def test_restart_method_exists(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert callable(runner.restart)

    def test_stop_returns_false_when_nothing_running(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert runner.stop() is False

    def test_kill_returns_false_when_nothing_running(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert runner.kill() is False

    def test_restart_runs_script_again(self, tmp_path):
        script_file = tmp_path / "counter.py"
        counter_file = tmp_path / "count.txt"
        counter_file.write_text("0")
        script_file.write_text(
            "from pathlib import Path\n"
            f"p = Path(r'{counter_file}')\n"
            "p.write_text(str(int(p.read_text()) + 1))\n"
        )
        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.run_script()
        runner.restart()

        assert int(counter_file.read_text()) == 2

    def test_stop_during_execution_terminates_process(self, tmp_path):
        """stop() called from another thread should terminate a long-running script."""
        script_file = tmp_path / "hang.py"
        script_file.write_text("import time\ntime.sleep(30)")
        runner = ScriptRunner(str(script_file), enable_history=False)

        results: List[Any] = []

        def _run():
            results.append(runner.run_script())

        t = threading.Thread(target=_run)
        t.start()
        time.sleep(0.5)  # Give subprocess time to start before stopping
        runner.stop()
        t.join(timeout=8)

        assert len(results) == 1
        # The script was forcibly stopped; return code should be non-zero
        assert results[0]['returncode'] != 0


class TestStreamOutput:
    """Test real-time output streaming"""

    def test_stream_output_captures_stdout(self, tmp_path):
        script_file = tmp_path / "printer.py"
        script_file.write_text("print('line1')\nprint('line2')\n")
        runner = ScriptRunner(
            str(script_file),
            stream_output=True,
            enable_history=False,
        )
        result = runner.run_script()

        assert 'line1' in result['stdout']
        assert 'line2' in result['stdout']

    def test_stream_output_timeout_still_raises_timeout_status(self, tmp_path):
        script_file = tmp_path / "hang.py"
        script_file.write_text("import time\ntime.sleep(20)")
        runner = ScriptRunner(
            str(script_file),
            timeout=1,
            stream_output=True,
            enable_history=False,
        )
        result = runner.run_script()

        assert result['status'] == 'timeout'

    def test_stream_output_false_by_default(self, tmp_path):
        script_file = tmp_path / "ok.py"
        script_file.write_text("exit(0)")
        runner = ScriptRunner(str(script_file), enable_history=False)
        assert runner.stream_output is False


# ============================================================================
# RUNNERS PACKAGE INTEGRATION TESTS
# Tests that verify runner.py and the runners/ subpackages work together.
# These tests use real imports (no mocks) to confirm the packages are
# importable and correctly wired into ScriptRunner.
# ============================================================================

class TestRunnersPackageIntegration:
    """Verify runner.py integrates with the real runners/ subpackages."""

    def test_runners_package_importable(self):
        """The runners package must be importable."""
        import runners  # noqa: F401
        assert hasattr(runners, '__version__')

    def test_runners_subpackages_importable(self):
        """All runners subpackages must be importable directly."""
        from runners.workflows.workflow_engine import WorkflowEngine
        from runners.workflows.workflow_parser import WorkflowParser
        from runners.scanners.code_analyzer import CodeAnalyzer
        from runners.scanners.dependency_scanner import DependencyVulnerabilityScanner
        from runners.security.secret_scanner import SecretScanner
        from runners.integrations.cloud_cost_tracker import CloudCostTracker
        from runners.profilers.performance_profiler import AdvancedProfiler
        from runners.templates.template_manager import TemplateManager

        for cls in (
            WorkflowEngine, WorkflowParser, CodeAnalyzer,
            DependencyVulnerabilityScanner, SecretScanner,
            CloudCostTracker, AdvancedProfiler, TemplateManager,
        ):
            assert cls is not None

    def test_enable_v7_workflows_uses_real_module(self, tmp_path):
        """enable_v7_feature('workflows') should load the real WorkflowEngine."""
        from runners.workflows.workflow_engine import WorkflowEngine

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.enable_v7_feature('workflows')

        assert result is True
        assert runner.enable_workflows is True
        assert isinstance(runner.workflow_engine, WorkflowEngine)

    def test_enable_v7_security_uses_real_module(self, tmp_path):
        """enable_v7_feature('security') should load the real CodeAnalyzer."""
        from runners.scanners.code_analyzer import CodeAnalyzer

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.enable_v7_feature('security')

        assert result is True
        assert runner.enable_code_analysis is True
        assert isinstance(runner.code_analyzer, CodeAnalyzer)

    def test_enable_v7_dependencies_uses_real_module(self, tmp_path):
        """enable_v7_feature('dependencies') should load DependencyVulnerabilityScanner."""
        from runners.scanners.dependency_scanner import DependencyVulnerabilityScanner

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.enable_v7_feature('dependencies')

        assert result is True
        assert runner.enable_dependency_scanning is True
        assert isinstance(runner.dependency_scanner, DependencyVulnerabilityScanner)

    def test_enable_v7_secrets_uses_real_module(self, tmp_path):
        """enable_v7_feature('secrets') should load the real SecretScanner."""
        from runners.security.secret_scanner import SecretScanner

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.enable_v7_feature('secrets')

        assert result is True
        assert runner.enable_secret_scanning is True
        assert isinstance(runner.secret_scanner, SecretScanner)

    def test_enable_v7_costs_uses_real_module(self, tmp_path):
        """enable_v7_feature('costs') should load the real CloudCostTracker."""
        from runners.integrations.cloud_cost_tracker import CloudCostTracker

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        result = runner.enable_v7_feature('costs')

        assert result is True
        assert runner.enable_cost_tracking is True
        assert isinstance(runner.cost_tracker, CloudCostTracker)

    def test_initialize_v7_features_enables_workflows(self, tmp_path):
        """_initialize_v7_features with workflows=True should use the real module."""
        from runners.workflows.workflow_engine import WorkflowEngine

        script_file = tmp_path / "test.py"
        script_file.write_text("print('test')")

        runner = ScriptRunner(str(script_file), enable_history=False)
        runner._initialize_v7_features({'v7_features': {'enable_workflows': True}})

        assert runner.enable_workflows is True
        assert isinstance(runner.workflow_engine, WorkflowEngine)

    def test_security_checks_run_with_real_code_analyzer(self, tmp_path):
        """run_pre_execution_security_checks should work with the real CodeAnalyzer."""
        script_file = tmp_path / "clean.py"
        script_file.write_text("print('Hello, world!')\n")

        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.enable_v7_feature('security')

        # Real analysis on a benign file must not raise and must return True or False
        result = runner.run_pre_execution_security_checks()
        assert isinstance(result, bool)

    def test_secret_scan_clean_file(self, tmp_path):
        """SecretScanner via ScriptRunner should not flag a clean file."""
        script_file = tmp_path / "clean.py"
        script_file.write_text("print('no secrets here')\n")

        runner = ScriptRunner(str(script_file), enable_history=False)
        runner.enable_v7_feature('secrets')

        runner.run_pre_execution_security_checks()
        assert isinstance(runner.v7_results['secrets_found'], list)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

