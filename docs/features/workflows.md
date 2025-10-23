# DAG-Based Workflow Orchestration

## Overview

Python Script Runner v7.0+ includes a sophisticated DAG (Directed Acyclic Graph) workflow engine for orchestrating complex multi-step processes with dependencies, parallel execution, and conditional branching.

## Why Workflow Orchestration?

- **Complex Workflows**: Manage 100+ step pipelines with dependencies
- **Parallel Execution**: Run independent tasks simultaneously
- **Error Recovery**: Smart retry logic and conditional branching
- **Monitoring**: Real-time progress tracking and metrics
- **Scalability**: From laptop to Kubernetes clusters

## Installation

```bash
pip install 'python-script-runner[all]'
# or just workflows:
pip install python-script-runner  # workflows included by default
```

## Quick Start

### 1. Define a Workflow

```yaml
# workflow.yaml
name: Data Processing Pipeline
version: 1.0.0

tasks:
  extract_data:
    script: ./scripts/extract.py
    timeout_minutes: 30
    retries: 2

  transform_data:
    script: ./scripts/transform.py
    depends_on: [extract_data]
    timeout_minutes: 60
    parallelism: 4

  validate_data:
    script: ./scripts/validate.py
    depends_on: [transform_data]
    timeout_minutes: 15

  load_data:
    script: ./scripts/load.py
    depends_on: [validate_data]
    timeout_minutes: 45

  notify_completion:
    script: ./scripts/notify.py
    depends_on: [load_data]
    timeout_minutes: 5
    run_always: true
```

### 2. Execute the Workflow

```python
from runner.workflows import WorkflowEngine, WorkflowParser

# Parse workflow
parser = WorkflowParser()
workflow = parser.parse_yaml('workflow.yaml')

# Execute
engine = WorkflowEngine()
result = engine.run(workflow)

# Check results
print(f"Status: {result.status}")  # success, failed, partial
print(f"Duration: {result.duration_seconds}s")
print(f"Tasks completed: {result.completed_count}/{result.total_count}")
```

### 3. Monitor Progress

```python
# Real-time monitoring
for event in engine.stream_events():
    if event.type == 'task_started':
        print(f"▶️  {event.task_name} starting...")
    elif event.type == 'task_completed':
        print(f"✅ {event.task_name} completed in {event.duration}s")
    elif event.type == 'task_failed':
        print(f"❌ {event.task_name} failed: {event.error}")
```

## Workflow Concepts

### Tasks

Individual units of work:

```yaml
my_task:
  script: ./scripts/my_script.py
  
  # Execution options
  timeout_minutes: 30
  retries: 2
  retry_backoff: exponential
  
  # Environment
  environment:
    LOG_LEVEL: INFO
    DB_HOST: db.example.com
  
  # Resource allocation
  cpu_cores: 2
  memory_mb: 4096
  
  # Conditional execution
  skip_if: '{{ previous_task.failed }}'
  run_always: false  # Run even if dependencies fail
```

### Dependencies

Define task relationships:

```yaml
# Serial dependency
task_b:
  depends_on: [task_a]

# Parallel dependencies (fan-out)
task_c:
  depends_on: [task_a]

task_d:
  depends_on: [task_a]

# Convergence (fan-in)
task_e:
  depends_on: [task_c, task_d]
```

### Conditional Execution

```yaml
tasks:
  process_data:
    script: ./scripts/process.py

  send_alert:
    script: ./scripts/alert.py
    depends_on: [process_data]
    condition: '{{ process_data.exit_code != 0 }}'  # Run if failed

  generate_report:
    script: ./scripts/report.py
    depends_on: [process_data]
    condition: '{{ process_data.exit_code == 0 }}'  # Run if succeeded
```

### Parallelism

```yaml
transform_users:
  script: ./scripts/transform_user_batch.py
  depends_on: [extract_data]
  parallelism: 8  # Run 8 instances in parallel
  matrix:
    batch_id: [0, 1, 2, 3, 4, 5, 6, 7]
  environment:
    BATCH_ID: '{{ matrix.batch_id }}'
```

## Advanced Features

### Error Handling

```yaml
risky_operation:
  script: ./scripts/risky.py
  retries: 3
  retry_backoff: exponential
  retry_delay_ms: 1000

recovery_task:
  script: ./scripts/recover.py
  depends_on: [risky_operation]
  run_always: true  # Run even if dependency fails
```

### Resource Management

```yaml
memory_intensive_task:
  script: ./scripts/big_data.py
  cpu_cores: 8
  memory_mb: 32768
  disk_gb: 100
  timeout_minutes: 180

io_bound_task:
  script: ./scripts/api_calls.py
  cpu_cores: 2
  memory_mb: 512
```

### Notifications

```yaml
workflow:
  name: Important Pipeline
  
  tasks:
    main_task:
      script: ./scripts/main.py
  
  notifications:
    on_success:
      - type: slack
        webhook: '{{ env.SLACK_WEBHOOK }}'
        message: 'Pipeline completed successfully'
    
    on_failure:
      - type: email
        recipients: ['ops@example.com']
        subject: 'Pipeline failed'
      
      - type: pagerduty
        integration_key: '{{ env.PD_KEY }}'
```

