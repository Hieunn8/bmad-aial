"""Health and readiness endpoints for the orchestration service."""

from __future__ import annotations

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
    checks: dict[str, Any] = {}
    all_ok = True

    for name, (host, port) in HEALTH_DEPS.items():
        ok = _tcp_check(host, port)
        checks[name] = "ok" if ok else "unreachable"
        if not ok:
            all_ok = False

    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code,
    )


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False
