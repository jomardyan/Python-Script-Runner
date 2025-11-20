import datetime
from typing import List

import pytest

from runner import TaskScheduler


class _DummyRunner:
    calls: List[str] = []

    def __init__(self, script_path: str, **_: object) -> None:
        self.script_path = script_path

    def run_script(self, retry_on_failure: bool = False):  # noqa: D401
        """Pretend to execute the script and record the call order."""
        _DummyRunner.calls.append(self.script_path)
        return {"returncode": 0, "stderr": "", "metrics": {"execution_time_seconds": 0.1}}


def test_run_due_tasks_executes_and_logs_success():
    scheduler = TaskScheduler()
    task = scheduler.add_scheduled_task("demo", "examples/sample_script.py", schedule="hourly")
    task.next_run = datetime.datetime.now() - datetime.timedelta(minutes=1)

    _DummyRunner.calls = []
    results = scheduler.run_due_tasks(runner_factory=_DummyRunner)

    assert results and results[0]["status"] == "success"
    assert scheduler.execution_log[-1]["status"] == "success"
    assert scheduler.tasks["demo"].run_count == 1
    assert _DummyRunner.calls == ["examples/sample_script.py"]


def test_dependencies_run_after_prerequisites():
    scheduler = TaskScheduler()
    parent = scheduler.add_scheduled_task("parent", "examples/sample_script.py")
    child = scheduler.add_scheduled_task(
        "child",
        "examples/sample_script.py",
        dependencies=["parent"],
    )

    parent.next_run = datetime.datetime.now() - datetime.timedelta(minutes=1)
    child.next_run = datetime.datetime.now() - datetime.timedelta(minutes=1)

    execution_order: List[str] = []

    class _DependencyAwareRunner:
        def __init__(self, script_path: str, **_: object) -> None:
            self.script_path = script_path

        def run_script(self, retry_on_failure: bool = False):  # noqa: D401
            execution_order.append(self.script_path)
            return {"returncode": 0, "stderr": "", "metrics": {}}

    scheduler.run_due_tasks(runner_factory=_DependencyAwareRunner)

    assert execution_order == ["examples/sample_script.py", "examples/sample_script.py"]
    assert scheduler.tasks["child"].last_status == "success"
