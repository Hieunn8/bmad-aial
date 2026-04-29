"""AIAL Orchestration Service — FastAPI application entry point."""

from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from aial_shared.auth.fastapi_deps import require_permission
from aial_shared.telemetry.tracer import setup_tracing
from orchestration.routes.health import router as health_router
from orchestration.routes.query import router as query_router

logger = logging.getLogger(__name__)

setup_tracing(
    "orchestration",
    otlp_endpoint=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"),
)

chat_query_auth = require_permission("api:chat", "default", "query")


async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == 401:
        return JSONResponse(status_code=401, content={"code": "AUTH_FAILED"})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def create_app() -> FastAPI:
    app = FastAPI(title="AIAL Orchestration", version="0.1.0")
    app.add_exception_handler(HTTPException, _http_exception_handler)

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

    app.include_router(health_router)
    app.include_router(query_router, dependencies=[Depends(chat_query_auth)])

    return app


app = create_app()
