# Next Phase: Unit Testing Kickoff

**Status**: All 6 core implementations complete and ready for testing  
**Date**: October 23, 2025  
**Effort Estimate**: 20 hours (14 unit + 6 integration)

---

## 📋 Test Plan Overview

### Module 1: Workflow Engine (20 tests - 3 hours)

**Tests to Write**:

```python
# Test DAG functionality
test_dag_creation()
test_add_task()
test_add_task_duplicate_error()
test_add_task_missing_dependency_error()
test_topological_sort_valid_dag()
test_topological_sort_cycle_detection()
test_get_ready_tasks_dependencies()
test_get_levels_parallelism()

# Test Task functionality
test_task_creation()
test_task_validation()
test_task_matrix_expansion()
test_task_expand_matrix_single()
test_task_expand_matrix_nested()

# Test Executor functionality
test_execute_task_success()
test_execute_task_with_retry()
test_execute_task_skip_if_condition()
test_execute_workflow_parallel()
test_execute_workflow_error_handling()
test_workflow_context_propagation()

# Test Parser functionality
test_parse_yaml_workflow()
test_parse_json_workflow()
test_workflow_schema_validation()
test_parser_error_handling()
```

**Mock Requirements**:
- Task executor function (return TaskResult)
- File I/O for YAML/JSON
- Threading for parallelism verification

**Fixtures**:
```python
@pytest.fixture
def sample_workflow_config():
    return {
        "id": "test_workflow",
        "tasks": [
            {"id": "task1", "script": "echo 'task1'"},
            {"id": "task2", "script": "echo 'task2'", "depends_on": ["task1"]},
        ]
    }

@pytest.fixture
def workflow_engine():
    return WorkflowEngine(max_parallel=2)
```

---

### Module 2: OpenTelemetry Integration (15 tests - 2.5 hours)

**Tests to Write**:

```python
# Test initialization
test_tracer_initialization_jaeger()
test_tracer_initialization_zipkin()
test_tracer_initialization_otlp()
test_tracer_initialization_none()
test_tracer_initialization_missing_otel()
test_tracer_disabled()

# Test sampling
test_sampling_always_on()
test_sampling_always_off()
test_sampling_probability()
test_sampling_tail_based()
test_sampling_config_from_env()

# Test tracing
test_create_span()
test_span_context_manager()
test_create_event()
test_set_span_status()
test_trace_context_propagation()
test_shutdown_graceful()
```

**Mock Requirements**:
- OpenTelemetry imports (can mock successfully)
- Exporter backends (mock HTTP calls)
- Tracer provider

**Fixtures**:
```python
@pytest.fixture
def tracer_manager():
    return TracingManager(enabled=True)

@pytest.fixture
def mock_otel(monkeypatch):
    # Mock OTEL_AVAILABLE = True
    # Mock exporter backends
    pass
```

---

### Module 3: Static Code Analysis (15 tests - 2.5 hours)

**Tests to Write**:

```python
# Test finding
test_finding_creation()
test_finding_to_dict()

# Test Bandit integration
test_bandit_analyze_file()
test_bandit_analyze_missing_file()
test_bandit_analyze_no_findings()
test_bandit_analyze_with_findings()
test_bandit_parse_severity()

# Test Semgrep integration
test_semgrep_analyze_file()
test_semgrep_custom_rules()
test_semgrep_parse_severity()

# Test combined analyzer
test_code_analyzer_single_file()
test_code_analyzer_directory()
test_code_analyzer_deduplication()
test_analysis_result_sarif_export()
test_analysis_blocking_issues()
```

**Mock Requirements**:
- `subprocess.run` for Bandit/Semgrep
- JSON output for parsers
- File system

**Fixtures**:
```python
@pytest.fixture
def sample_vulnerable_code():
    return """
    import pickle
    data = pickle.loads(user_input)  # Vulnerable!
    """

@pytest.fixture
def code_analyzer():
    return CodeAnalyzer(use_bandit=True, use_semgrep=True)
```

