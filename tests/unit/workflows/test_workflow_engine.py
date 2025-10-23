"""
Unit tests for DAG-Based Workflow Engine.
Tests for WorkflowEngine, WorkflowExecutor, WorkflowDAG, and WorkflowParser.
Coverage target: 85%+
"""

import pytest
import time
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runners.workflows.workflow_engine import (
    TaskStatus, TaskPriority, RetryPolicy, TaskMetadata,
    TaskResult, Task, WorkflowDAG, WorkflowExecutor, WorkflowEngine
)


class TestTaskCreation:
    """Test Task and TaskMetadata creation."""
    
    def test_task_metadata_with_defaults(self, sample_task_metadata):
        """Test creating TaskMetadata with default values."""
        metadata = TaskMetadata(**sample_task_metadata)
        assert metadata.name == 'test_task'
        assert metadata.description == 'Test task for unit tests'
        assert metadata.timeout == 30
        assert metadata.priority == 1
        assert 'test' in metadata.tags
    
    def test_task_creation_simple(self):
        """Test creating a simple task."""
        task = Task(
            id='task1',
            script='echo hello',
            metadata=None,
            depends_on=[]
        )
        assert task.id == 'task1'
        assert task.script == 'echo hello'
        assert len(task.depends_on) == 0
        assert task.status == TaskStatus.PENDING
    
    def test_task_with_dependencies(self):
        """Test creating a task with dependencies."""
        task = Task(
            id='task2',
            script='cat input.txt',
            depends_on=['task1', 'task0'],
            metadata=None
        )
        assert len(task.depends_on) == 2
        assert 'task1' in task.depends_on
        assert 'task0' in task.depends_on
    
    def test_task_with_retry_policy(self):
        """Test task with retry policy."""
        retry = RetryPolicy(
            max_attempts=3,
            initial_delay=1.0,
            max_delay=10.0,
            backoff_multiplier=2.0
        )
        task = Task(
            id='task_retry',
            script='flaky_command',
            depends_on=[],
            metadata=TaskMetadata(name='retry_task', retry_policy=retry)
        )
        assert task.metadata.retry_policy.max_attempts == 3
        assert task.metadata.retry_policy.backoff_multiplier == 2.0
    
    def test_task_result_creation(self):
        """Test creating TaskResult."""
        result = TaskResult(
            task_id='task1',
            status=TaskStatus.COMPLETED,
            exit_code=0,
            stdout='Success',
            stderr='',
            duration=5.5,
            attempts=1
        )
        assert result.task_id == 'task1'
        assert result.status == TaskStatus.COMPLETED
        assert result.exit_code == 0
        assert result.success
        assert result.duration == 5.5


