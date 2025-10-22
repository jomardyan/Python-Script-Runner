# Quick Start

Get up and running in 5 minutes!

## Installation

```bash
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner
pip install -r requirements.txt
```

## Your First Script

Create `test_app.py`:

```python
import time
print('Starting...')
for i in range(5):
    print(f'Step {i+1}')
    time.sleep(0.5)
print('Done!')
```

Run with monitoring:

```bash
python runner.py test_app.py
```

## Common Use Cases

### CI/CD with Performance Gates

```bash
python runner.py tests/suite.py \\
    --add-gate cpu_max:90 \\
    --add-gate memory_max_mb:1024 \\
    --junit-output results.xml
```

### Track Performance Over Time

```bash
python runner.py script.py \\
    --history-db metrics.db \\
    --detect-anomalies \\
    --analyze-trend
```

### Slack Alerts

```bash
python runner.py script.py \\
    --slack-webhook 'https://hooks.slack.com/services/YOUR/WEBHOOK'
```

## Next Steps

- 📖 [Installation](installation.md)
- 📚 [Usage Guide](usage.md)
- 🔧 [CLI Reference](cli-reference.md)
- ⚙️ [Configuration](configuration.md)
