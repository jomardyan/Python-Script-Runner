# v7.0 Migration Guide

## Overview

Python Script Runner v7.0 introduces major new features while maintaining 100% backward compatibility with v6.x. This guide helps you upgrade and adopt new capabilities.

## Key Changes

### New in v7.0

✨ **Observability Features**
- OpenTelemetry integration for distributed tracing
- Enhanced metrics collection and analytics
- Real-time monitoring dashboard updates

🔒 **Security & Compliance**
- Static code analysis (Bandit + Semgrep)
- Dependency vulnerability scanning
- Secret detection and vault integration
- SOC2, HIPAA, PCI-DSS compliance support

💰 **Cost Management**
- Cloud cost attribution (AWS, Azure, GCP)
- Cost reporting and analytics
- Budget monitoring and optimization

🔄 **Workflow Orchestration**
- DAG-based workflow engine
- Complex dependency management
- Parallel execution and matrix operations
- Conditional branching

📦 **Templates & Scaffolding**
- Pre-built templates (ETL, API, file processing, etc.)
- CLI-based code generation
- Best practices baked in

🚀 **CI/CD Integration**
- GitHub Actions support
- GitLab CI/CD templates
- Zero-config setup

### Backward Compatibility

✅ All v6.x code continues to work without changes
✅ Core `ScriptRunner` API unchanged
✅ Configuration format compatible
✅ Database schema migrations automatic

## Installation

### Upgrade from v6.x

```bash
# Upgrade to v7.0
pip install --upgrade python-script-runner

# Or install with all features
pip install 'python-script-runner[all]'
```

### Feature-Based Installation

```bash
# Choose only the features you need
pip install python-script-runner                    # Core only
pip install 'python-script-runner[dashboard]'      # Web UI
pip install 'python-script-runner[otel]'           # Tracing
pip install 'python-script-runner[security]'       # Security scanning
pip install 'python-script-runner[cloud]'          # Cost tracking
pip install 'python-script-runner[all]'            # Everything
```

## Migration Steps

### Step 1: Update Version (Optional)

Your code will work as-is. Optionally, update to use new features:

**Before (v6.x):**
```python
from runner import ScriptRunner

runner = ScriptRunner('script.py')
result = runner.run_script()
```

**After (v7.0 - still compatible):**
```python
from runner import ScriptRunner

runner = ScriptRunner('script.py')
result = runner.run_script()
# No changes needed!
```

### Step 2: Adopt New Features Incrementally

**Enable Tracing:**
```python
runner.enable_tracing = True
```

**Enable Security Scanning:**
```python
runner.enable_security_scan = True
runner.enable_dependency_scan = True
```

**Enable Cost Tracking:**
```python
runner.enable_cost_tracking = True
```

### Step 3: Update CI/CD

**GitHub Actions:**

```yaml
# Old way (still works)
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
- run: pip install python-script-runner
- run: python-script-runner script.py

# New way (recommended)
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './script.py'
    enable-tracing: true
    enable-security-scan: true
```

**GitLab CI:**

```yaml
# Old way (still works)
image: python:3.11
script:
  - pip install python-script-runner
  - python-script-runner script.py

# New way (recommended)
my_job:
  extends: .psr_script_runner_secure
  variables:
    SCRIPT_PATH: ./script.py
```

### Step 4: Use Templates (Optional)

Generate new scripts from templates:

```bash
python-script-runner --template etl_pipeline --output my_etl.py
python-script-runner --template api_integration --output my_api.py
python-script-runner --template file_processing --output my_processor.py
python-script-runner --template data_transformation --output my_transform.py
```

### Step 5: Adopt Workflows (For Complex Pipelines)

Define multi-step pipelines:

```yaml
# workflow.yaml
name: My Pipeline
tasks:
  step1:
    script: ./scripts/step1.py
  step2:
    script: ./scripts/step2.py
    depends_on: [step1]
```

Execute:
```python
from runner.workflows import WorkflowEngine, WorkflowParser

engine = WorkflowEngine()
result = engine.run(WorkflowParser().parse_yaml('workflow.yaml'))
```