class TestWorkflowDAG:
    """Test Workflow DAG (Directed Acyclic Graph) operations."""
    
    def test_dag_creation(self):
        """Test creating an empty DAG."""
        dag = WorkflowDAG(name='test_dag')
        assert dag.name == 'test_dag'
        assert len(dag.tasks) == 0
    
    def test_add_task_to_dag(self):
        """Test adding tasks to DAG."""
        dag = WorkflowDAG(name='test_dag')
        task = Task(id='task1', script='echo hello', depends_on=[], metadata=None)
        dag.add_task(task)
        
        assert len(dag.tasks) == 1
        assert dag.tasks['task1'] == task
    
    def test_topological_sort_linear(self):
        """Test topological sort with linear dependency chain."""
        dag = WorkflowDAG(name='linear_dag')
        
        # Create chain: task1 -> task2 -> task3
        task1 = Task(id='task1', script='cmd1', depends_on=[], metadata=None)
        task2 = Task(id='task2', script='cmd2', depends_on=['task1'], metadata=None)
        task3 = Task(id='task3', script='cmd3', depends_on=['task2'], metadata=None)
        
        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        
        sorted_tasks = dag.topological_sort()
        assert sorted_tasks == ['task1', 'task2', 'task3']
    
    def test_topological_sort_parallel(self):
        """Test topological sort with independent parallel tasks."""
        dag = WorkflowDAG(name='parallel_dag')
        
        # Create parallel tasks: task1, task2, task3 (no dependencies)
        for i in range(1, 4):
            task = Task(id=f'task{i}', script=f'cmd{i}', depends_on=[], metadata=None)
            dag.add_task(task)
        
        sorted_tasks = dag.topological_sort()
        assert len(sorted_tasks) == 3
        assert set(sorted_tasks) == {'task1', 'task2', 'task3'}
    
    def test_topological_sort_complex(self):
        """Test topological sort with complex dependencies."""
        dag = WorkflowDAG(name='complex_dag')
        
        # Complex graph:
        #   task1 -> task3 -\
        #   task2 -> task4 -> task5
        dag.add_task(Task(id='task1', script='cmd1', depends_on=[], metadata=None))
        dag.add_task(Task(id='task2', script='cmd2', depends_on=[], metadata=None))
        dag.add_task(Task(id='task3', script='cmd3', depends_on=['task1'], metadata=None))
        dag.add_task(Task(id='task4', script='cmd4', depends_on=['task2'], metadata=None))
        dag.add_task(Task(id='task5', script='cmd5', depends_on=['task3', 'task4'], metadata=None))
        
        sorted_tasks = dag.topological_sort()
        
        # Verify ordering constraints
        assert sorted_tasks.index('task1') < sorted_tasks.index('task3')
        assert sorted_tasks.index('task2') < sorted_tasks.index('task4')
        assert sorted_tasks.index('task3') < sorted_tasks.index('task5')
        assert sorted_tasks.index('task4') < sorted_tasks.index('task5')
    
    def test_cycle_detection(self):
        """Test that cycles are detected in DAG."""
        dag = WorkflowDAG(name='cyclic_dag')
        
        # Create cycle: task1 -> task2 -> task1
        dag.add_task(Task(id='task1', script='cmd1', depends_on=['task2'], metadata=None))
        dag.add_task(Task(id='task2', script='cmd2', depends_on=['task1'], metadata=None))
        
        with pytest.raises(ValueError, match='cycle'):
            dag.topological_sort()
    
    def test_get_ready_tasks(self):
        """Test identifying ready tasks (no pending dependencies)."""
        dag = WorkflowDAG(name='ready_dag')
        
        # Create tasks
        task1 = Task(id='task1', script='cmd1', depends_on=[], metadata=None)
        task2 = Task(id='task2', script='cmd2', depends_on=['task1'], metadata=None)
        task3 = Task(id='task3', script='cmd3', depends_on=['task1'], metadata=None)
        
        dag.add_task(task1)
        dag.add_task(task2)
        dag.add_task(task3)
        
        # Mark task1 as completed
        dag.tasks['task1'].status = TaskStatus.COMPLETED
        
        ready = dag.get_ready_tasks()
        assert 'task1' not in [t.id for t in ready]  # Already completed
        assert 'task2' in [t.id for t in ready]
        assert 'task3' in [t.id for t in ready]


