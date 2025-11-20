"""Unit tests for OpenTelemetry Integration."""

import pytest
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from runners.tracers.otel_manager import (
        TracingManager, ExporterType, PropagatorType, ExporterConfig, SamplingConfig, OTEL_AVAILABLE as _OTEL_AVAILABLE
    )
    OTEL_AVAILABLE = bool(_OTEL_AVAILABLE)
except ImportError:
    OTEL_AVAILABLE = False


@pytest.mark.skipif(not OTEL_AVAILABLE, reason="OpenTelemetry not installed")
class TestTracingManagerInitialization:
    """Test TracingManager initialization."""
    
    def test_init_without_otel(self):
        """Test initialization when OTEL is not available."""
        manager = TracingManager(exporter_type='NONE')
        assert manager is not None
    
    def test_exporter_config_from_env(self, monkeypatch):
        """Test creating ExporterConfig from environment variables."""
        monkeypatch.setenv('OTEL_EXPORTER', 'JAEGER')
        monkeypatch.setenv('OTEL_JAEGER_HOST', 'localhost')
        monkeypatch.setenv('OTEL_JAEGER_PORT', '6831')
        
        config = ExporterConfig.from_env()
        assert config.type == 'JAEGER'
    
    def test_sampling_config_from_env(self, monkeypatch):
        """Test creating SamplingConfig from environment variables."""
        monkeypatch.setenv('OTEL_SAMPLING_STRATEGY', 'probability')
        monkeypatch.setenv('OTEL_SAMPLING_PROBABILITY', '0.5')
        
        config = SamplingConfig.from_env()
        assert config.strategy == 'probability'


@pytest.mark.skipif(not OTEL_AVAILABLE, reason="OpenTelemetry not installed")
class TestSpanOperations:
    """Test span creation and management."""
    
    def test_create_span_context_manager(self):
        """Test span creation with context manager."""
        manager = TracingManager(exporter_type='NONE')
        
        # This should not raise an error
        with manager.create_span('test_span') as span:
            assert span is not None
    
    def test_create_nested_spans(self):
        """Test creating nested spans."""
        manager = TracingManager(exporter_type='NONE')
        
        with manager.create_span('parent') as parent_span:
            with manager.create_span('child') as child_span:
                assert child_span is not None
    
    def test_set_span_status(self):
        """Test setting span status."""
        manager = TracingManager(exporter_type='NONE')
        
        with manager.create_span('test') as span:
            manager.set_span_status('OK')
            # Should not raise


@pytest.mark.skipif(not OTEL_AVAILABLE, reason="OpenTelemetry not installed")
class TestSampling:
    """Test sampling strategies."""
    
    def test_always_on_sampler(self):
        """Test always-on sampling strategy."""
        config = SamplingConfig(strategy='always_on')
        manager = TracingManager(
            exporter_type='NONE',
            sampling_config=config
        )
        assert manager is not None
    
    def test_always_off_sampler(self):
        """Test always-off sampling strategy."""
        config = SamplingConfig(strategy='always_off')
        manager = TracingManager(
            exporter_type='NONE',
            sampling_config=config
        )
        assert manager is not None
    
    def test_probability_sampler(self):
        """Test probability-based sampling."""
        config = SamplingConfig(
            strategy='probability',
            probability=0.5
        )
        manager = TracingManager(
            exporter_type='NONE',
            sampling_config=config
        )
        assert manager is not None


class TestTracingManagerCleanup:
    """Test tracing manager cleanup."""
    
    def test_shutdown(self):
        """Test shutting down tracing manager."""
        manager = TracingManager(exporter_type='NONE')
        # Should not raise
        manager.shutdown()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