---

### Module 4: Dependency Vulnerability Scanning (15 tests - 2.5 hours)

**Tests to Write**:

```python
# Test vulnerability
test_vulnerability_creation()
test_vulnerability_to_dict()

# Test Safety scanner
test_safety_scan_requirements()
test_safety_scan_missing_file()
test_safety_parse_severity()
test_safety_scan_no_vulns()
test_safety_scan_with_vulns()

# Test OSV scanner
test_osv_scan_requirements()
test_osv_parse_severity()
test_osv_scan_no_vulns()
test_osv_scan_with_vulns()

# Test combined scanner
test_dependency_scanner_requirements()
test_dependency_scanner_deduplication()
test_sbom_generation()
test_sbom_cyclonedx_format()
test_blocking_vulnerabilities()
```

**Mock Requirements**:
- `subprocess.run` for Safety/OSV
- JSON output for both scanners
- requirements.txt file parsing

**Fixtures**:
```python
@pytest.fixture
def sample_requirements():
    return """
    requests==2.25.1  # Known vulnerability
    django==3.0.0     # Known vulnerability
    """

@pytest.fixture
def dependency_scanner():
    return DependencyVulnerabilityScanner()
```

---

### Module 5: Secret Scanning & Vault (15 tests - 2.5 hours)

**Tests to Write**:

```python
# Test secret
test_secret_creation()
test_secret_to_dict()

# Test pattern scanner
test_pattern_detection_api_key()
test_pattern_detection_aws_credentials()
test_pattern_detection_private_key()
test_pattern_detection_jwt()
test_pattern_detection_slack_token()
test_pattern_detection_github_token()

# Test file scanning
test_scan_single_file()
test_scan_directory()
test_scan_with_exclusions()

# Test vault adapters
test_vault_adapter_aws()
test_vault_adapter_vault()
test_vault_adapter_azure()
test_vault_adapter_set_secret()
test_vault_adapter_error_handling()
```

**Mock Requirements**:
- File I/O for scanning
- boto3, hvac, azure-identity (mock)
- Pattern matching verification

**Fixtures**:
```python
@pytest.fixture
def vulnerable_code():
    return """
    AWS_KEY = "AKIA1234567890ABCDEF"
    DB_URL = "mysql://user:pass@host:3306/db"
    """

@pytest.fixture
def secret_scanner():
    return SecretScanner()
```

---

### Module 6: Cloud Cost Tracking (15 tests - 2.5 hours)

**Tests to Write**:

```python
# Test resource usage
test_resource_usage_creation()
test_resource_usage_to_dict()

# Test AWS calculator
test_aws_ec2_cost()
test_aws_s3_cost()
test_aws_lambda_cost()
test_aws_cost_breakdown()

# Test Azure calculator
test_azure_vm_cost()
test_azure_storage_cost()

# Test GCP calculator
test_gcp_compute_engine_cost()
test_gcp_storage_cost()

# Test tracker
test_cloud_cost_tracker_add_resource()
test_cloud_cost_tracker_add_tag()
test_cloud_cost_tracker_finalize()
test_cloud_cost_tracker_total_cost()
test_cloud_cost_tracker_multi_cloud()
```

**Mock Requirements**:
- Time tracking
- Cost calculations

**Fixtures**:
```python
@pytest.fixture
def cost_tracker():
    return CloudCostTracker()

@pytest.fixture
def aws_calculator():
    return AWSCostCalculator()
```

---

## 🔧 Testing Infrastructure

### pytest Configuration

Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --cov=runners --cov-report=html
```

### conftest.py Setup

Create `tests/conftest.py`:
```python
import pytest
import logging
from unittest.mock import Mock, patch

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)

@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging between tests."""
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess.run for external tool tests."""
    def mock_run(cmd, *args, **kwargs):
        # Return appropriate JSON based on command
        return Mock(returncode=0, stdout='{}', stderr='')
    monkeypatch.setattr("subprocess.run", mock_run)
