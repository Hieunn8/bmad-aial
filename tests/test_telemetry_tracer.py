"""Tests for OpenTelemetry tracing setup."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from aial_shared.telemetry.tracer import setup_tracing


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
