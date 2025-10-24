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
import os
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
    metadata: Optional[TaskMetadata] = None
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
        # Initialize default metadata if not provided
        if self.metadata is None:
            self.metadata = TaskMetadata(name=self.id)

    def expand_matrix(self) -> List["Task"]:
        """Expand matrix into multiple tasks."""
        if not self.matrix:
            return [self]

        expanded = []
        # Handle 'include' key specially - it adds extra configurations
        include_configs = self.matrix.pop('include', [])
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
        
        # Add included configurations
        for include_config in include_configs:
            task_copy = Task(
                id=f"{self.id}[{','.join(str(v) for v in include_config.values())}]",
                script=self.script.format(**include_config),
                metadata=self.metadata,
                depends_on=self.depends_on,
                skip_if=self.skip_if,
                run_always=self.run_always,
                env={**self.env, **include_config},
                inputs=self.inputs,
                outputs=self.outputs,
            )
            expanded.append(task_copy)
        
        return expanded


class WorkflowDAG:
    """Directed Acyclic Graph for workflow tasks."""

    def __init__(self, name: str = None, **kwargs):
        """Initialize DAG.
        
        Args:
            name: Optional name for the DAG (for testing/tracking)
        """
        self.name = name or "default_dag"
        self.id = kwargs.get('id', self.name)
        self.tasks: Dict[str, Task] = {}
        self.graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.logger = logging.getLogger(__name__)
        # Track execution state for get_ready_tasks without parameters
        self.completed: Set[str] = set()
        self.failed: Set[str] = set()

    def add_task(self, task: Task):
        """Add task to DAG."""
        if task.id in self.tasks:
            raise ValueError(f"Task {task.id} already exists")

        self.tasks[task.id] = task

        # Build adjacency lists (defer validation to topological_sort)
        for dep in task.depends_on:
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
            raise ValueError("cycle detected in task dependencies")

        return sorted_list

    def get_ready_tasks(self, completed: Set[str] = None, failed: Set[str] = None) -> List[Task]:
        """Get tasks ready for execution.
        
        Args:
            completed: Set of completed task IDs (defaults to self.completed)
            failed: Set of failed task IDs (defaults to self.failed)
            
        Returns:
            List of Task objects ready to execute
        """
        # Use instance state if not provided
        if completed is None:
            completed = self.completed.copy()
        if failed is None:
            failed = self.failed.copy()
        
        # Also mark tasks with COMPLETED status as completed
        for task_id, task in self.tasks.items():
            if hasattr(task, 'status') and task.status == TaskStatus.COMPLETED:
                completed.add(task_id)
            
        ready = []
        for task_id, dependencies in self.reverse_graph.items():
            task = self.tasks[task_id]
            # Skip if already completed/failed
            if task_id in completed or task_id in failed:
                continue
            # All dependencies must be completed
            if dependencies.issubset(completed):
                ready.append(task)
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

    def validate(self) -> List[str]:
        """Validate DAG consistency and dependencies.
        
        Returns:
            List of validation errors (empty if valid)
            
        Raises:
            ValueError: If validation errors are found
        """
        errors = []
        
        # Check for cycles
        try:
            self.topological_sort()
        except ValueError as e:
            errors.append(str(e))
        
        # Check dependencies exist
        for task_id, task in self.tasks.items():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    errors.append(f"Task {task_id} depends on non-existent dependency {dep}")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return errors


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
        """Default task executor (executes shell commands with timeout and retry)."""
        import subprocess
        
        self.logger.info(f"Executing task {task.id}: {task.script}")
        start_time = datetime.now()
        
        try:
            timeout = task.metadata.timeout if task.metadata else 3600.0
            # Run the actual subprocess command
            process = subprocess.Popen(
                task.script,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **task.env} if hasattr(task, 'env') else None,
            )
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                return TaskResult(
                    task_id=task.id,
                    status=TaskStatus.FAILED,
                    exit_code=-1,
                    stderr=f"Task timed out after {timeout}s",
                    duration=(datetime.now() - start_time).total_seconds(),
                    start_time=start_time,
                    end_time=datetime.now(),
                    error=f"Task timed out after {timeout}s",
                )
            
            end_time = datetime.now()
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED if exit_code == 0 else TaskStatus.FAILED,
                exit_code=exit_code,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                duration=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            end_time = datetime.now()
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                exit_code=-1,
                error=str(e),
                stderr=str(e),
                duration=(end_time - start_time).total_seconds(),
                start_time=start_time,
                end_time=end_time,
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
        
        # Ensure task has metadata with retry policy
        if not task.metadata:
            task.metadata = TaskMetadata(name=task.id)
        
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
            for task in ready:
                if task.id in self.running_tasks or len(self.running_tasks) >= self.max_parallel:
                    continue

                self.running_tasks.add(task.id)

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
                active_threads[task.id] = thread

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
        self.next_workflow_id = 0

    def create_workflow(self, workflow_id: str = None) -> WorkflowDAG:
        """Create a new workflow."""
        if workflow_id is None:
            workflow_id = f"workflow_{self.next_workflow_id}"
            self.next_workflow_id += 1
        dag = WorkflowDAG(name=workflow_id)
        self.workflows[workflow_id] = (dag, {})
        self.logger.info(f"Created workflow {workflow_id}")
        return dag

    def create_workflow_from_dict(self, workflow_dict: Dict[str, Any]) -> WorkflowDAG:
        """Create workflow from dictionary configuration.
        
        Args:
            workflow_dict: Dictionary with 'name' and 'tasks' keys
                tasks format: [{'id': 'task1', 'script': 'echo hello', ...}, ...]
        
        Returns:
            WorkflowDAG instance
        """
        workflow_name = workflow_dict.get('name', f'workflow_{self.next_workflow_id}')
        dag = WorkflowDAG(name=workflow_name)
        
        # Add tasks to DAG
        for task_dict in workflow_dict.get('tasks', []):
            task_id = task_dict.get('id')
            script = task_dict.get('script')
            depends_on = task_dict.get('depends_on', [])
            skip_if = task_dict.get('skip_if')
            run_always = task_dict.get('run_always', False)
            env = task_dict.get('env', {})
            inputs = task_dict.get('inputs', {})
            outputs = task_dict.get('outputs', [])
            matrix = task_dict.get('matrix')
            
            # Create task metadata
            metadata_dict = task_dict.get('metadata', {})
            metadata = TaskMetadata(
                name=metadata_dict.get('name', task_id),
                description=metadata_dict.get('description', ''),
                tags=metadata_dict.get('tags', []),
                estimated_duration=metadata_dict.get('estimated_duration'),
                timeout=metadata_dict.get('timeout', 3600.0),
                priority=TaskPriority[metadata_dict.get('priority', 'NORMAL')],
                retry_policy=RetryPolicy(**metadata_dict.get('retry_policy', {}))
            )
            
            task = Task(
                id=task_id,
                script=script,
                metadata=metadata,
                depends_on=depends_on,
                skip_if=skip_if,
                run_always=run_always,
                env=env,
                inputs=inputs,
                outputs=outputs,
                matrix=matrix
            )
            dag.add_task(task)
        
        self.workflows[workflow_name] = (dag, {})
        self.next_workflow_id += 1
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
        workflow_id,
        task_executor: Optional[Callable] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, TaskResult]:
        """
        Execute a workflow.

        Args:
            workflow_id: Workflow identifier (str) or WorkflowDAG object
            task_executor: Custom task executor function
            context: Execution context

        Returns:
            Dictionary of task results
        """
        # Handle both string IDs and WorkflowDAG objects
        if isinstance(workflow_id, WorkflowDAG):
            dag = workflow_id
            workflow_id = dag.name
            # Auto-register if not already registered
            if workflow_id not in self.workflows:
                self.workflows[workflow_id] = (dag, {})
        elif workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        else:
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
        
        # Check if all tasks succeeded
        all_succeeded = all(r.status == TaskStatus.COMPLETED for r in results.values())
        
        return {
            "success": all_succeeded,
            "results": [
                {**r.to_dict(), "success": r.status == TaskStatus.COMPLETED}
                for r in results.values()
            ],
            "details": {tid: r.to_dict() for tid, r in results.items()},
        }

    def get_workflow_status(self, workflow_id) -> Dict[str, Any]:
        """Get workflow execution status."""
        # Handle both string IDs and WorkflowDAG objects
        if isinstance(workflow_id, WorkflowDAG):
            dag = workflow_id
            workflow_id = dag.name
        elif workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        else:
            dag, results = self.workflows[workflow_id]

        # If we have a DAG but not registered, get empty results
        if workflow_id in self.workflows:
            dag, results = self.workflows[workflow_id]
        else:
            results = {}

        completed = sum(1 for r in results.values() if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results.values() if r.status == TaskStatus.FAILED)
        skipped = sum(1 for r in results.values() if r.status == TaskStatus.SKIPPED)
        pending = len(dag.tasks) - completed - failed - skipped

        return {
            "workflow_id": workflow_id,
            "total_tasks": len(dag.tasks),
            "completed_tasks": completed,
            "failed_tasks": failed,
            "skipped_tasks": skipped,
            "pending_tasks": pending,
            "results": {tid: r.to_dict() for tid, r in results.items()},
        }
