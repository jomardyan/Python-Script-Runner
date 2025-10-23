# OpenTelemetry Integration

## Overview

Python Script Runner v7.0+ includes comprehensive OpenTelemetry (OTEL) support for distributed tracing and observability across script executions. This enables industry-standard monitoring, performance analysis, and debugging of complex workflows.

## Why OpenTelemetry?

- **Industry Standard**: Used by 80%+ of enterprise organizations
- **Multi-Vendor Support**: Works with Jaeger, Zipkin, Datadog, New Relic, etc.
- **Zero Lock-in**: Switch collectors without code changes
- **Performance**: Minimal overhead (<2% CPU impact)
- **Context Propagation**: Automatic trace linking across services

## Installation

```bash
# Install with OpenTelemetry support
pip install 'python-script-runner[otel]'

# Or install all features
pip install 'python-script-runner[all]'
```

## Quick Start

### 1. Configure OTEL Exporter

```bash
# Point to your trace collector
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=my-app
export OTEL_TRACES_EXPORTER=otlp
```

### 2. Enable Tracing in Your Script

```python
from runner import ScriptRunner

runner = ScriptRunner('my_script.py')
runner.enable_tracing = True
result = runner.run_script()

print(f"Trace ID: {result.trace_id}")
```

### 3. View Traces

- **Jaeger**: http://localhost:16686
- **Zipkin**: http://localhost:9411
- **DataDog**: https://app.datadoghq.com/apm
- **New Relic**: https://one.newrelic.com

## Architecture

```
ScriptRunner (root span)
├── extract_metadata (span)
├── validate_dependencies (span)
├── setup_environment (span)
├── execute_script (span)
│   ├── cpu_monitoring (event)
│   ├── memory_monitoring (event)
│   └── io_monitoring (event)
├── collect_metrics (span)
└── upload_traces (span)
```

## Core Concepts

### Spans

A span represents a unit of work (e.g., script execution, function call):

```python
with runner.tracer.trace("custom_operation") as span:
    span.set_attribute("operation.type", "etl")
    span.set_attribute("data.size_mb", 150)
    # Your code here
```

### Events

Record discrete events during span execution:

```python
span.add_event("checkpoint", {
    "progress_percent": 50,
    "items_processed": 1000
})
```

### Context Propagation

Automatically link traces across services:

```python
# Context is automatically propagated via W3C Trace Context headers
# when making HTTP requests
import requests

# The trace context is automatically added to headers
response = requests.get("https://api.example.com/data")
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector endpoint | `http://localhost:4317` |
| `OTEL_SERVICE_NAME` | Service identifier | `my-etl-pipeline` |
| `OTEL_TRACES_EXPORTER` | Exporter type | `otlp` |
| `OTEL_PROPAGATORS` | Context propagation | `tracecontext,baggage` |
| `OTEL_SDK_DISABLED` | Disable tracing | `false` |
| `OTEL_TRACES_SAMPLER` | Sampling strategy | `always_on` |

### Programmatic Configuration

```python
from runner import ScriptRunner, TracingConfig

config = TracingConfig(
    enabled=True,
    exporter_type='jaeger',
    collector_endpoint='http://localhost:6831',
    service_name='my-app',
    sample_rate=1.0,  # Sample 100% of traces
    max_attributes=128,
    max_events=128,
    batch_size=512,
    export_timeout_ms=30000
)

runner = ScriptRunner('script.py')
runner.set_tracing_config(config)
```

## Real-World Examples

### Example 1: ETL Pipeline with Tracing

```python
from runner import ScriptRunner

def main():
    runner = ScriptRunner('etl_pipeline.py')
    runner.enable_tracing = True
    
    # Custom tracing attributes
    runner.tracing_attributes = {
        'pipeline.name': 'daily_etl',
        'environment': 'production',
        'team': 'data-engineering'
    }
    
    result = runner.run_script()
    
    if result.success:
        print(f"✅ Pipeline completed")
        print(f"📊 Trace: {result.trace_id}")
        print(f"⏱️  Duration: {result.metrics['execution_time_seconds']}s")
    else:
        print(f"❌ Pipeline failed: {result.error}")

if __name__ == '__main__':
    main()
```

### Example 2: Distributed Request Tracing

```python
import requests
from runner import ScriptRunner

def fetch_data():
    runner = ScriptRunner('data_fetcher.py')
    runner.enable_tracing = True
    
    with runner.tracer.trace("fetch_batch") as span:
        span.set_attribute("batch.id", "2024-10-23-001")
        
        # Trace context is automatically added to request headers
        response = requests.get("https://api.example.com/data")
        
        span.add_event("data_fetched", {
            "status_code": response.status_code,
            "size_kb": len(response.content) / 1024
        })
    
    return response.json()
```

