# Troubleshooting

## Installation Issues

### ImportError: No module named 'psutil'

```bash
pip install psutil
```

### YAML configuration not loading

```bash
pip install pyyaml
# Or use JSON format instead
```

### Slack/webhook notifications not working

1. Verify webhook URL is correct
2. Check network connectivity:
   ```bash
   curl -X POST <webhook_url>
   ```
3. Enable debug logging:
   ```bash
   python runner.py script.py --log-level DEBUG
   ```

## Runtime Issues

### Database file locked

Ensure no other processes are using the database:

```bash
# Check for open database files
lsof -i :8000  # if dashboard is running

# Close dashboard if needed
kill $(lsof -t -i :8000)
```

### Performance gates always failing

1. Verify metric names match JSON output:
   ```bash
   python runner.py script.py --json-output metrics.json
   ```
2. Check baseline file format is valid JSON
3. Use `--metrics-list` to see available metrics

### High memory usage

Reduce sampling interval or archive old data:

```bash
python runner.py script.py --monitor-interval 1.0

# Archive and cleanup old records
python runner.py --cleanup-old 30 --archive-path ./archive
```

### SSH execution failing

Check connectivity and permissions:

```bash
# Test SSH connection
ssh -i ~/.ssh/key user@host "python --version"

# Ensure runner.py is on remote system
```

## Debug Mode

Enable detailed logging:

```bash
python runner.py script.py \
    --log-level DEBUG \
    --suppress-warnings false
```

## Getting Help

1. Check documentation
2. Review error logs with `--log-level DEBUG`
3. Create GitHub issue with:
   - Configuration file (redacted)
   - Error logs
   - Minimal reproduction case
