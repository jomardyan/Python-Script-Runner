"""
Pytest configuration and fixtures for all tests.
Provides common test utilities, mocks, and fixtures.
"""

import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
from dataclasses import dataclass


# ============================================================================
# FIXTURES: Test Data & Samples
# ============================================================================

@pytest.fixture
def sample_task_metadata():
    """Sample task metadata for workflow tests."""
    return {
        'name': 'test_task',
        'description': 'Test task for unit tests',
        'tags': ['test', 'unit'],
        'estimated_duration': 10,
        'timeout': 30,
        'priority': 1
    }


@pytest.fixture
def sample_workflow_dict():
    """Sample workflow definition as dictionary."""
    return {
        'name': 'test_workflow',
        'version': '1.0.0',
        'tasks': [
            {
                'id': 'task1',
                'script': 'echo "hello"',
                'metadata': {
                    'name': 'Task 1',
                    'description': 'First task',
                },
                'depends_on': []
            },
            {
                'id': 'task2',
                'script': 'echo "world"',
                'metadata': {
                    'name': 'Task 2',
                    'description': 'Second task',
                },
                'depends_on': ['task1']
            }
        ]
    }


@pytest.fixture
def sample_workflow_yaml(tmp_path):
    """Sample workflow in YAML format."""
    workflow_content = """
name: test_workflow
version: 1.0.0
tasks:
  - id: task1
    script: echo "hello"
    depends_on: []
  - id: task2
    script: echo "world"
    depends_on: [task1]
"""
    workflow_file = tmp_path / "workflow.yaml"
    workflow_file.write_text(workflow_content)
    return workflow_file


@pytest.fixture
def sample_code_findings():
    """Sample security findings from code analysis."""
    return [
        {
            'id': 'B101',
            'title': 'assert_used',
            'description': 'Use of assert detected. Use raise AssertionError() instead.',
            'severity': 'HIGH',
            'file_path': 'app.py',
            'line_number': 42,
            'column_number': 5,
            'analysis_type': 'BANDIT',
            'rule_id': 'B101',
            'cve': None,
            'recommendation': 'Replace assert with proper error handling'
        },
        {
            'id': 'SG001',
            'title': 'hardcoded_password',
            'description': 'Hardcoded password detected in code',
            'severity': 'CRITICAL',
            'file_path': 'config.py',
            'line_number': 10,
            'column_number': 0,
            'analysis_type': 'SEMGREP',
            'rule_id': 'python.lang.security.hardcoded-password',
            'cve': None,
            'recommendation': 'Move password to environment variables or vault'
        }
    ]


@pytest.fixture
def sample_vulnerabilities():
    """Sample vulnerability data from dependency scanning."""
    return [
        {
            'id': 'CVE-2021-12345',
            'package_name': 'requests',
            'package_version': '2.25.0',
            'vulnerability_id': 'PYUP-1234',
            'title': 'HTTP request smuggling vulnerability',
            'description': 'Requests library version 2.25.0 has HTTP smuggling vulnerability',
            'severity': 'HIGH',
            'fixed_version': '2.26.0',
            'published_date': '2021-05-15',
            'cvss_score': 7.5,
            'cwe': 'CWE-444',
            'scanner': 'safety'
        },
        {
            'id': 'GHSA-12ab-cd34-ef56',
            'package_name': 'django',
            'package_version': '3.0.0',
            'vulnerability_id': 'GHSA-12ab-cd34-ef56',
            'title': 'SQL injection in ORM',
            'description': 'Django ORM vulnerable to SQL injection',
            'severity': 'CRITICAL',
            'fixed_version': '3.2.0',
            'published_date': '2021-06-01',
            'cvss_score': 9.8,
            'cwe': 'CWE-89',
            'scanner': 'osv'
        }
    ]


@pytest.fixture
def sample_secrets():
    """Sample secret data from secret scanning."""
    return [
        {
            'id': 'secret_1',
            'type': 'AWS_KEY',
            'file_path': 'config.py',
            'line_number': 10,
            'start_column': 0,
            'end_column': 20,
            'confidence': 0.95,
            'pattern_matched': 'AKIA[0-9A-Z]{16}',
            'masked_value': 'AKIA****...',
            'detected_by': 'detect-secrets'
        },
        {
            'id': 'secret_2',
            'type': 'PRIVATE_KEY',
            'file_path': 'keys.py',
            'line_number': 5,
            'start_column': 0,
            'end_column': 30,
            'confidence': 0.88,
            'pattern_matched': 'BEGIN RSA PRIVATE KEY',
            'masked_value': 'BEGIN RSA PRIVATE KEY****...',
            'detected_by': 'detect-secrets'
        }
    ]


@pytest.fixture
def sample_aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'test_access_key_id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'test_secret_access_key')
    monkeypatch.setenv('AWS_DEFAULT_REGION', 'us-east-1')
    return {
        'access_key': 'test_access_key_id',
        'secret_key': 'test_secret_access_key',
        'region': 'us-east-1'
    }


@pytest.fixture
def temp_python_file(tmp_path):
    """Create a temporary Python file for testing."""
    code = """
def hello_world():
    print("Hello, World!")
    assert True  # This is a security issue
    
def get_password():
    password = "hardcoded_password"  # This is a security issue
    return password
"""
    py_file = tmp_path / "sample_script.py"
    py_file.write_text(code)
    return py_file