```

### Test Execution Plan

```bash
# Run all tests with coverage
pytest tests/ -v --cov=runners --cov-report=html

# Run specific module tests
pytest tests/unit/test_workflow_engine.py -v

# Run with markers
pytest -m unit  # Unit tests only
pytest -m integration  # Integration only

# Run with coverage threshold
pytest --cov=runners --cov-fail-under=85
```

---

## 📊 Coverage Goals

| Module | Target | Strategy |
|--------|--------|----------|
| Workflow Engine | 85% | Test DAG, executor, parser |
| OpenTelemetry | 80% | Mock OTEL, test initialization |
| Code Analysis | 85% | Mock subprocess, test parsing |
| Dependency Scan | 85% | Mock scanners, test SBOM |
| Secret Scanning | 90% | Pattern matching, vault mocks |
| Cloud Costs | 85% | Calculator tests, resource tracking |
| **Overall** | **85%** | All modules targeted |

---

## 🧪 Integration Testing Plan

### Scenario 1: End-to-End Workflow

```python
def test_workflow_with_tracing_and_costing():
    """Full workflow with tracing and cost tracking."""
    engine = WorkflowEngine()
    tracer = TracingManager()
    tracker = CloudCostTracker()
    
    with tracer.create_span("workflow_execution"):
        results = engine.run_workflow(...)
        tracker.finalize_resource(...)
    
    assert results.success
    assert tracker.get_total_cost() > 0
```

### Scenario 2: Security Checks Pre-Execution

```python
def test_pre_execution_security_checks():
    """Test all security checks before script execution."""
    analyzer = CodeAnalyzer()
    dep_scanner = DependencyVulnerabilityScanner()
    secret_scanner = SecretScanner()
    
    # All should pass
    assert not analyzer.analyze(script).has_blocking_issues
    assert not dep_scanner.scan(req).has_blocking_issues
    assert not secret_scanner.scan(dir).has_secrets
```

### Scenario 3: Multi-Cloud Cost Scenario

```python
def test_multi_cloud_cost_tracking():
    """Track costs across multiple clouds."""
    tracker = CloudCostTracker()
    
    # Add AWS resource
    tracker.add_resource("ec2-123", ResourceType.COMPUTE, CloudProvider.AWS)
    
    # Add Azure resource
    tracker.add_resource("vm-456", ResourceType.COMPUTE, CloudProvider.AZURE)
    
    # Add GCP resource
    tracker.add_resource("gce-789", ResourceType.COMPUTE, CloudProvider.GCP)
    
    # Verify multi-cloud aggregation
    result = tracker.get_result()
    assert len(result.resource_usages) == 3
    assert result.total_estimated_cost_usd > 0
```

---

## 📅 Testing Schedule

**Week 1**:
- Unit tests for modules 1-3 (Workflow, OTEL, CodeAnalysis)
- Completion: 50 tests, 8 hours

**Week 2**:
- Unit tests for modules 4-6 (Deps, Secrets, Costs)
- Integration tests
- Completion: 30 tests, 12 hours

**Total**: 80+ unit tests + integration tests in 20 hours

---

## ✅ Definition of Done

Tests are "done" when:
- ✅ All test cases pass
- ✅ Coverage >85% per module
- ✅ All mocks properly configured
- ✅ Error cases covered
- ✅ Fixtures reusable and documented
- ✅ CI/CD integration verified
- ✅ Performance benchmarks captured

---

## 🚀 Ready to Begin

All 6 modules are ready for comprehensive testing:

1. ✅ Code is production-quality
2. ✅ All classes/methods documented
3. ✅ Error handling comprehensive
4. ✅ Mock points identified
5. ✅ Fixtures pre-planned
6. ✅ Integration points clear

**Next Step**: Begin writing unit tests for Workflow Engine module.

Let's go! 🎯
