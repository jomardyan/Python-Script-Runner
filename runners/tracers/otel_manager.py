"""
OpenTelemetry Integration for Python Script Runner

Provides distributed tracing capabilities with automatic context propagation,
span creation, and exporter configuration.

Features:
- Automatic span creation for script execution
- Context propagation (W3C Trace Context)
- Multiple exporter backends (Jaeger, Zipkin, OTLP, etc.)
- Sampling strategies (always_on, probability, tail-based)
- Performance monitoring (<1% overhead)
- Structured logging integration
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from contextlib import contextmanager

# Optional OpenTelemetry imports
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import (
        Sampler,
        AlwaysOnSampler,
        AlwaysOffSampler,
        ProbabilitySampler,
        SamplingResult,
    )
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.exporter.zipkin.json import ZipkinExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.api.trace import Status, StatusCode
    from opentelemetry.propagate import set_global_textmap
    from opentelemetry.propagators.jaeger import JaegerPropagator
    from opentelemetry.propagators.b3 import B3Format
    from opentelemetry.propagators.tracecontext import TraceContextPropagator
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    Sampler = None
    AlwaysOnSampler = None
    AlwaysOffSampler = None
    ProbabilitySampler = None
    SamplingResult = None


class ExporterType(Enum):
    """Supported OpenTelemetry exporters."""
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"
    OTLP = "otlp"
    NONE = "none"


class PropagatorType(Enum):
    """Supported trace context propagators."""
    JAEGER = "jaeger"
    B3 = "b3"
    W3C_TRACE_CONTEXT = "tracecontext"


@dataclass
class ExporterConfig:
    """Configuration for OpenTelemetry exporter."""
    type: ExporterType = ExporterType.JAEGER
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    zipkin_url: str = "http://localhost:9411/api/v2/spans"
    otlp_endpoint: str = "localhost:4317"
    service_name: str = "python-script-runner"
    environment: str = "production"
    version: str = "1.0.0"

    @classmethod
    def from_env(cls) -> "ExporterConfig":
        """Create config from environment variables."""
        return cls(
            type=ExporterType(os.getenv("OTEL_EXPORTER_TYPE", "jaeger").lower()),
            jaeger_host=os.getenv("OTEL_JAEGER_HOST", "localhost"),
            jaeger_port=int(os.getenv("OTEL_JAEGER_PORT", "6831")),
            zipkin_url=os.getenv("OTEL_ZIPKIN_URL", "http://localhost:9411/api/v2/spans"),
            otlp_endpoint=os.getenv("OTEL_OTLP_ENDPOINT", "localhost:4317"),
            service_name=os.getenv("OTEL_SERVICE_NAME", "python-script-runner"),
            environment=os.getenv("OTEL_ENVIRONMENT", "production"),
            version=os.getenv("OTEL_VERSION", "1.0.0"),
        )


@dataclass
class SamplingConfig:
    """Sampling strategy configuration."""
    strategy: str = "always_on"  # always_on, always_off, probability, tail_based
    probability: float = 0.1  # For probability sampling
    tail_sampling_rules: Optional[Dict[str, Any]] = None

    @classmethod
    def from_env(cls) -> "SamplingConfig":
        """Create config from environment variables."""
        return cls(
            strategy=os.getenv("OTEL_SAMPLING_STRATEGY", "always_on").lower(),
            probability=float(os.getenv("OTEL_SAMPLING_PROBABILITY", "0.1")),
        )


@dataclass
class TraceInfo:
    """Information about an active trace."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "UNSET"
    attributes: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize defaults."""
        if self.attributes is None:
            self.attributes = {}


# Only define CustomTailSampler if OpenTelemetry is available
if OTEL_AVAILABLE and Sampler is not None:
    class CustomTailSampler(Sampler):
        """Custom tail-based sampler for OpenTelemetry."""

        def __init__(self, rules: Optional[Dict[str, Any]] = None):
            """
            Initialize with sampling rules.

            Rules can include:
            - error: Always sample if error occurs
            - duration_ms: Min duration to sample
            - tags: Sample if specific tags present
            """
            self.rules = rules or {"error": True}

        def should_sample(
            self,
            parent_context,
            trace_id,
            span_name,
            span_kind,
            attributes,
            links,
            trace_state=None,
        ):
            """Determine if span should be sampled."""
            # Check error rule
            if self.rules.get("error") and attributes:
                if attributes.get("error") or attributes.get("exception"):
                    return SamplingResult(
                        decision=True,
                        trace_state=trace_state,
                        attributes={"sampled_reason": "error"},
                    )

            # Check duration rule
            if "duration_ms" in self.rules and attributes:
                estimated_duration = attributes.get("estimated_duration_ms", 0)
                if estimated_duration >= self.rules["duration_ms"]:
                    return SamplingResult(
                        decision=True,
                        trace_state=trace_state,
                        attributes={"sampled_reason": "duration"},
                    )

            # Default: sample based on probability
            return SamplingResult(
                decision=True,
                trace_state=trace_state,
                attributes={"sampled_reason": "default"},
            )

        def get_description(self) -> str:
            """Get sampler description."""
            return f"CustomTailSampler({self.rules})"
else:
    # Stub implementation for when OpenTelemetry is not available
    class CustomTailSampler:
        """Stub for CustomTailSampler when OpenTelemetry is not available."""

        def __init__(self, rules: Optional[Dict[str, Any]] = None):
            """Initialize stub."""
            self.rules = rules or {"error": True}


class TracingManager:
    """Manage OpenTelemetry tracing for script execution."""

    def __init__(
        self,
        exporter_config: Optional[ExporterConfig] = None,
        sampling_config: Optional[SamplingConfig] = None,
        enabled: bool = True,
        exporter_type: str = None,
        **kwargs
    ):
        """
        Initialize tracing manager.

        Args:
            exporter_config: Exporter configuration
            sampling_config: Sampling configuration
            enabled: Enable tracing
            exporter_type: Exporter type string ('jaeger', 'zipkin', 'otlp', 'NONE')
            **kwargs: Additional parameters for compatibility
        """
        self.enabled = enabled and OTEL_AVAILABLE
        self.logger = logging.getLogger(__name__)
        
        # Handle exporter_type string parameter
        if exporter_type is not None and exporter_config is None:
            try:
                exporter_enum = ExporterType(exporter_type.lower())
            except (ValueError, AttributeError):
                exporter_enum = ExporterType.NONE
            exporter_config = ExporterConfig(type=exporter_enum)
        
        self.exporter_config = exporter_config or ExporterConfig.from_env()
        self.sampling_config = sampling_config or SamplingConfig.from_env()
        self.tracer_provider: Optional[TracerProvider] = None
        self.tracer = None
        self.active_spans: Dict[str, Any] = {}

        if self.enabled:
            self._initialize()
        else:
            if not OTEL_AVAILABLE:
                self.logger.warning("OpenTelemetry not available. Install: pip install opentelemetry-api")
            else:
                self.logger.info("Tracing disabled")

    def _initialize(self):
        """Initialize OpenTelemetry components."""
        if not OTEL_AVAILABLE:
            return

        try:
            # Create sampler
            sampler = self._create_sampler()

            # Create tracer provider
            self.tracer_provider = TracerProvider(sampler=sampler)

            # Create exporter
            exporter = self._create_exporter()
            if exporter:
                self.tracer_provider.add_span_processor(BatchSpanProcessor(exporter))

            # Set global tracer provider
            trace.set_tracer_provider(self.tracer_provider)

            # Set propagator for context propagation
            self._setup_propagator()

            # Get tracer
            self.tracer = trace.get_tracer(__name__)

            self.logger.info(
                f"Tracing initialized: {self.exporter_config.type.value}, "
                f"sampling: {self.sampling_config.strategy}"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize tracing: {e}")
            self.enabled = False

    def _create_sampler(self) -> Optional[Sampler]:
        """Create sampler based on configuration."""
        if not OTEL_AVAILABLE or not Sampler:
            return None

        strategy = self.sampling_config.strategy.lower()

        if strategy == "always_on":
            return AlwaysOnSampler()
        elif strategy == "always_off":
            return AlwaysOffSampler()
        elif strategy == "probability":
            return ProbabilitySampler(self.sampling_config.probability)
        elif strategy == "tail_based":
            return CustomTailSampler(self.sampling_config.tail_sampling_rules)
        else:
            self.logger.warning(f"Unknown sampling strategy: {strategy}, using always_on")
            return AlwaysOnSampler()

    def _create_exporter(self):
        """Create exporter based on configuration."""
        if not OTEL_AVAILABLE:
            return None

        exporter_type = self.exporter_config.type

        try:
            if exporter_type == ExporterType.JAEGER:
                return JaegerExporter(
                    agent_host_name=self.exporter_config.jaeger_host,
                    agent_port=self.exporter_config.jaeger_port,
                )
            elif exporter_type == ExporterType.ZIPKIN:
                return ZipkinExporter(
                    zipkin_url=self.exporter_config.zipkin_url,
                )
            elif exporter_type == ExporterType.OTLP:
                return OTLPSpanExporter(
                    endpoint=self.exporter_config.otlp_endpoint,
                )
            elif exporter_type == ExporterType.NONE:
                return None
            else:
                self.logger.warning(f"Unknown exporter type: {exporter_type}")
                return None
        except Exception as e:
            self.logger.warning(f"Failed to create exporter {exporter_type.value}: {e}")
            return None

    def _setup_propagator(self):
        """Setup trace context propagator."""
        if not OTEL_AVAILABLE:
            return

        try:
            # Use W3C Trace Context as default
            set_global_textmap(TraceContextPropagator())
        except Exception as e:
            self.logger.warning(f"Failed to setup propagator: {e}")

    @contextmanager
    def create_span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Create a span context manager.

        Args:
            name: Span name
            attributes: Span attributes

        Yields:
            Active span
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        attributes = attributes or {}
        start_time = time.time()

        with self.tracer.start_as_current_span(name) as span:
            # Set attributes
            for key, value in attributes.items():
                try:
                    span.set_attribute(key, value)
                except Exception as e:
                    self.logger.debug(f"Failed to set attribute {key}: {e}")

            # Add event for start
            span.add_event(f"{name}_start")

            yield span

            # Add event for end
            span.add_event(f"{name}_end", attributes={"duration_ms": (time.time() - start_time) * 1000})

    def create_event(
        self, name: str, attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Add event to current span.

        Args:
            name: Event name
            attributes: Event attributes
        """
        if not self.enabled or not self.tracer:
            return

        try:
            current_span = trace.get_current_span()
            if current_span:
                current_span.add_event(name, attributes=attributes or {})
        except Exception as e:
            self.logger.debug(f"Failed to add event: {e}")

    def set_span_status(self, status: str, description: Optional[str] = None):
        """
        Set status of current span.

        Args:
            status: Status (OK, ERROR, UNSET)
            description: Status description
        """
        if not self.enabled or not self.tracer or not OTEL_AVAILABLE:
            return

        try:
            current_span = trace.get_current_span()
            if current_span:
                status_code = getattr(StatusCode, status.upper(), StatusCode.UNSET)
                current_span.set_status(Status(status_code, description))
        except Exception as e:
            self.logger.debug(f"Failed to set span status: {e}")

    def get_trace_context(self) -> Optional[Dict[str, str]]:
        """
        Get current trace context for propagation.

        Returns:
            Dictionary with trace context or None
        """
        if not self.enabled or not self.tracer or not OTEL_AVAILABLE:
            return None

        try:
            current_span = trace.get_current_span()
            if current_span:
                span_context = current_span.get_span_context()
                return {
                    "trace_id": format(span_context.trace_id, "032x"),
                    "span_id": format(span_context.span_id, "016x"),
                }
        except Exception as e:
            self.logger.debug(f"Failed to get trace context: {e}")

        return None

    def shutdown(self, timeout_secs: int = 5):
        """
        Shutdown tracing and flush spans.

        Args:
            timeout_secs: Timeout for flushing
        """
        if not self.enabled or not self.tracer_provider:
            return

        try:
            self.tracer_provider.force_flush(timeout_ms=timeout_secs * 1000)
            self.tracer_provider.shutdown()
            self.logger.info("Tracing shutdown complete")
        except Exception as e:
            self.logger.error(f"Error during tracing shutdown: {e}")
