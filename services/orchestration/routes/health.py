"""Health and readiness endpoints for the orchestration service."""

from __future__ import annotations

import asyncio
import socket
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

HEALTH_DEPS = {
    "postgres": ("localhost", 5432),
    "redis": ("localhost", 6379),
    "cerbos": ("localhost", 3592),
}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/readiness")
async def readiness() -> JSONResponse:
    loop = asyncio.get_running_loop()
    items = list(HEALTH_DEPS.items())
    results: list[bool] = await asyncio.gather(
        *(loop.run_in_executor(None, _tcp_check, host, port) for _, (host, port) in items)
    )
    checks: dict[str, Any] = {
        name: "ok" if ok else "unreachable" for (name, _), ok in zip(items, results, strict=False)
    }
    all_ok = all(results)
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=200 if all_ok else 503,
    )


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False
