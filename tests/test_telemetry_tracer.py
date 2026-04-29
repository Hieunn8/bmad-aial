"""Tests for OpenTelemetry tracing setup."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from aial_shared.telemetry.tracer import _DEFAULT_OTLP_ENDPOINT, setup_tracing


class TestSetupTracing:
    def test_returns_tracer_provider(self) -> None:
        provider = setup_tracing("test-service")
        assert isinstance(provider, TracerProvider)

    def test_sets_service_name_resource(self) -> None:
        provider = setup_tracing("my-service")
        resource = provider.resource
        attrs = dict(resource.attributes)
        assert attrs["service.name"] == "my-service"

    def test_global_provider_is_sdk_provider(self) -> None:
        setup_tracing("global-test")
        current = trace.get_tracer_provider()
        assert isinstance(current, TracerProvider)

    def test_tracer_creates_spans(self) -> None:
        provider = setup_tracing("span-test")
        tracer = provider.get_tracer("test")
        with tracer.start_as_current_span("test-span") as span:
            assert span is not None
            assert span.is_recording()
            ctx = span.get_span_context()
            assert ctx.trace_id != 0

    def test_default_otlp_endpoint(self) -> None:
        assert _DEFAULT_OTLP_ENDPOINT == "http://localhost:4317"

    def test_otlp_exporter_always_attached(self) -> None:
        provider = setup_tracing("otlp-test")
        processors = provider._active_span_processor._span_processors
        batch_processors = [p for p in processors if isinstance(p, BatchSpanProcessor)]
        assert len(batch_processors) >= 1