@pytest.fixture
def temp_requirements_file(tmp_path):
    """Create a temporary requirements.txt for testing."""
    requirements = """requests==2.25.0
django==3.0.0
flask==1.1.0
numpy==1.19.0
"""
    req_file = tmp_path / "requirements.txt"
    req_file.write_text(requirements)
    return req_file


# ============================================================================
# FIXTURES: Mock Objects & Patches
# ============================================================================

@pytest.fixture
def mock_subprocess_success(monkeypatch):
    """Mock subprocess.Popen for successful command execution."""
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b'stdout output', b'')
    mock_process.returncode = 0
    mock_process.wait.return_value = 0
    
    mock_popen = MagicMock(return_value=mock_process)
    monkeypatch.setattr('subprocess.Popen', mock_popen)
    return mock_process


@pytest.fixture
def mock_subprocess_failure(monkeypatch):
    """Mock subprocess.Popen for failed command execution."""
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b'', b'error output')
    mock_process.returncode = 1
    mock_process.wait.return_value = 1
    
    mock_popen = MagicMock(return_value=mock_process)
    monkeypatch.setattr('subprocess.Popen', mock_popen)
    return mock_process


@pytest.fixture
def mock_bandit_output():
    """Mock Bandit JSON output."""
    return {
        'results': [
            {
                'test_id': 'B101',
                'test_name': 'assert_used',
                'issue_severity': 'MEDIUM',
                'issue_confidence': 'HIGH',
                'issue_text': 'Use of assert detected',
                'line_number': 42,
                'filename': 'app.py'
            }
        ],
        'metrics': {'_totals': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 1, 'LOW': 0}}
    }


@pytest.fixture
def mock_semgrep_output():
    """Mock Semgrep JSON output."""
    return {
        'results': [
            {
                'rule_id': 'python.lang.security.hardcoded-password',
                'message': 'Hardcoded password',
                'severity': 'ERROR',
                'path': 'config.py',
                'start': {'line': 10, 'col': 0},
                'end': {'line': 10, 'col': 30}
            }
        ],
        'errors': []
    }


@pytest.fixture
def mock_safety_output():
    """Mock Safety JSON output."""
    return [
        {
            'vulnerability': 'CVE-2021-12345',
            'package_name': 'requests',
            'package_version': '2.25.0',
            'advisory': 'HTTP request smuggling vulnerability',
            'cve': 'CVE-2021-12345',
            'specs': ['requests>=2.26.0'],
            'v': '<2.26.0'
        }
    ]


@pytest.fixture
def mock_osv_output():
    """Mock OSV-Scanner JSON output."""
    return {
        'results': [
            {
                'package': {
                    'name': 'django',
                    'version': '3.0.0',
                    'ecosystem': 'PyPI'
                },
                'vulnerabilities': [
                    {
                        'id': 'GHSA-12ab-cd34-ef56',
                        'summary': 'SQL injection in ORM',
                        'severity': 'CRITICAL',
                        'fixed_version': '3.2.0'
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_detect_secrets_output():
    """Mock detect-secrets JSON output."""
    return {
        'version': '1.3.0',
        'plugins_used': [
            {'name': 'ArtifactoryDetector'},
            {'name': 'AWSKeyDetector'},
            {'name': 'PrivateKeyDetector'}
        ],
        'results': {
            'config.py': [
                {
                    'type': 'AWS Access Key',
                    'filename': 'config.py',
                    'line_number': 10,
                    'hashed_secret': 'abc123'
                }
            ]
        },
        'generated_at': '2025-10-23T12:00:00.000000Z'
    }


# ============================================================================
# FIXTURES: Database & File System
# ============================================================================

@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database."""
    db_file = tmp_path / "test.db"
    return str(db_file)


@pytest.fixture
def sample_project_dir(tmp_path):
    """Create a sample project directory structure."""
    project = tmp_path / "sample_project"
    project.mkdir()
    
    # Create Python files
    (project / "app.py").write_text("print('hello')")
    (project / "config.py").write_text("password = 'secret'")
    (project / "requirements.txt").write_text("requests==2.25.0\ndjango==3.0.0\n")
    
    # Create subdirectories
    src = project / "src"
    src.mkdir()
    (src / "main.py").write_text("print('main')")
    
    return project


# ============================================================================
# FIXTURES: Context Managers
# ============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Capture log output for testing."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture
def suppress_logger():
    """Suppress logger output during tests."""
    import logging
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "requires_external: mark test as requiring external tools"
    )


# ============================================================================
# PYTEST HOOKS
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Auto-mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        else:
            item.add_marker(pytest.mark.unit)


# ============================================================================
# TEST UTILITIES
# ============================================================================

def assert_is_valid_json(data):
    """Assert that data is valid JSON."""
    json.dumps(data)


def assert_contains_keys(data, keys):
    """Assert that dictionary contains all required keys."""
    for key in keys:
        assert key in data, f"Missing key: {key}"


def assert_contains_any_keys(data, keys):
    """Assert that dictionary contains at least one of the keys."""
    found = any(key in data for key in keys)
    assert found, f"None of these keys found: {keys}"
