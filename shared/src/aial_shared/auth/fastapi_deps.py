"""FastAPI dependencies for authentication and authorization.

Provides reusable Depends() callables that:
1. Extract and validate JWT from the Authorization header (authn)
2. Check Cerbos PDP for resource-level permissions (authz)

Kong handles JWT signature verification; these dependencies decode
claims and enforce Cerbos policies before the route handler runs.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from functools import lru_cache

from fastapi import Depends, HTTPException, Request

from aial_shared.auth.cerbos import CerbosClient
from aial_shared.auth.keycloak import (
    JWTClaims,
    TokenValidationError,
    decode_jwt,
    validate_token_claims,
)

logger = logging.getLogger(__name__)

_ISSUER = os.environ.get("KEYCLOAK_ISSUER", "http://localhost:8080/realms/aial")
_CERBOS_URL = os.environ.get("CERBOS_URL", "http://localhost:3592")


@lru_cache(maxsize=1)
def _get_cerbos_client() -> CerbosClient:
    return CerbosClient(base_url=_CERBOS_URL)


def reset_cerbos_client_cache() -> None:
    _get_cerbos_client.cache_clear()


async def get_current_user(request: Request) -> JWTClaims:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]

    try:
        loop = asyncio.get_running_loop()
        raw_claims = await loop.run_in_executor(
            None, lambda: decode_jwt(token, issuer=_ISSUER, verify=True)
        )
    except Exception as exc:
        logger.warning("JWT validation failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    try:
        return validate_token_claims(raw_claims)
    except TokenValidationError as exc:
        logger.warning("Token claims validation failed: %s", exc)
        raise HTTPException(status_code=401, detail=str(exc)) from exc


CURRENT_USER_DEP = Depends(get_current_user)
CERBOS_CLIENT_DEP = Depends(_get_cerbos_client)


def require_permission(
    resource_kind: str,
    resource_id: str,
    action: str,
) -> Callable:
    async def _check_permission(
        principal: JWTClaims = CURRENT_USER_DEP,
        cerbos: CerbosClient = CERBOS_CLIENT_DEP,
    ) -> JWTClaims:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: cerbos.check(principal, resource_kind, resource_id, action)
        )
        if not result.allowed:
            logger.info(
                "Cerbos DENY: principal=%s resource=%s action=%s",
                result.principal_id,
                result.resource,
                result.action,
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {action} on {resource_kind}",
            )
        return principal

    return _check_permission
