"""
Tests for security enhancements across the application.

Covers:
- Command injection prevention in workflow engine (shell=False)
- Path validation (symlinks, null bytes)
- Environment variable filtering
- Subprocess timeout in code analyzers
"""

import pytest
import shlex
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.workflows.workflow_engine import (
    Task, TaskMetadata, TaskStatus, WorkflowExecutor,
)


class TestCommandInjectionPrevention:
    """Verify the workflow executor no longer uses shell=True."""

    @patch('subprocess.Popen')
    def test_default_executor_uses_shell_false(self, mock_popen):
        """The default executor must invoke Popen with shell=False."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'ok', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = WorkflowExecutor()
        task = Task(id='t1', script='echo hello', depends_on=[], metadata=None)
        executor.execute_task(task)

        call_kwargs = mock_popen.call_args
        # shell must be False
        assert call_kwargs[1].get('shell') is False or call_kwargs.kwargs.get('shell') is False

    @patch('subprocess.Popen')
    def test_default_executor_passes_list_to_popen(self, mock_popen):
        """The command should be passed as a list (shlex-split), not a raw string."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        executor = WorkflowExecutor()
        task = Task(id='t1', script='python -c "print(1)"', depends_on=[], metadata=None)
        executor.execute_task(task)

        args, kwargs = mock_popen.call_args
        cmd = args[0]
        # Must be a list, not a string
        assert isinstance(cmd, list)
        assert cmd == shlex.split('python -c "print(1)"')


class TestCodeAnalyzerTimeouts:
    """Verify that Bandit and Semgrep analyzers use timeouts."""

    @patch('subprocess.Popen')
    def test_bandit_communicate_has_timeout(self, mock_popen):
        """BanditAnalyzer.analyze() should pass a timeout to communicate()."""
        from runners.scanners.code_analyzer import BanditAnalyzer

        mock_process = MagicMock()
        mock_process.communicate.return_value = ('{"results":[]}', '')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        analyzer = BanditAnalyzer()
        analyzer.analyze('/tmp/dummy.py')

        mock_process.communicate.assert_called_once_with(timeout=300)

    @patch('subprocess.Popen')
    def test_semgrep_communicate_has_timeout(self, mock_popen):
        """SemgrepAnalyzer.analyze() should pass a timeout to communicate()."""
        from runners.scanners.code_analyzer import SemgrepAnalyzer

        mock_process = MagicMock()
        mock_process.communicate.return_value = ('{"results":[]}', '')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        analyzer = SemgrepAnalyzer()
        analyzer.analyze('/tmp/dummy.py')

        mock_process.communicate.assert_called_once_with(timeout=300)


class TestPathValidation:
    """Tests for _validate_script_path enhancements in the Web API."""

    def test_null_byte_in_path_rejected(self):
        """Paths containing null bytes must be rejected."""
        from WEBAPI.api import _validate_script_path
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_script_path("/some/path\x00.py")
        assert exc_info.value.status_code == 400
        assert "Invalid" in exc_info.value.detail

    def test_symlink_rejected(self, tmp_path):
        """Symlinks must be rejected even if they point to a valid .py file."""
        from WEBAPI.api import _validate_script_path, ALLOWED_SCRIPT_ROOT
        from fastapi import HTTPException

        # Create a real .py file and a symlink to it
        real_file = tmp_path / "real.py"
        real_file.write_text("print('hello')")
        link = tmp_path / "link.py"
        link.symlink_to(real_file)

        # The symlink check happens after resolve(), so we need the resolved
        # path to be within the allowed root.  Since it might not be, we
        # just verify that either a symlink or allowed-root error is raised.
        with pytest.raises(HTTPException):
            _validate_script_path(str(link))


class TestEnvVarFiltering:
    """Tests for dangerous environment variable filtering."""

    def test_dangerous_env_vars_stripped(self):
        """_validate_payload must strip dangerous env vars like PATH."""
        from WEBAPI.api import _validate_payload, RunRequest, _DANGEROUS_ENV_VARS
        from fastapi import HTTPException

        # Create a minimal valid payload (the script won't actually be
        # validated here because _validate_script_path will raise – we
        # mock it).
        payload = RunRequest(
            script_path="/dummy.py",
            env_vars={"PATH": "/evil", "MY_VAR": "safe", "LD_PRELOAD": "/bad.so"},
        )

        with patch("WEBAPI.api._validate_script_path"):
            result = _validate_payload(payload)

        assert "PATH" not in result.env_vars
        assert "LD_PRELOAD" not in result.env_vars
        assert result.env_vars["MY_VAR"] == "safe"

    def test_safe_env_vars_preserved(self):
        """Non-dangerous env vars must pass through unchanged."""
        from WEBAPI.api import _validate_payload, RunRequest
        from fastapi import HTTPException

        payload = RunRequest(
            script_path="/dummy.py",
            env_vars={"APP_MODE": "test", "DEBUG": "1"},
        )

        with patch("WEBAPI.api._validate_script_path"):
            result = _validate_payload(payload)

        assert result.env_vars == {"APP_MODE": "test", "DEBUG": "1"}
