# Installation

## Requirements

- Python 3.6 or higher
- psutil (core dependency)
- pyyaml (optional, for YAML configuration)
- requests (optional, for Slack/webhooks/enterprise integrations)

## From Git

```bash
git clone https://github.com/jomardyan/Python-Script-Runner.git
cd Python-Script-Runner
pip install psutil pyyaml requests
```

## Optional Dependencies

```bash
# For Parquet export
pip install pyarrow

# For testing
pip install pytest pytest-cov pytest-mock

# For advanced ML features
pip install scikit-learn
```

## Verification

```bash
python runner.py --help
```

If you see the help output, installation is successful.
