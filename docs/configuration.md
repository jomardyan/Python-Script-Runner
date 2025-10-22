# Configuration

## YAML Configuration File

Create `config.yaml`:

```yaml
alerts:
  - name: cpu_high
    condition: cpu_max > 85
    channels: [slack, email]
    severity: WARNING
    throttle_seconds: 300

  - name: memory_spike
    condition: memory_max_mb > 2048
    channels: [email]
    severity: CRITICAL

performance_gates:
  - metric_name: cpu_max
    max_value: 90
  - metric_name: memory_max_mb
    max_value: 1024

notifications:
  slack:
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
  
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    from: "alerts@company.com"
    to:
      - "team@company.com"
    username: "alerts@company.com"
    password: "${EMAIL_PASSWORD}"
    use_tls: true

retry:
  strategy: exponential
  max_attempts: 3
  initial_delay: 2
  max_delay: 60

database:
  path: "/var/lib/script-runner/metrics.db"
  retention_days: 90
```

## Email Configuration

Create `email_config.json`:

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "from": "alerts@company.com",
  "to": ["team@company.com"],
  "username": "alerts@company.com",
  "password": "your-app-password",
  "use_tls": true
}
```

## Usage

```bash
python runner.py myscript.py --config config.yaml
```

## Security

Use environment variables for sensitive credentials:

```bash
export EMAIL_PASSWORD="your_password"
python runner.py script.py --config config.yaml
```
