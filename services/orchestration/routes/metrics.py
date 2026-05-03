"""Prometheus metrics endpoint for orchestration runtime signals."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from orchestration.cache.query_result_cache import get_query_result_cache

router = APIRouter()


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        content=get_query_result_cache().render_prometheus_metrics(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