## Real-World Examples

### Example 1: ETL Pipeline

```yaml
name: Daily Data ETL
version: 1.0.0

tasks:
  # Extract
  fetch_from_api:
    script: ./etl/extract_api.py
    timeout_minutes: 60
    environment:
      API_ENDPOINT: https://api.example.com/v1

  fetch_from_db:
    script: ./etl/extract_db.py
    timeout_minutes: 30

  # Transform (parallel)
  transform_api_data:
    script: ./etl/transform.py
    depends_on: [fetch_from_api]
    environment:
      SOURCE: api

  transform_db_data:
    script: ./etl/transform.py
    depends_on: [fetch_from_db]
    environment:
      SOURCE: db

  # Validate & Merge
  validate_and_merge:
    script: ./etl/validate_merge.py
    depends_on: [transform_api_data, transform_db_data]
    timeout_minutes: 45

  # Load
  load_warehouse:
    script: ./etl/load.py
    depends_on: [validate_and_merge]
    timeout_minutes: 90

  # Notify
  send_report:
    script: ./etl/send_report.py
    depends_on: [load_warehouse]
    run_always: true
```

### Example 2: Distributed Batch Processing

```yaml
name: Batch Data Processing
version: 1.0.0

tasks:
  prepare_batches:
    script: ./batch/prepare.py
    timeout_minutes: 15

  process_batch:
    script: ./batch/process.py
    depends_on: [prepare_batches]
    parallelism: 16  # Process 16 batches in parallel
    matrix:
      batch_num: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    environment:
      BATCH_NUM: '{{ matrix.batch_num }}'
    timeout_minutes: 120

  aggregate_results:
    script: ./batch/aggregate.py
    depends_on: [process_batch]
    timeout_minutes: 30

  publish_results:
    script: ./batch/publish.py
    depends_on: [aggregate_results]
    timeout_minutes: 15
```

### Example 3: Resilient Multi-Service Workflow

```yaml
name: Production Deployment Pipeline
version: 1.0.0

tasks:
  run_tests:
    script: ./ci/test.py
    timeout_minutes: 30

  security_scan:
    script: ./ci/security.py
    timeout_minutes: 20

  build_artifacts:
    script: ./ci/build.py
    depends_on: [run_tests, security_scan]
    timeout_minutes: 45

  deploy_staging:
    script: ./cd/deploy.py
    depends_on: [build_artifacts]
    environment:
      ENVIRONMENT: staging
    timeout_minutes: 30

  smoke_tests:
    script: ./cd/smoke_tests.py
    depends_on: [deploy_staging]
    timeout_minutes: 15

  deploy_production:
    script: ./cd/deploy.py
    depends_on: [smoke_tests]
    environment:
      ENVIRONMENT: production
    timeout_minutes: 45

  notify_team:
    script: ./cd/notify.py
    depends_on: [deploy_production]
    run_always: true
```

## Integration with Python Script Runner Features

### Distributed Tracing

```python
from runner.workflows import WorkflowEngine, WorkflowParser

parser = WorkflowParser()
workflow = parser.parse_yaml('workflow.yaml')

engine = WorkflowEngine(enable_tracing=True)
result = engine.run(workflow)

print(f"Trace ID: {result.trace_id}")  # View in Jaeger/Zipkin
```

### Cost Attribution

```python
engine = WorkflowEngine(enable_cost_tracking=True)
result = engine.run(workflow)

for task_result in result.tasks:
    print(f"{task_result.name}: ${task_result.cost:.2f}")

print(f"Total cost: ${result.total_cost:.2f}")
```

## CLI Integration

```bash
# Run workflow
python-script-runner workflow.yaml

# With options
python-script-runner workflow.yaml \
  --dry-run \
  --parallelism 8 \
  --timeout 300 \
  --enable-tracing \
  --output results.json

# View workflow status
python-script-runner workflow.yaml --status

# Cancel running workflow
python-script-runner workflow.yaml --cancel
```

## Performance Characteristics

| Aspect | Value |
|--------|-------|
| Max tasks per workflow | 1000+ |
| Max parallelism | Limited by system resources |
| Task startup time | ~100ms |
| Overhead per task | <5% CPU |
| Memory per workflow | ~50MB base + task memory |

## Troubleshooting

### Tasks Not Running

```yaml
# Add depends_on for serial execution
task_a:
  script: ./scripts/a.py

task_b:
  script: ./scripts/b.py
  depends_on: [task_a]  # task_b waits for task_a
```

### High Memory Usage

```yaml
# Reduce parallelism
transform_data:
  parallelism: 4  # Reduce from 8
  memory_mb: 2048  # Limit per task
```

### Slow Execution

```yaml
# Increase parallelism for independent tasks
parallel_tasks:
  parallelism: 16
  matrix:
    item: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
```

## Related Documentation

- [Apache Airflow](https://airflow.apache.org/) - Similar DAG concepts
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [Kubeflow Pipelines](https://www.kubeflow.org/) - Kubernetes workflows
- [Dagster](https://dagster.io/) - Data orchestration