### Example 3: Multi-Service Workflow

```python
# service1.py
from runner import ScriptRunner

runner = ScriptRunner('service1.py')
runner.enable_tracing = True

# Gets trace context from environment or W3C headers
runner.run_script()

# service2.py (called by service1)
from runner import ScriptRunner

runner = ScriptRunner('service2.py')
runner.enable_tracing = True

# Trace context is automatically inherited
runner.run_script()

# Result: Single trace showing complete flow across both services
```

## Sampling Strategies

### Always On (Development)

```python
import os
os.environ['OTEL_TRACES_SAMPLER'] = 'always_on'
```

Traces all requests. **Not recommended for production** (too much overhead).

### Probability-Based Sampling

```python
os.environ['OTEL_TRACES_SAMPLER'] = 'traceidratio'
os.environ['OTEL_TRACES_SAMPLER_ARG'] = '0.1'  # Sample 10%
```

### Tail-Based Sampling (Recommended)

```python
# Configure in collector
# samples slow/error traces at higher rate, fast traces at lower rate
os.environ['OTEL_TRACES_SAMPLER'] = 'tailbased'
```

## Performance Considerations

### Overhead

- **Span Creation**: ~0.1ms per span
- **Event Recording**: ~0.05ms per event
- **Context Propagation**: <0.01ms
- **Batch Export**: 0-100ms (async, non-blocking)

**Total Impact**: <1% CPU overhead at typical sampling rates.

### Optimization Tips

1. **Use appropriate sample rate**: Don't trace 100% in production
2. **Batch exports**: Automatically batched in 512-item batches
3. **Disable unnecessary events**: Only record relevant events
4. **Local processing**: Traces are batched and exported asynchronously

## Integration with Collectors

### Jaeger (Local Development)

```bash
# Start Jaeger all-in-one
docker run -d --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  jaegertracing/all-in-one:latest

# Configure
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_SERVICE_NAME=my-app
```

### Grafana Loki + Tempo (Recommended for Production)

```yaml
# docker-compose.yml
version: '3'
services:
  tempo:
    image: grafana/tempo:latest
    ports:
      - "4317:4317"
    environment:
      - TEMPO_TRACE_STORAGE_BACKEND=s3

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    datasources:
      - type: tempo
        url: http://tempo:3200
```

### OpenTelemetry Collector (Enterprise)

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:
    send_batch_size: 512
    timeout: 5s
  memory_limiter:
    check_interval: 1s
    limit_mib: 512

exporters:
  jaeger:
    endpoint: jaeger:14250
  datadog:
    api:
      key: ${DD_API_KEY}

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, memory_limiter]
      exporters: [jaeger, datadog]
```

## Troubleshooting

### No Traces Appearing

1. Check OTEL endpoint is running:
   ```bash
   curl http://localhost:4317
   ```

2. Verify environment variables:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   echo $OTEL_SERVICE_NAME
   ```

3. Enable debug logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### High Memory Usage

- **Reduce sample rate**: `OTEL_TRACES_SAMPLER_ARG=0.01` (1%)
- **Reduce batch size**: `OTEL_BSP_MAX_QUEUE_SIZE=1024`
- **Increase export frequency**: `OTEL_BSP_SCHEDULE_DELAY_MILLIS=5000`

### Slow Trace Export

- **Check network**: Ensure collector is reachable
- **Increase timeout**: `OTEL_EXPORTER_OTLP_TIMEOUT=60000`
- **Enable compression**: `OTEL_EXPORTER_OTLP_COMPRESSION=gzip`

## Advanced Topics

### Custom Attributes

```python
runner.tracing_attributes = {
    'deployment.environment': 'production',
    'service.version': '7.0.1',
    'custom.team': 'platform'
}
```

### Span Decorators

```python
from runner import trace_span

@trace_span("expensive_operation")
def process_data(data):
    # Automatically traced
    return data * 2
```

### Instrumentation

```python
from runner import auto_instrument

# Auto-instrument requests, database calls, etc.
auto_instrument('requests', 'mysql', 'redis')
```

## Related Documentation

- [Official OpenTelemetry Docs](https://opentelemetry.io/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Python SDK](https://github.com/open-telemetry/opentelemetry-python)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)

## Support

- Issues: https://github.com/jomardyan/Python-Script-Runner/issues
- Discussions: https://github.com/jomardyan/Python-Script-Runner/discussions
- Documentation: https://python-script-runner.readthedocs.io
