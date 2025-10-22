# Metrics

## Collected Metrics

### Timing
- `start_time` - ISO 8601 timestamp
- `end_time` - ISO 8601 timestamp
- `execution_time_seconds` - Total duration

### Exit Status
- `exit_code` - Process exit code
- `success` - Boolean success flag
- `error_message` - Error message if failed

### CPU Metrics
- `cpu_max` - Peak CPU utilization (%)
- `cpu_avg` - Average CPU utilization (%)
- `cpu_min` - Minimum CPU utilization (%)
- `user_time_seconds` - User mode time
- `system_time_seconds` - System mode time

### Memory Metrics
- `memory_max_mb` - Peak memory (MB)
- `memory_avg_mb` - Average memory (MB)
- `memory_min_mb` - Minimum memory (MB)
- `page_faults_minor` - Minor page faults
- `page_faults_major` - Major page faults

### System Resources
- `num_threads` - Thread count
- `num_fds` - File descriptor count
- `voluntary_context_switches` - Voluntary switches
- `involuntary_context_switches` - Involuntary switches
- `block_io_read_bytes` - Bytes read
- `block_io_write_bytes` - Bytes written

### Output Metrics
- `stdout_lines` - Lines of stdout
- `stderr_lines` - Lines of stderr
- `stdout_size_bytes` - Stdout size
- `stderr_size_bytes` - Stderr size

## JSON Output Format

```json
{
  "script_path": "train.py",
  "script_args": ["--epochs", "100"],
  "start_time": "2024-11-15T10:30:00.123456",
  "end_time": "2024-11-15T10:35:45.654321",
  "execution_time_seconds": 345.531,
  "exit_code": 0,
  "success": true,
  "cpu_max": 87.5,
  "cpu_avg": 62.3,
  "memory_max_mb": 512.3,
  "memory_avg_mb": 412.1,
  "python_version": "3.11.0",
  "platform": "linux"
}
```

## Accessing Metrics

### CLI Output
```bash
python runner.py script.py --json-output metrics.json
```

### Python API
```python
result = runner.run_script()
metrics = result['metrics']
print(metrics['cpu_max'])
```

### Database Query
```bash
python runner.py --query-metric cpu_max --query-script train.py
```
