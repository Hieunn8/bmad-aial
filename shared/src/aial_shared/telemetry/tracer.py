"""OpenTelemetry tracing setup for AIAL services.

Every service must call setup_tracing(service_name) as the first line
in its main() before creating the FastAPI app or any other instrumented code.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


_DEFAULT_OTLP_ENDPOINT = "http://localhost:4317"


def setup_tracing(
    service_name: str,
    *,
    otlp_endpoint: str | None = None,
    console_export: bool = False,
) -> TracerProvider:
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = otlp_endpoint or _DEFAULT_OTLP_ENDPOINT
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    if console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    return provider
