"""AIAL Orchestration Service — FastAPI application entry point."""

from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI

from aial_shared.auth.fastapi_deps import require_permission
from aial_shared.telemetry.tracer import setup_tracing

from orchestration.routes.health import router as health_router

logger = logging.getLogger(__name__)

setup_tracing(
    "orchestration",
    otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
)

chat_query_auth = require_permission("api:chat", "default", "query")


def create_app() -> FastAPI:
    app = FastAPI(title="AIAL Orchestration", version="0.1.0")

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

    app.include_router(health_router)

    @app.post(
        "/v1/chat/query",
        dependencies=[Depends(chat_query_auth)],
    )
    async def chat_query() -> dict[str, str]:
        return {"answer": "stub", "status": "ok"}

    return app


app = create_app()
