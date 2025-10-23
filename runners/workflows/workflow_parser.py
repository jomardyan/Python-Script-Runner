"""
Workflow Parser - Parse YAML/JSON workflow definitions

Supports:
- YAML and JSON format
- Template variable substitution
- Inline and file-based definitions
- Schema validation
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from .workflow_engine import (
    Task,
    TaskMetadata,
    TaskPriority,
    RetryPolicy,
    WorkflowEngine,
)

try:
    import yaml
except ImportError:
    yaml = None


class WorkflowParser:
    """Parse workflow definitions from YAML or JSON."""

    def __init__(self):
        """Initialize parser."""
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse workflow from file.

        Args:
            file_path: Path to YAML or JSON file

        Returns:
            Parsed workflow configuration
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")

        content = path.read_text()

        if path.suffix.lower() in [".yaml", ".yml"]:
            if yaml is None:
                raise ImportError("PyYAML is required for YAML parsing. Install with: pip install pyyaml")
            return yaml.safe_load(content)
        elif path.suffix.lower() == ".json":
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}")

    def parse_string(self, content: str, format: str = "yaml") -> Dict[str, Any]:
        """
        Parse workflow from string.

        Args:
            content: Workflow definition as string
            format: "yaml" or "json"

        Returns:
            Parsed workflow configuration
        """
        if format.lower() == "yaml":
            if yaml is None:
                raise ImportError("PyYAML is required. Install with: pip install pyyaml")
            return yaml.safe_load(content)
        elif format.lower() == "json":
            return json.loads(content)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def build_tasks(self, workflow_config: Dict[str, Any]) -> List[Task]:
        """
        Build Task objects from parsed configuration.

        Args:
            workflow_config: Parsed workflow configuration

        Returns:
            List of Task objects
        """
        tasks = []
        task_configs = workflow_config.get("tasks", [])

        for task_config in task_configs:
            task = self._parse_task(task_config)
            tasks.append(task)

        return tasks

    def _parse_task(self, task_config: Dict[str, Any]) -> Task:
        """Parse individual task configuration."""
        task_id = task_config.get("id")
        if not task_id:
            raise ValueError("Task must have 'id' field")

        script = task_config.get("script")
        if not script:
            raise ValueError(f"Task {task_id} must have 'script' field")

        # Parse metadata
        metadata_config = task_config.get("metadata", {})
        retry_config = metadata_config.get("retry", {})

        retry_policy = RetryPolicy(
            max_attempts=retry_config.get("max_attempts", 1),
            initial_delay=retry_config.get("initial_delay", 1.0),
            max_delay=retry_config.get("max_delay", 60.0),
            backoff_multiplier=retry_config.get("backoff_multiplier", 2.0),
            retry_on_exit_codes=retry_config.get("retry_on_exit_codes", [1]),
        )

        priority_str = metadata_config.get("priority", "normal").upper()
        try:
            priority = TaskPriority[priority_str]
        except KeyError:
            priority = TaskPriority.NORMAL

        metadata = TaskMetadata(
            name=metadata_config.get("name", task_id),
            description=metadata_config.get("description", ""),
            tags=metadata_config.get("tags", []),
            estimated_duration=metadata_config.get("estimated_duration"),
            timeout=metadata_config.get("timeout", 3600.0),
            priority=priority,
            retry_policy=retry_policy,
        )

        # Parse task
        task = Task(
            id=task_id,
            script=script,
            metadata=metadata,
            depends_on=task_config.get("depends_on", []),
            skip_if=task_config.get("skip_if"),
            run_always=task_config.get("run_always", False),
            env=task_config.get("env", {}),
            inputs=task_config.get("inputs", {}),
            outputs=task_config.get("outputs", []),
            matrix=task_config.get("matrix"),
        )

        return task

    def build_workflow(
        self, workflow_config: Dict[str, Any], workflow_engine: WorkflowEngine
    ) -> str:
        """
        Build workflow in engine from configuration.

        Args:
            workflow_config: Parsed workflow configuration
            workflow_engine: WorkflowEngine instance

        Returns:
            Workflow ID
        """
        workflow_id = workflow_config.get("id", "default")
        engine_config = workflow_config.get("config", {})

        # Create workflow
        dag = workflow_engine.create_workflow(workflow_id)

        # Add tasks
        tasks = self.build_tasks(workflow_config)
        for task in tasks:
            workflow_engine.add_task(workflow_id, task)

        self.logger.info(f"Built workflow {workflow_id} with {len(tasks)} task(s)")
        return workflow_id

    def validate_schema(self, workflow_config: Dict[str, Any]) -> List[str]:
        """
        Validate workflow configuration schema.

        Args:
            workflow_config: Configuration to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if "tasks" not in workflow_config:
            errors.append("Missing 'tasks' field")
            return errors

        tasks = workflow_config.get("tasks", [])
        if not isinstance(tasks, list):
            errors.append("'tasks' must be a list")
            return errors

        task_ids = set()
        for i, task_config in enumerate(tasks):
            if not isinstance(task_config, dict):
                errors.append(f"Task {i} is not a dictionary")
                continue

            # Check required fields
            if "id" not in task_config:
                errors.append(f"Task {i} missing 'id' field")
            elif task_config["id"] in task_ids:
                errors.append(f"Duplicate task id: {task_config['id']}")
            else:
                task_ids.add(task_config["id"])

            if "script" not in task_config:
                errors.append(f"Task {task_config.get('id', i)} missing 'script' field")

            # Validate dependencies
            for dep in task_config.get("depends_on", []):
                if dep not in task_ids and dep not in [t.get("id") for t in tasks]:
                    errors.append(
                        f"Task {task_config.get('id')} depends on non-existent task {dep}"
                    )

        return errors
