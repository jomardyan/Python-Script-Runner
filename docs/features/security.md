# Security & Compliance Features

## Overview

Python Script Runner v7.0+ includes comprehensive security features for detecting vulnerabilities, managing secrets, and ensuring compliance with security best practices.

## Features

### 1. Static Code Analysis

Automatically scan Python scripts for security vulnerabilities and code quality issues before execution.

#### Installation

```bash
pip install 'python-script-runner[security]'
```

#### Supported Scanners

- **Bandit**: Security issue detection in Python code
- **Semgrep**: Advanced pattern-based static analysis
- **Ruff**: Fast Python linter with security rules

#### Quick Start

```python
from runner import ScriptRunner

runner = ScriptRunner('my_script.py')
runner.enable_security_scan = True

result = runner.run_script()
print(result.security_findings)  # List of issues found
```

#### Configuration

```python
from runner import SecurityConfig

config = SecurityConfig(
    enabled=True,
    scanners=['bandit', 'semgrep'],
    block_on_severity='high',  # Block execution on HIGH/CRITICAL
    report_format='sarif',  # SARIF format for integration with tools
    exclude_patterns=['tests/*', '**/.venv/*']
)

runner = ScriptRunner('script.py')
runner.security_config = config
```

### 2. Dependency Vulnerability Scanning

Detect known vulnerabilities in Python dependencies before execution.

#### Supported Tools

- **Safety CLI**: Checks against known CVE database
- **OSV-Scanner**: Google's OSV database for dependencies
- **Pip-audit**: Automatically from PyPI

#### Example

```python
from runner import ScriptRunner

runner = ScriptRunner('script.py')
runner.enable_dependency_scan = True

result = runner.run_script()

if result.vulnerable_dependencies:
    print("⚠️ Vulnerable dependencies found:")
    for vuln in result.vulnerable_dependencies:
        print(f"  {vuln.package}: {vuln.cve_id} ({vuln.severity})")
```

#### SBOM Generation

Automatically generate Software Bill of Materials:

```python
runner.enable_sbom_generation = True
result = runner.run_script()

# SBOM saved to: results/sbom-{timestamp}.json
# Format: CycloneDX 1.4
```

### 3. Secret Scanning

Detect hardcoded secrets and passwords in scripts before execution.

#### Detection Methods

- **Pattern Matching**: AWS keys, API tokens, private keys
- **Entropy Analysis**: High-entropy strings likely to be secrets
- **Dictionary**: Known secret patterns

#### Usage

```python
from runner import ScriptRunner

runner = ScriptRunner('script.py')
runner.enable_secret_scan = True

result = runner.run_script()

if result.secrets_found:
    print("🔐 Potential secrets detected:")
    for secret in result.secrets_found:
        print(f"  Line {secret.line_number}: {secret.pattern_type}")
```

### 4. Vault Integration

Manage secrets securely with AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault.

#### AWS Secrets Manager

```python
from runner import SecretManagerAdapter

adapter = SecretManagerAdapter('aws')
secret = adapter.get_secret('my-database-password')

# Inject into script environment
runner = ScriptRunner('script.py')
runner.secrets = {'DB_PASSWORD': secret}
result = runner.run_script()
```

#### HashiCorp Vault

```python
adapter = SecretManagerAdapter('vault')
adapter.configure(
    vault_addr='https://vault.example.com:8200',
    vault_token='s.xxxxxxxx'
)

secret = adapter.get_secret('secret/data/prod/db-password')
```

#### Azure Key Vault

```python
adapter = SecretManagerAdapter('azure')
adapter.configure(
    vault_name='my-vault',
    credential_type='managed_identity'  # or 'service_principal'
)

secret = adapter.get_secret('db-password')
```

## Real-World Example

```python
from runner import ScriptRunner, SecurityConfig, SecretManagerAdapter

# Configure security
security_config = SecurityConfig(
    enabled=True,
    scanners=['bandit', 'semgrep'],
    block_on_severity='high',
    exclude_patterns=['tests/*']
)

# Setup vault integration
vault_adapter = SecretManagerAdapter('aws')
database_password = vault_adapter.get_secret('prod/db-password')
api_key = vault_adapter.get_secret('prod/api-key')

# Execute with security checks
runner = ScriptRunner('etl_pipeline.py')
runner.security_config = security_config
runner.enable_secret_scan = True
runner.secrets = {
    'DB_PASSWORD': database_password,
    'API_KEY': api_key
}

result = runner.run_script()

print(f"✅ Security checks: {result.security_findings}")
print(f"✅ Script exit code: {result.exit_code}")
```

## CI/CD Integration

### GitHub Actions

```yaml
- uses: jomardyan/python-script-runner@v1
  with:
    script-path: './scripts/critical_script.py'
    enable-security-scan: true
    enable-dependency-scan: true
    fail-fast: true
```

### GitLab CI

```yaml
secure_script:
  extends: .psr_script_runner_secure
  variables:
    SCRIPT_PATH: ./scripts/critical_script.py
  only:
    - main
    - tags
```

## Compliance Frameworks

### SOC 2

- ✅ Secret vault integration with audit logs
- ✅ Dependency vulnerability scanning
- ✅ Code security scanning (static analysis)
- ✅ Execution tracing with OpenTelemetry

### HIPAA

- ✅ Encrypted secret storage (Vault support)
- ✅ Comprehensive audit trails
- ✅ Access control via CI/CD environment

### PCI DSS

- ✅ No hardcoded secrets (detection blocks execution)
- ✅ Dependency vulnerability scanning
- ✅ Security scanning for OWASP Top 10

### ISO 27001

- ✅ Information security controls
- ✅ Access control and authentication
- ✅ Audit and accountability

## Best Practices

1. **Always enable security scanning in CI/CD**: Catches issues before production
2. **Use vault for secrets**: Never commit credentials
3. **Regular dependency updates**: Keep scanner databases fresh
4. **Review scan findings**: Address HIGH/CRITICAL issues immediately
5. **Automate compliance checks**: Integrate with your CI/CD pipeline

## Troubleshooting

### Bandit Not Found

```bash
pip install bandit>=1.7.5
```

### Semgrep Errors

```bash
# Update rules
semgrep --update

# Test with sample config
semgrep --config=p/security-audit script.py
```

### Vault Connection Issues

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

adapter = SecretManagerAdapter('vault')
# Errors will now show detailed connection info
```

## Related Documentation

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Semgrep Documentation](https://semgrep.dev/)
- [Safety CLI Documentation](https://safety.readthedocs.io/)
- [HashiCorp Vault](https://www.vaultproject.io/)
