# Troubleshooting Guide

> Solutions for common issues and problems

## Installation Issues

### ImportError: No module named 'psutil'

**Problem**: psutil dependency is not installed

**Solution**:
```bash
pip install psutil
```

### ImportError: No module named 'yaml'

**Problem**: PyYAML is not installed

**Solution**:
```bash
pip install pyyaml
# Or use JSON config instead:
python runner.py script.py --json-config config.json
```

## Runtime Issues

### Database Lock Error

**Problem**: `sqlite3.OperationalError: database is locked`

**Causes**:
- Multiple processes accessing database simultaneously
- Corrupted WAL files

**Solutions**:
```bash
# Remove lock files
rm -f script_runner_history.db-wal
rm -f script_runner_history.db-shm

# Or use separate database per process
python runner.py script.py --history-db metrics_$$.db
```

### Memory Usage Growing

**Problem**: Script Runner using too much memory

**Solutions**:
- Disable real-time monitoring if not needed
- Archive old database records
- Use smaller retention period

### Alerts Not Triggering

**Problem**: Alert conditions met but no alerts sent

**Solutions**:
- Check alert configuration syntax
- Verify notification credentials (email, Slack)
- Check network connectivity
- Enable debug logging

## Monitoring Issues

### High CPU Usage

**Problem**: Script Runner using high CPU

**Solutions**:
- Reduce monitoring frequency
- Disable unnecessary features
- Use PyPy for faster execution

### Missing Metrics

**Problem**: Some metrics not collected

**Solutions**:
- Check script execution time (need minimum time for sampling)
- Verify monitoring is enabled
- Check for process termination

## Performance Issues

### Slow Query Performance

**Problem**: Database queries are slow

**Solutions**:
```bash
# Archive old data
python runner.py --archive-db metrics.db --days 90

# Vacuum database
sqlite3 metrics.db "VACUUM;"
```

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from runner import ScriptRunner
runner = ScriptRunner('script.py')
result = runner.execute()
```

### Check Database

```bash
# List tables
sqlite3 metrics.db ".tables"

# Check recent executions
sqlite3 metrics.db "SELECT * FROM executions LIMIT 5;"
```

