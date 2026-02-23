"""
Tests for enhanced ExecutionVisualizer and ScriptWorkflow orchestration.

Covers:
- ExecutionVisualizer: color support, per-step timing, output_format=json,
  output_file, get_execution_report()
- ScriptWorkflow: stop_on_failure, on_step_callback, parallel execution,
  visualize_dag()
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from io import StringIO
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from runner import ExecutionVisualizer, ScriptWorkflow, ScriptNode


# ---------------------------------------------------------------------------
# ExecutionVisualizer tests
# ---------------------------------------------------------------------------

class TestExecutionVisualizerBasics:
    """Basic no-op behaviour when disabled."""

    def test_disabled_no_output(self, capsys):
        v = ExecutionVisualizer(enabled=False)
        v.show_header("script.py")
        v.show_step("Stage", "desc", "running")
        v.show_footer(1.0, True)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_enabled_text_output(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("my_script.py", attempt=1)
        v.show_step("Validation", "Checking script", "done")
        v.show_footer(0.5, True, returncode=0)
        out = capsys.readouterr().out
        assert "SCRIPT EXECUTION FLOW VISUALIZATION" in out
        assert "Validation" in out
        assert "EXECUTION SUCCESS" in out

    def test_step_count_increments(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("script.py")
        assert v.step_count == 0
        v.show_step("A", "desc A", "done")
        assert v.step_count == 1
        v.show_step("B", "desc B", "done")
        assert v.step_count == 2

    def test_step_details_shown(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("script.py")
        v.show_step("Stage", "desc", "done", details={"key": "value"})
        out = capsys.readouterr().out
        assert "key" in out
        assert "value" in out

    def test_show_subprocess_start(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("script.py")
        v.show_subprocess_start(["python", "script.py"], pid=12345)
        out = capsys.readouterr().out
        assert "12345" in out
        assert "script.py" in out

    def test_show_metrics_summary(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("script.py")
        metrics = {
            "execution_time_seconds": 0.5,
            "cpu_max": 45.0,
            "exit_code": 0,
        }
        v.show_metrics_summary(metrics)
        out = capsys.readouterr().out
        assert "Metrics" in out
        assert "Exit Code" in out


class TestExecutionVisualizerColor:
    """ANSI color code behaviour."""

    def test_color_disabled_no_ansi(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("s.py")
        v.show_step("Stage", "desc", "done")
        v.show_footer(1.0, True)
        out = capsys.readouterr().out
        assert "\033[" not in out

    def test_color_enabled_contains_ansi(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=True)
        v.show_header("s.py")
        v.show_step("Stage", "desc", "done")
        v.show_footer(1.0, True)
        out = capsys.readouterr().out
        assert "\033[" in out

    def test_auto_color_no_tty(self):
        """When stdout is not a TTY, use_color should default to False."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = False
            v = ExecutionVisualizer(enabled=True)
            assert v.use_color is False

    def test_auto_color_tty(self):
        """When stdout is a TTY, use_color should default to True."""
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty.return_value = True
            v = ExecutionVisualizer(enabled=True)
            assert v.use_color is True


