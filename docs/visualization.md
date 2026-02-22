# Script Execution Visualization Feature

## Overview

The Python Script Runner now includes a comprehensive visualization feature that displays the complete execution flow and orchestration of script execution in real-time. This feature helps users understand and debug the execution pipeline by showing each stage with clear visual markers and timing.

## Usage

To enable visualization, use the `--visualize` flag:

```bash
python runner.py your_script.py --visualize
```

## What Gets Visualized

The visualization displays the following execution stages:

1. **Validation** - Script path and permissions validation
2. **System Metrics** - Collection of initial system metrics
3. **Pre-Hooks** - Execution of any registered pre-execution hooks
4. **Environment** - Setup of execution environment variables
5. **Process Monitor** - Initialization of the process monitoring system
6. **Subprocess Launch** - Launching the Python subprocess with command and PID
7. **Monitoring** - Real-time process monitoring (CPU, memory, I/O)
8. **Execution** - Script execution progress
9. **Metrics Collection** - Collection of execution metrics (CPU, memory, timing)
10. **Alerts** - Checking and triggering of configured alert rules
11. **History** - Saving metrics to the history database
12. **Post-Hooks** - Execution of any registered post-execution hooks

## Example Output

```
================================================================================
SCRIPT EXECUTION FLOW VISUALIZATION
================================================================================
Script: /path/to/script.py
Attempt: #1
Started: 2026-02-22 20:39:28
================================================================================

[  0.00s] ⏳ Step 1: Validation
           └─ Validating script path and permissions

[  0.00s] ✓ Step 2: Validation
           └─ Script validated successfully

[  0.10s] ⏳ Step 3: System Metrics
           └─ Collecting initial system metrics

[  0.10s] ✓ Step 4: System Metrics
           └─ Initial metrics collected

...

================================================================================
EXECUTION SUCCESS ✓
================================================================================
Total Time: 2.1812s
Exit Code: 0
Steps Completed: 21
Ended: 2026-02-22 20:39:30
================================================================================
```

## Status Symbols

- ⏳ **Running** - Step is currently executing
- ✓ **Done** - Step completed successfully
- ⊘ **Skip** - Step was skipped (e.g., no hooks registered)
- ✗ **Error** - Step failed with an error
- 🚀 **Launch** - Subprocess launch
- 📊 **Monitor** - Real-time monitoring
- 📈 **Metrics** - Metrics summary

## Programmatic Usage

You can also enable visualization programmatically:

```python
from runner import ScriptRunner

runner = ScriptRunner('script.py')
runner.visualizer.enabled = True

result = runner.run_script()
```

## Testing

To test the visualization feature:

```bash
# Run the example test script
python runner.py examples/test_visualization.py --visualize

# Run unit tests
python tests/test_visualization.py
```

## Benefits

1. **Debugging** - See exactly where execution time is spent
2. **Understanding** - Learn how the runner orchestrates script execution
3. **Monitoring** - Watch real-time metrics collection
4. **Transparency** - Full visibility into all execution stages
5. **Troubleshooting** - Quickly identify which stage failed

## Performance

The visualization feature has minimal overhead:
- Only displays output when enabled
- No-op when disabled (default)
- Does not affect metric collection or execution

## Related Features

- Use `--monitor-interval` to adjust monitoring sample rate
- Use `--history-db` to track metrics in database
- Use `--alert-config` to configure alert rules
- Combine with other flags for comprehensive analysis
