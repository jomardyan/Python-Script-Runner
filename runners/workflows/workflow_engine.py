"""
DAG-Based Workflow Engine for Python Script Runner

Supports task-based workflows with dependency resolution, parallel execution,
conditional branching, and resource constraints.

Features:
- DAG definition and validation
- Topological sort for execution order
- Parallel task execution with constraints
- Conditional branching (skip_if, run_always)
- Matrix/parametric operations
- Error handling and retry strategies
- Comprehensive logging and metrics
"""

import json
import logging
import time
import threading
import queue
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Callable, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import re


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task execution priority."""
    LOW = 3
    NORMAL = 2
    HIGH = 1


@dataclass
class RetryPolicy:
    """Retry configuration for tasks."""
    max_attempts: int = 1
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retry_on_exit_codes: List[int] = field(default_factory=lambda: [1])

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay)


@dataclass
class TaskMetadata:
    """Metadata for a task."""
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    estimated_duration: Optional[float] = None
    timeout: float = 3600.0
    priority: TaskPriority = TaskPriority.NORMAL
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    status: TaskStatus
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    error: Optional[str] = None
    attempts: int = 0
    outputs: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Check if task succeeded."""
        return self.status == TaskStatus.COMPLETED and self.exit_code == 0

    @property
    def failed(self) -> bool:
        """Check if task failed."""
        return self.status == TaskStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


@dataclass
class Task:
    """Workflow task definition."""
    id: str
    script: str
    metadata: TaskMetadata = field(default_factory=TaskMetadata)
    depends_on: List[str] = field(default_factory=list)
    skip_if: Optional[str] = None
    run_always: bool = False
    env: Dict[str, str] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: List[str] = field(default_factory=list)
    matrix: Optional[Dict[str, List[Any]]] = None
    status: TaskStatus = field(default=TaskStatus.PENDING)

    def __post_init__(self):
        """Validate task configuration."""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.script:
            raise ValueError(f"Task {self.id} script cannot be empty")

    def expand_matrix(self) -> List["Task"]:
        """Expand matrix into multiple tasks."""
        if not self.matrix:
            return [self]

        expanded = []
        matrix_vars = list(self.matrix.items())

        def generate_combinations(vars_list: List[Tuple], combo: Dict):
            if not vars_list:
                task_copy = Task(
                    id=f"{self.id}[{','.join(str(v) for v in combo.values())}]",
                    script=self.script.format(**combo),
                    metadata=self.metadata,
                    depends_on=self.depends_on,
                    skip_if=self.skip_if,
                    run_always=self.run_always,
                    env={**self.env, **combo},
                    inputs=self.inputs,
                    outputs=self.outputs,
                )
                expanded.append(task_copy)
                return

            var_name, var_values = vars_list[0]
            for value in var_values:
                combo[var_name] = value
                generate_combinations(vars_list[1:], combo)
                del combo[var_name]

        generate_combinations(matrix_vars, {})
        return expanded


class WorkflowDAG:
    """Directed Acyclic Graph for workflow tasks."""

    def __init__(self, name: str = None, **kwargs):
        """Initialize DAG.
        
        Args:
            name: Optional name for the DAG (for testing/tracking)
        """
        self.name = name or "default_dag"
        self.tasks: Dict[str, Task] = {}
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.logger = logging.getLogger(__name__)

    def add_task(self, task: Task):
        """Add task to DAG."""
        if task.id in self.tasks:
            raise ValueError(f"Task {task.id} already exists")

        self.tasks[task.id] = task

        # Build adjacency lists
        for dep in task.depends_on:
            if dep not in self.tasks:
                raise ValueError(f"Dependency {dep} not found for task {task.id}")
            self.graph[dep].add(task.id)
            self.reverse_graph[task.id].add(dep)

        if task.id not in self.graph:
            self.graph[task.id] = set()
        if task.id not in self.reverse_graph:
            self.reverse_graph[task.id] = set()

    def topological_sort(self) -> List[str]:
        """Get topological sort of tasks."""
        in_degree = {task_id: len(self.reverse_graph[task_id]) for task_id in self.tasks}
        queue_ts = deque([tid for tid in self.tasks if in_degree[tid] == 0])
        sorted_list = []

        while queue_ts:
            node = queue_ts.popleft()
            sorted_list.append(node)

            for neighbor in self.graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue_ts.append(neighbor)

        if len(sorted_list) != len(self.tasks):
            raise ValueError("Cycle detected in task dependencies")

        return sorted_list

    def get_ready_tasks(self, completed: Set[str], failed: Set[str]) -> List[str]:
        """Get tasks ready for execution."""
        ready = []
        for task_id, dependencies in self.reverse_graph.items():
            if task_id in completed or task_id in failed:
                continue
            # All dependencies must be completed
            if dependencies.issubset(completed):
                ready.append(task_id)
        return ready

    def get_levels(self) -> Dict[str, int]:
        """Get execution level for each task (for parallelism)."""
        levels = {}
        sorted_tasks = self.topological_sort()

        for task_id in sorted_tasks:
            if not self.reverse_graph[task_id]:
                levels[task_id] = 0
            else:
                levels[task_id] = max(levels[dep] for dep in self.reverse_graph[task_id]) + 1

        return levels