class TestExecutionVisualizerStepTiming:
    """Per-step duration tracking."""

    def test_step_duration_tracked(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("s.py")
        v.show_step("Stage", "start", "running")
        time.sleep(0.05)
        v.show_step("Stage", "end", "done")
        out = capsys.readouterr().out
        # The footer shows the step with (Xs) duration annotation
        assert "Stage" in out

    def test_step_duration_in_report(self):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("s.py")
        v.show_step("Stage", "start", "running")
        time.sleep(0.05)
        v.show_step("Stage", "end", "done")
        v.show_footer(1.0, True)
        report = v.get_execution_report()
        done_steps = [s for s in report["steps"] if s["status"] == "done"]
        assert len(done_steps) >= 1
        # The "done" step should carry a duration_s
        assert "duration_s" in done_steps[0]
        assert done_steps[0]["duration_s"] >= 0.0


class TestExecutionVisualizerOutputFile:
    """Output written to file."""

    def test_output_file_created(self, tmp_path, capsys):
        out_file = tmp_path / "vis.txt"
        v = ExecutionVisualizer(enabled=True, use_color=False, output_file=str(out_file))
        v.show_header("s.py")
        v.show_step("Stage", "desc", "done")
        v.show_footer(1.0, True)
        assert out_file.exists()
        content = out_file.read_text()
        assert "SCRIPT EXECUTION FLOW VISUALIZATION" in content
        assert "Stage" in content

    def test_output_file_no_ansi_codes(self, tmp_path):
        out_file = tmp_path / "vis.txt"
        v = ExecutionVisualizer(enabled=True, use_color=True, output_file=str(out_file))
        v.show_header("s.py")
        v.show_step("Stage", "desc", "done")
        v.show_footer(1.0, True)
        content = out_file.read_text()
        # File output should not contain ANSI escape codes
        assert "\033[" not in content


class TestExecutionVisualizerJSONFormat:
    """output_format='json' behaviour."""

    def test_json_no_text_during_steps(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False, output_format="json")
        v.show_header("s.py")
        v.show_step("Stage", "desc", "done")
        # No output yet
        mid = capsys.readouterr().out
        assert mid == ""

    def test_json_emitted_on_footer(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False, output_format="json")
        v.show_header("s.py", script_args=["--flag"], attempt=2)
        v.show_step("Validation", "Checking script", "done")
        v.show_footer(1.23, True, returncode=0)
        out = capsys.readouterr().out.strip()
        data = json.loads(out)
        assert data["header"]["script_path"] == "s.py"
        assert data["header"]["attempt"] == 2
        assert data["footer"]["success"] is True
        assert data["footer"]["returncode"] == 0
        assert len(data["steps"]) >= 1

    def test_json_steps_recorded(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False, output_format="json")
        v.show_header("s.py")
        v.show_step("A", "desc A", "running")
        v.show_step("B", "desc B", "done")
        v.show_footer(0.5, False, returncode=1)
        out = capsys.readouterr().out
        data = json.loads(out)
        stages = [s["stage"] for s in data["steps"]]
        assert "A" in stages
        assert "B" in stages


class TestExecutionVisualizerGetReport:
    """get_execution_report() returns correct structure."""

    def test_report_structure(self, capsys):
        v = ExecutionVisualizer(enabled=True, use_color=False)
        v.show_header("s.py", script_args=["arg1"])
        v.show_step("S1", "desc 1", "done")
        v.show_footer(2.0, True, returncode=0)
        report = v.get_execution_report()
        assert "header" in report
        assert "steps" in report
        assert "footer" in report
        assert report["header"]["script_path"] == "s.py"
        assert report["footer"]["success"] is True
        assert isinstance(report["steps"], list)

    def test_report_empty_when_disabled(self):
        v = ExecutionVisualizer(enabled=False)
        report = v.get_execution_report()
        assert report["steps"] == []
        assert report["header"] == {}
        assert report["footer"] == {}


# ---------------------------------------------------------------------------
# ScriptWorkflow tests
# ---------------------------------------------------------------------------

class TestScriptWorkflowStopOnFailure:
    """stop_on_failure prevents execution of remaining scripts."""

    def test_stop_on_failure_aborts(self, tmp_path):
        failing = tmp_path / "fail.py"
        failing.write_text("import sys; sys.exit(1)")
        ok = tmp_path / "ok.py"
        ok.write_text("print('ok')")

        wf = ScriptWorkflow(name="test", stop_on_failure=True)
        wf.add_script("a", str(failing))
        wf.add_script("b", str(ok), dependencies=["a"])
        result = wf.execute()

        assert result["status"] == "aborted"
        # 'b' should not have been run — it gets "blocked" because its dependency failed
        assert wf.scripts["b"].status == "blocked"
        assert result.get("failed", 0) >= 1
        assert result.get("blocked", 0) >= 1

    def test_stop_on_failure_false_continues(self, tmp_path):
        failing = tmp_path / "fail.py"
        failing.write_text("import sys; sys.exit(1)")
        ok = tmp_path / "ok.py"
        ok.write_text("print('ok')")

        wf = ScriptWorkflow(name="test", stop_on_failure=False)
        wf.add_script("a", str(failing))
        wf.add_script("b", str(ok))  # independent of 'a'
        result = wf.execute()

        # 'b' has no dependency on 'a' so it should still execute
        assert wf.scripts["b"].status == "completed"


class TestScriptWorkflowOnStepCallback:
    """on_step_callback is called on state changes."""

    def test_callback_invoked(self, tmp_path):
        script = tmp_path / "ok.py"
        script.write_text("print('hello')")
        events = []

        def cb(name, status, result):
            events.append((name, status))

        wf = ScriptWorkflow(name="test", on_step_callback=cb)
        wf.add_script("s", str(script))
        wf.execute()

        # Should have at least "running" and "completed" events for "s"
        statuses = [e[1] for e in events if e[0] == "s"]
        assert "running" in statuses
        assert "completed" in statuses

    def test_callback_receives_result(self, tmp_path):
        script = tmp_path / "ok.py"
        script.write_text("print('hello')")
        completed_results = []

        def cb(name, status, result):
            if status == "completed":
                completed_results.append(result)

        wf = ScriptWorkflow(name="test", on_step_callback=cb)
        wf.add_script("s", str(script))
        wf.execute()

        assert len(completed_results) == 1
        assert completed_results[0]["success"] is True


class TestScriptWorkflowParallelExecution:
    """Parallel execution respects max_parallel and DAG order."""

    def test_parallel_scripts_complete(self, tmp_path):
        for i in range(3):
            s = tmp_path / f"s{i}.py"
            s.write_text("import time; time.sleep(0.1); print('done')")

        wf = ScriptWorkflow(name="par_test", max_parallel=3)
        for i in range(3):
            wf.add_script(f"s{i}", str(tmp_path / f"s{i}.py"))

        result = wf.execute()
        assert result["status"] == "completed"
        assert result["successful"] == 3
        assert result["blocked"] == 0  # No scripts were blocked

    def test_parallel_respects_dependencies(self, tmp_path):
        """b must run after a completes."""
        a_script = tmp_path / "a.py"
        a_script.write_text("print('a')")
        b_script = tmp_path / "b.py"
        b_script.write_text("print('b')")

        order = []

        def cb(name, status, result):
            if status == "completed":
                order.append(name)

        wf = ScriptWorkflow(name="dep_test", max_parallel=2, on_step_callback=cb)
        wf.add_script("a", str(a_script))
        wf.add_script("b", str(b_script), dependencies=["a"])
        result = wf.execute()

        assert result["status"] == "completed"
        assert order.index("a") < order.index("b")


class TestScriptWorkflowVisualizeDag:
    """visualize_dag() output correctness."""

    def test_visualize_dag_contains_names(self):
        wf = ScriptWorkflow(name="my_pipeline")
        wf.add_script("fetch", "/tmp/fetch.py")
        wf.add_script("transform", "/tmp/transform.py", dependencies=["fetch"])
        wf.add_script("load", "/tmp/load.py", dependencies=["transform"])
        diagram = wf.visualize_dag()
        assert "my_pipeline" in diagram
        assert "fetch" in diagram
        assert "transform" in diagram
        assert "load" in diagram

    def test_visualize_dag_shows_arrows(self):
        wf = ScriptWorkflow(name="pipe")
        wf.add_script("a", "/tmp/a.py")
        wf.add_script("b", "/tmp/b.py", dependencies=["a"])
        diagram = wf.visualize_dag()
        assert "──▶" in diagram

    def test_visualize_dag_no_scripts(self):
        wf = ScriptWorkflow(name="empty")
        diagram = wf.visualize_dag()
        assert "empty" in diagram

    def test_visualize_dag_returns_string(self):
        wf = ScriptWorkflow(name="pipe")
        wf.add_script("a", "/tmp/a.py")
        result = wf.visualize_dag()
        assert isinstance(result, str)
        assert len(result) > 0


class TestScriptWorkflowDryRun:
    """Dry run returns plan without executing."""

    def test_dry_run_no_execution(self, tmp_path):
        script = tmp_path / "s.py"
        script.write_text("print('should not run')")
        wf = ScriptWorkflow(name="dry")
        wf.add_script("s", str(script))
        result = wf.execute(dry_run=True)
        assert result["status"] == "dry_run"
        assert "plan" in result
        # Script status should remain pending
        assert wf.scripts["s"].status == "pending"
