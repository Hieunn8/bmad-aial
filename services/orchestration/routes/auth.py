"""Local auth routes for username/password development login."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from aial_shared.auth.local_tokens import issue_local_token
from orchestration.persistence.local_auth_store import LocalAuthUser, get_local_auth_store

router = APIRouter(prefix="/v1/auth")
CURRENT_USER_DEP = Depends(get_current_user)

_ACCESS_EXPIRES_SECONDS = int(os.getenv("AIAL_LOCAL_AUTH_ACCESS_TTL_SECONDS", "3600"))
_REFRESH_EXPIRES_SECONDS = int(os.getenv("AIAL_LOCAL_AUTH_REFRESH_TTL_SECONDS", "86400"))
_LOCAL_AUTH_SECRET = os.getenv("AIAL_LOCAL_AUTH_SECRET", "aial-local-dev-secret")


class LocalLoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LocalRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LocalUserCreateRequest(BaseModel):
    username: str
    password: str
    email: str
    department: str
    roles: list[str] = []
    clearance: int = 1


def _require_admin(principal: JWTClaims) -> None:
    if "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Admin role required")


def _issue_tokens(user: LocalAuthUser) -> dict[str, Any]:
    access_token = issue_local_token(
        secret=_LOCAL_AUTH_SECRET,
        subject=user.username,
        email=user.email,
        department=user.department,
        roles=list(user.roles),
        clearance=user.clearance,
        token_use="access",
        expires_in_seconds=_ACCESS_EXPIRES_SECONDS,
    )
    refresh_token = issue_local_token(
        secret=_LOCAL_AUTH_SECRET,
        subject=user.username,
        email=user.email,
        department=user.department,
        roles=list(user.roles),
        clearance=user.clearance,
        token_use="refresh",
        expires_in_seconds=_REFRESH_EXPIRES_SECONDS,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "id_token": "",
        "token_type": "Bearer",
        "expires_in": _ACCESS_EXPIRES_SECONDS,
        "refresh_expires_in": _REFRESH_EXPIRES_SECONDS,
        "user": user.to_dict(),
    }


@router.post("/login")
async def local_login(body: LocalLoginRequest) -> dict[str, Any]:
    user = get_local_auth_store().verify_credentials(body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return _issue_tokens(user)


@router.post("/refresh")
async def local_refresh(body: LocalRefreshRequest) -> dict[str, Any]:
    from aial_shared.auth.local_tokens import decode_local_token

    try:
        payload = decode_local_token(body.refresh_token, secret=_LOCAL_AUTH_SECRET, token_use="refresh")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    user = get_local_auth_store().get_user(str(payload["sub"]))
    if user is None or user.disabled:
        raise HTTPException(status_code=401, detail="Refresh user not available")
    return _issue_tokens(user)


@router.get("/me")
async def get_me(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    return {
        "sub": principal.sub,
        "email": principal.email,
        "department": principal.department,
        "roles": list(principal.roles),
        "clearance": principal.clearance,
    }


@router.get("/local-users")
async def list_local_users(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    users = get_local_auth_store().list_users()
    return {"users": [user.to_dict() for user in users], "total": len(users)}


@router.post("/local-users", status_code=201)
async def create_local_user(
    body: LocalUserCreateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    user = get_local_auth_store().create_user(
        username=body.username,
        password=body.password,
        email=body.email,
        department=body.department,
        roles=body.roles,
        clearance=body.clearance,
    )
    return {"user": user.to_dict()}
