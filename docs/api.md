# API Documentation

## Python API

### Basic Usage

```python
from runner import ScriptRunner

runner = ScriptRunner(
    script_path='my_script.py',
    script_args=['arg1', 'arg2'],
    timeout=300
)

result = runner.run_script()

metrics = result['metrics']
print(f"CPU Peak: {metrics['cpu_max']:.1f}%")
print(f"Memory Peak: {metrics['memory_max_mb']:.1f} MB")
print(f"Exit Code: {result['returncode']}")
```

### Alerting

```python
from runner import AlertManager

runner.alert_manager.add_alert(
    name='high_cpu',
    condition='cpu_max > 80',
    channels=['slack', 'email'],
    severity='WARNING'
)

runner.alert_manager.configure_slack(
    webhook_url='https://hooks.slack.com/services/...'
)
```

### Performance Gates

```python
from runner import CICDIntegration

runner.cicd_integration.add_performance_gate('cpu_max', max_value=90)
runner.cicd_integration.add_performance_gate('memory_max_mb', max_value=1024)

gates_passed, results = runner.cicd_integration.check_gates(metrics)
```

### History & Analytics

```python
from runner import HistoryManager, TrendAnalyzer

history = HistoryManager('metrics.db')

# Save metrics
history.save_execution('train.py', metrics)

# Get history
executions = history.get_execution_history('train.py', days=30, limit=50)

# Analyze trends
analyzer = TrendAnalyzer(history)
trend = analyzer.detect_trend('execution_time_seconds', days=30)

if trend['is_increasing']:
    print(f"⚠️ Performance degrading: {trend['rate']:.2f}s per day")
```

### Retry Configuration

```python
runner.configure_retry(
    max_attempts=3,
    strategy='exponential',
    initial_delay=2,
    max_delay=60
)
```

### Report Generation

```python
# JUnit XML
runner.cicd_integration.generate_junit_xml(metrics, gates, 'output.xml')

# TAP Format
runner.cicd_integration.generate_tap_output(metrics, gates, 'output.tap')

# JSON
import json
with open('metrics.json', 'w') as f:
    json.dump(metrics, f, indent=2)
```

## Key Classes

- `ScriptRunner` - Main execution engine
- `ProcessMonitor` - Real-time monitoring
- `AlertManager` - Alert configuration
- `HistoryManager` - SQLite persistence
- `TrendAnalyzer` - Statistical analysis
- `CICDIntegration` - CI/CD features
- `AdvancedProfiler` - Profiling utilities
- `EnterpriseIntegrations` - Enterprise features
