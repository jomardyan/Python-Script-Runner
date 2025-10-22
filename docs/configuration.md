# Configuration Guide

> Complete guide to configuring Python Script Runner

## Configuration File Format

Configuration files can be in YAML or JSON format.

### Basic Structure

```yaml
alerts:
  - name: alert_name
    condition: metric > threshold
    channels: [email, slack]
    severity: WARNING

performance_gates:
  - metric_name: cpu_max
    max_value: 90

notifications:
  email:
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from: alerts@company.com

retry:
  strategy: exponential
  max_attempts: 3
```

## Alert Configuration

```yaml
alerts:
  - name: cpu_high
    condition: cpu_max > 85
    channels: [email, slack]
    severity: WARNING
    enabled: true
```

## Performance Gates

```yaml
performance_gates:
  - metric_name: cpu_max
    max_value: 90
  - metric_name: memory_max_mb
    max_value: 1024
```

## Notifications Configuration

### Email

```yaml
notifications:
  email:
    smtp_server: smtp.gmail.com
    smtp_port: 587
    from: alerts@company.com
    to: team@company.com
    use_tls: true
    username: your_email@gmail.com
    password: your_app_password
```

### Slack

```yaml
notifications:
  slack:
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK
    channel: '#alerts'
    username: PSR Bot
```

## Retry Configuration

```yaml
retry:
  strategy: exponential  # linear, exponential, fibonacci
  max_attempts: 3
  initial_delay: 2       # seconds
  max_delay: 60          # seconds
```