class TestWorkflowExecutor:
    """Test WorkflowExecutor for task execution."""
    
    def test_executor_creation(self):
        """Test creating a WorkflowExecutor."""
        executor = WorkflowExecutor(max_parallel=4)
        assert executor.max_parallel == 4
    
    @patch('subprocess.Popen')
    def test_execute_single_task_success(self, mock_popen):
        """Test executing a single task successfully."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'Success', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        executor = WorkflowExecutor()
        task = Task(id='task1', script='echo hello', depends_on=[], metadata=None)
        
        result = executor.execute_task(task)
        
        assert result.task_id == 'task1'
        assert result.status == TaskStatus.COMPLETED
        assert result.exit_code == 0
        assert result.success
    
    @patch('subprocess.Popen')
    def test_execute_task_failure(self, mock_popen):
        """Test task execution failure."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'', b'Error')
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        executor = WorkflowExecutor()
        task = Task(id='task1', script='false', depends_on=[], metadata=None)
        
        result = executor.execute_task(task)
        
        assert result.status == TaskStatus.FAILED
        assert result.exit_code == 1
        assert not result.success
    
    @patch('subprocess.Popen')
    @patch('time.sleep')
    def test_execute_with_retry(self, mock_sleep, mock_popen):
        """Test task execution with retry on failure."""
        # First two calls fail, third succeeds
        mock_process_fail = MagicMock()
        mock_process_fail.communicate.return_value = (b'', b'Error')
        mock_process_fail.returncode = 1
        
        mock_process_success = MagicMock()
        mock_process_success.communicate.return_value = (b'Success', b'')
        mock_process_success.returncode = 0
        
        mock_popen.side_effect = [mock_process_fail, mock_process_fail, mock_process_success]
        
        retry_policy = RetryPolicy(max_attempts=3, initial_delay=0.1)
        executor = WorkflowExecutor()
        task = Task(
            id='task1',
            script='flaky',
            depends_on=[],
            metadata=TaskMetadata(name='retry_task', retry_policy=retry_policy)
        )
        
        result = executor.execute_task(task)
        
        assert result.status == TaskStatus.COMPLETED
        assert result.attempts == 3
    
    @patch('subprocess.Popen')
    def test_execute_with_timeout(self, mock_popen):
        """Test task execution with timeout."""
        mock_process = MagicMock()
        mock_process.communicate.side_effect = TimeoutError()
        mock_popen.return_value = mock_process
        
        executor = WorkflowExecutor()
        task = Task(
            id='task1',
            script='sleep 1000',
            depends_on=[],
            metadata=TaskMetadata(name='timeout_task', timeout=1)
        )
        
        result = executor.execute_task(task)
        
        assert result.status == TaskStatus.FAILED