class WorkflowExecutor:
    """Executor for workflow tasks."""

    def __init__(self, max_parallel: int = 4, task_executor: Optional[Callable] = None):
        """
        Initialize executor.

        Args:
            max_parallel: Maximum parallel tasks
            task_executor: Callable to execute a task (default: logging only)
        """
        self.max_parallel = max_parallel
        self.task_executor = task_executor or self._default_executor
        self.logger = logging.getLogger(__name__)
        self.results: Dict[str, TaskResult] = {}
        self.running_tasks: Set[str] = set()
        self.lock = threading.Lock()

    def _default_executor(self, task: Task, context: Dict[str, Any]) -> TaskResult:
        """Default task executor (logging only)."""
        self.logger.info(f"Executing task {task.id}: {task.script}")
        time.sleep(0.1)
        return TaskResult(
            task_id=task.id,
            status=TaskStatus.COMPLETED,
            exit_code=0,
            duration=0.1,
            start_time=datetime.now(),
            end_time=datetime.now(),
        )

    def _should_skip(self, task: Task, context: Dict[str, Any]) -> bool:
        """Check if task should be skipped."""
        if not task.skip_if:
            return False

        # Evaluate skip condition
        try:
            # Safe evaluation with context
            return self._eval_condition(task.skip_if, context)
        except Exception as e:
            self.logger.warning(f"Error evaluating skip_if for {task.id}: {e}")
            return False

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a condition."""
        # Support simple conditions like "task_id.exit_code != 0"
        import re

        pattern = r"(\w+)\.(\w+)\s*(==|!=|<|>|<=|>=)\s*(.+)"
        match = re.match(pattern, condition.strip())

        if not match:
            raise ValueError(f"Invalid condition syntax: {condition}")

        task_id, attr, op, value = match.groups()

        if task_id not in self.results:
            raise ValueError(f"Task {task_id} not found in results")

        result = self.results[task_id]
        actual = getattr(result, attr, None)

        if actual is None:
            raise ValueError(f"Attribute {attr} not found in task result")

        # Convert value to appropriate type
        try:
            value = int(value)
        except ValueError:
            value = str(value).strip('"\'')

        ops = {
            "==": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            ">": lambda a, b: a > b,
            "<=": lambda a, b: a <= b,
            ">=": lambda a, b: a >= b,
        }

        return ops[op](actual, value)

    def execute_task(self, task: Task, context: Optional[Dict[str, Any]] = None) -> TaskResult:
        """Execute a single task with retry logic.
        
        Args:
            task: Task to execute
            context: Optional execution context (defaults to empty dict)
        """
        if context is None:
            context = {}
        retry_policy = task.metadata.retry_policy
        last_result = None

        for attempt in range(1, retry_policy.max_attempts + 1):
            # Check skip condition
            if self._should_skip(task, context):
                result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.SKIPPED,
                    attempts=attempt,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                )
                self.results[task.id] = result
                self.logger.info(f"Task {task.id} skipped")
                return result

            try:
                # Execute task
                result = self.task_executor(task, context)
                result.attempts = attempt
                result.start_time = result.start_time or datetime.now()
                result.end_time = result.end_time or datetime.now()
                result.duration = (result.end_time - result.start_time).total_seconds()

                if result.success or result.status == TaskStatus.SKIPPED:
                    self.results[task.id] = result
                    self.logger.info(f"Task {task.id} completed: {result.status.value}")
                    return result

                last_result = result

                # Check retry conditions
                if (
                    attempt < retry_policy.max_attempts
                    and result.exit_code in retry_policy.retry_on_exit_codes
                ):
                    delay = retry_policy.get_delay(attempt)
                    self.logger.warning(
                        f"Task {task.id} failed, retrying in {delay}s "
                        f"(attempt {attempt}/{retry_policy.max_attempts})"
                    )
                    time.sleep(delay)
                    continue

                result.status = TaskStatus.FAILED
                self.results[task.id] = result
                return result

            except Exception as e:
                self.logger.error(f"Task {task.id} error: {e}")
                result = TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    attempts=attempt,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                )
                self.results[task.id] = result

                if attempt < retry_policy.max_attempts:
                    delay = retry_policy.get_delay(attempt)
                    self.logger.warning(f"Retrying {task.id} in {delay}s")
                    time.sleep(delay)
                    continue

                return result

        return last_result or TaskResult(
            task_id=task.id,
            status=TaskStatus.FAILED,
            error="Unknown error",
        )

    def execute_workflow(
        self, dag: WorkflowDAG, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, TaskResult]:
        """
        Execute workflow with parallelism constraints.

        Returns:
            Dictionary mapping task IDs to results
        """
        context = context or {}
        completed: Set[str] = set()
        failed: Set[str] = set()
        skipped: Set[str] = set()
        active_threads: Dict[str, threading.Thread] = {}

        self.logger.info(f"Starting workflow execution with {len(dag.tasks)} tasks")

        while len(completed) + len(failed) + len(skipped) < len(dag.tasks):
            # Get ready tasks
            ready = dag.get_ready_tasks(completed, failed | skipped)

            # Start parallel execution
            for task_id in ready:
                if task_id in self.running_tasks or len(self.running_tasks) >= self.max_parallel:
                    continue

                task = dag.tasks[task_id]
                self.running_tasks.add(task_id)

                def run_task(t: Task):
                    try:
                        result = self.execute_task(t, context)
                        with self.lock:
                            if result.status == TaskStatus.COMPLETED and result.exit_code == 0:
                                completed.add(t.id)
                            elif result.status == TaskStatus.SKIPPED:
                                skipped.add(t.id)
                            else:
                                failed.add(t.id)
                            self.running_tasks.discard(t.id)
                    except Exception as e:
                        self.logger.error(f"Thread error for {t.id}: {e}")
                        with self.lock:
                            failed.add(t.id)
                            self.running_tasks.discard(t.id)

                thread = threading.Thread(target=run_task, args=(task,), daemon=False)
                thread.start()
                active_threads[task_id] = thread

            # Wait a bit before checking again
            time.sleep(0.1)

        # Wait for all threads to finish
        for thread in active_threads.values():
            thread.join(timeout=10)

        self.logger.info(
            f"Workflow completed: {len(completed)} completed, "
            f"{len(failed)} failed, {len(skipped)} skipped"
        )

        return self.results


class WorkflowEngine:
    """High-level workflow orchestration engine."""

    def __init__(self, max_parallel: int = 4, db_path: str = None, **kwargs):
        """Initialize workflow engine.
        
        Args:
            max_parallel: Maximum parallel tasks
            db_path: Optional database path for persistence (for testing)
        """
        self.max_parallel = max_parallel
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.workflows: Dict[str, Tuple[WorkflowDAG, Dict[str, TaskResult]]] = {}

    def create_workflow(self, workflow_id: str) -> WorkflowDAG:
        """Create a new workflow."""
        dag = WorkflowDAG()
        self.workflows[workflow_id] = (dag, {})
        self.logger.info(f"Created workflow {workflow_id}")
        return dag

    def add_task(self, workflow_id: str, task: Task):
        """Add task to workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        dag, _ = self.workflows[workflow_id]

        # Handle matrix expansion
        expanded_tasks = task.expand_matrix()
        for expanded_task in expanded_tasks:
            dag.add_task(expanded_task)

        self.logger.info(f"Added {len(expanded_tasks)} task(s) to workflow {workflow_id}")

    def run_workflow(
        self,
        workflow_id: str,
        task_executor: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, TaskResult]:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow identifier
            task_executor: Custom task executor function
            context: Execution context

        Returns:
            Dictionary of task results
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        dag, _ = self.workflows[workflow_id]

        # Validate DAG
        try:
            dag.topological_sort()
        except ValueError as e:
            self.logger.error(f"Workflow validation failed: {e}")
            raise

        executor = WorkflowExecutor(max_parallel=self.max_parallel, task_executor=task_executor)
        results = executor.execute_workflow(dag, context or {})

        self.workflows[workflow_id] = (dag, results)
        return results

    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get workflow execution status."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        dag, results = self.workflows[workflow_id]

        completed = sum(1 for r in results.values() if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results.values() if r.status == TaskStatus.FAILED)
        skipped = sum(1 for r in results.values() if r.status == TaskStatus.SKIPPED)
        pending = len(dag.tasks) - completed - failed - skipped

        return {
            "workflow_id": workflow_id,
            "total_tasks": len(dag.tasks),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "results": {tid: r.to_dict() for tid, r in results.items()},
        }