## Breaking Changes

⚠️ **NONE** - v7.0 is 100% backward compatible with v6.x

All existing code, scripts, and configurations continue to work without modification.

## Configuration Updates

### New Environment Variables

```bash
# Tracing
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=my-app

# Security
export PSR_SECURITY_SCAN_ENABLED=true
export PSR_BLOCK_ON_CRITICAL=true

# Cost tracking
export PSR_COST_TRACKING_ENABLED=true
export AWS_REGION=us-east-1

# Workflows
export PSR_WORKFLOW_MAX_PARALLELISM=8
```

### Updated config.example.yaml

```yaml
# v7.0 additions (optional)
observability:
  tracing:
    enabled: false
    exporter: otlp
    sample_rate: 1.0

security:
  enabled: false
  scanners:
    - bandit
    - semgrep
  block_on_severity: high

cost_tracking:
  enabled: false
  provider: aws  # or azure, gcp
  
workflows:
  max_parallelism: 8
  timeout_minutes: 60
```

## Database Migration

SQLite schemas are automatically migrated:

```bash
# Automatic on first run of v7.0
python-script-runner script.py

# Check migration status
python-script-runner --check-db-version
```

If you have a large database, consider backing up first:

```bash
cp metrics.db metrics.db.backup
python-script-runner script.py  # Triggers migration
```

## Deprecations

None in v7.0. All v6.x features remain supported.

## Performance

v7.0 has similar or better performance to v6.x:

| Feature | Overhead |
|---------|----------|
| None (base) | 0% |
| Tracing | <1% |
| Security scanning | 2-5% (pre-execution) |
| Dependency scanning | 1-3% (pre-execution) |
| Cost tracking | <0.5% |
| Workflows | <1% |

## Troubleshooting

### ImportError: No module named 'runners'

```bash
# Upgrade package
pip install --upgrade python-script-runner

# Or install with all features
pip install 'python-script-runner[all]'
```

### OpenTelemetry not working

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Should see debug output about OTEL initialization
```

### Security scan errors

```bash
# Install optional scanners
pip install 'python-script-runner[security]'

# Verify bandit is installed
bandit --version

# Verify semgrep is installed
semgrep --version
```

### Cost tracking shows $0

1. Ensure AWS/Azure/GCP credentials are configured
2. Resources must actually be running during script execution
3. Allow 24 hours for billing data to propagate
4. Check IAM permissions for cost/billing APIs

## Support

### Documentation

- **Main docs**: https://github.com/jomardyan/Python-Script-Runner
- **API reference**: /docs/api.md
- **Examples**: /examples/
- **Feature guides**: /docs/features/

### Getting Help

- **Issues**: https://github.com/jomardyan/Python-Script-Runner/issues
- **Discussions**: https://github.com/jomardyan/Python-Script-Runner/discussions
- **Changelog**: CHANGELOG.md

## Next Steps

1. **Upgrade**: `pip install --upgrade python-script-runner`
2. **Try one feature**: Enable tracing or security scanning
3. **Test in dev**: Verify your scripts still work
4. **Adopt incrementally**: Turn on features as needed
5. **Join community**: Share feedback and use cases

## Checklists

### For All Users

- [ ] Upgrade to v7.0
- [ ] Verify existing scripts still work
- [ ] Read features documentation
- [ ] Enable one new feature (recommended: tracing)
- [ ] Test in dev/staging environment

### For CI/CD Users

- [ ] Update GitHub Actions or GitLab CI config
- [ ] Enable security scanning in pipeline
- [ ] Add cost tracking (if using AWS/Azure/GCP)
- [ ] Test workflows in dev branch

### For Production Users

- [ ] Backup database: `cp metrics.db metrics.db.backup`
- [ ] Test in staging environment first
- [ ] Plan migration for non-business hours
- [ ] Monitor logs during first production runs
- [ ] Enable monitoring/alerting for new features

## Questions?

Check the **[FAQ](../faq.md)** or open an **[issue](https://github.com/jomardyan/Python-Script-Runner/issues)**.
