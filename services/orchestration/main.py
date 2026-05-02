"""AIAL Orchestration Service — FastAPI application entry point."""

from __future__ import annotations

import logging
import os

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from aial_shared.auth.fastapi_deps import require_permission
from aial_shared.telemetry.tracer import setup_tracing
from orchestration.routes.admin import router as admin_router
from orchestration.routes.documents import router as documents_router
from orchestration.routes.glossary import router as glossary_router
from orchestration.routes.health import router as health_router
from orchestration.routes.onboarding import router as onboarding_router
from orchestration.routes.query import _INVALID_QUERY_TYPE, router as query_router
from orchestration.routes.stream import router as stream_router

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


async def _validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    detail = first_error.get("msg", "Invalid request")
    return JSONResponse(
        status_code=400,
        content={"type": _INVALID_QUERY_TYPE, "detail": detail},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="AIAL Orchestration", version="0.1.0")
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)

    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

    app.include_router(health_router)
    app.include_router(query_router, dependencies=[Depends(chat_query_auth)])
    app.include_router(glossary_router, dependencies=[Depends(chat_query_auth)])
    app.include_router(stream_router, dependencies=[Depends(chat_query_auth)])
    app.include_router(onboarding_router, dependencies=[Depends(chat_query_auth)])
    app.include_router(admin_router, dependencies=[Depends(chat_query_auth)])
    app.include_router(documents_router, dependencies=[Depends(chat_query_auth)])

    return app


app = create_app()