class TestWorkflowEngine:
    """Test high-level WorkflowEngine operations."""
    
    def test_engine_creation(self, temp_db):
        """Test creating a WorkflowEngine."""
        engine = WorkflowEngine(db_path=temp_db)
        assert engine is not None
    
    def test_create_workflow(self, sample_workflow_dict, temp_db):
        """Test creating a workflow from dictionary."""
        engine = WorkflowEngine(db_path=temp_db)
        workflow = engine.create_workflow_from_dict(sample_workflow_dict)
        
        assert workflow.name == 'test_workflow'
        assert len(workflow.tasks) == 2
        assert 'task1' in workflow.tasks
        assert 'task2' in workflow.tasks
    
    @patch('subprocess.Popen')
    def test_run_simple_workflow(self, mock_popen, sample_workflow_dict, temp_db):
        """Test running a simple workflow."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'Output', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        engine = WorkflowEngine(db_path=temp_db)
        workflow = engine.create_workflow_from_dict(sample_workflow_dict)
        
        result = engine.run_workflow(workflow)
        
        assert result['success']
        assert len(result['results']) == 2
    
    def test_workflow_status_tracking(self, sample_workflow_dict, temp_db):
        """Test tracking workflow execution status."""
        engine = WorkflowEngine(db_path=temp_db)
        workflow = engine.create_workflow_from_dict(sample_workflow_dict)
        
        # Check initial status
        status = engine.get_workflow_status(workflow.id)
        assert status['total_tasks'] == 2
        assert status['completed_tasks'] == 0


class TestMatrixExpansion:
    """Test matrix task expansion for parameterized execution."""
    
    def test_matrix_expansion_single_parameter(self):
        """Test expanding matrix with single parameter."""
        matrix_config = {
            'python_version': ['3.8', '3.9', '3.10']
        }
        
        task = Task(
            id='test_task',
            script='python -c "import sys; print(sys.version)"',
            depends_on=[],
            metadata=None,
            matrix=matrix_config
        )
        
        expanded = task.expand_matrix()
        
        assert len(expanded) == 3
        assert all(isinstance(t, Task) for t in expanded)
    
    def test_matrix_expansion_multiple_parameters(self):
        """Test expanding matrix with multiple parameters."""
        matrix_config = {
            'python_version': ['3.8', '3.9'],
            'os': ['ubuntu', 'macos']
        }
        
        task = Task(
            id='test_task',
            script='python test.py',
            depends_on=[],
            metadata=None,
            matrix=matrix_config
        )
        
        expanded = task.expand_matrix()
        
        # Should create 2 x 2 = 4 combinations
        assert len(expanded) == 4
    
    def test_matrix_with_include(self):
        """Test matrix with additional include configurations."""
        matrix_config = {
            'python_version': ['3.8', '3.9'],
            'include': [
                {'python_version': '3.11', 'experimental': True}
            ]
        }
        
        task = Task(
            id='test_task',
            script='python test.py',
            depends_on=[],
            metadata=None,
            matrix=matrix_config
        )
        
        expanded = task.expand_matrix()
        
        # 2 base versions + 1 included = 3
        assert len(expanded) == 3


class TestWorkflowParsing:
    """Test workflow definition parsing."""
    
    def test_parse_workflow_yaml(self, sample_workflow_yaml, temp_db):
        """Test parsing YAML workflow file."""
        from runners.workflows.workflow_parser import WorkflowParser
        
        parser = WorkflowParser()
        workflow = parser.parse_file(str(sample_workflow_yaml))
        
        assert workflow.name == 'test_workflow'
        assert len(workflow.tasks) == 2
    
    def test_parse_workflow_json(self, tmp_path, sample_workflow_dict):
        """Test parsing JSON workflow file."""
        import json
        from runners.workflows.workflow_parser import WorkflowParser
        
        workflow_file = tmp_path / "workflow.json"
        workflow_file.write_text(json.dumps(sample_workflow_dict))
        
        parser = WorkflowParser()
        workflow = parser.parse_file(str(workflow_file))
        
        assert workflow.name == 'test_workflow'


class TestErrorHandling:
    """Test error handling in workflow execution."""
    
    def test_task_with_invalid_dependencies(self):
        """Test task with non-existent dependencies."""
        dag = WorkflowDAG(name='invalid_dag')
        task = Task(
            id='task1',
            script='cmd',
            depends_on=['nonexistent_task'],
            metadata=None
        )
        dag.add_task(task)
        
        with pytest.raises(ValueError, match='dependency'):
            dag.validate()
    
    def test_missing_script(self):
        """Test task with missing script."""
        with pytest.raises(ValueError):
            Task(id='task1', script='', depends_on=[], metadata=None)
    
    @patch('subprocess.Popen')
    def test_subprocess_error(self, mock_popen):
        """Test handling subprocess errors."""
        mock_popen.side_effect = OSError("Command not found")
        
        executor = WorkflowExecutor()
        task = Task(id='task1', script='nonexistent_cmd', depends_on=[], metadata=None)
        
        result = executor.execute_task(task)
        
        assert result.status == TaskStatus.FAILED


# ============================================================================
# INTEGRATION TESTS FOR WORKFLOW ENGINE
# ============================================================================

@pytest.mark.integration
class TestWorkflowEngineIntegration:
    """Integration tests for complete workflow execution."""
    
    @patch('subprocess.Popen')
    def test_complete_workflow_execution(self, mock_popen, sample_workflow_dict, temp_db):
        """Test executing a complete workflow end-to-end."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = (b'Success', b'')
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        engine = WorkflowEngine(db_path=temp_db)
        workflow = engine.create_workflow_from_dict(sample_workflow_dict)
        result = engine.run_workflow(workflow)
        
        assert result['success']
        assert all(r['success'] for r in result['results'])
        assert len(result['results']) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=runners.workflows'])
