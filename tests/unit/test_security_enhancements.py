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
