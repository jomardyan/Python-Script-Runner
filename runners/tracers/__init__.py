"""
OpenTelemetry Integration Module

Provides comprehensive distributed tracing capabilities with:
- Automatic span creation and context propagation
- Integration with runner execution lifecycle
- Support for Jaeger, Zipkin, and other OTEL exporters
"""

try:
    from runners.tracers.otel_manager import TracingManager
    __all__ = ["TracingManager"]
except ImportError:
    __all__ = []
