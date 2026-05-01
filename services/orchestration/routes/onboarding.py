"""User onboarding role preference API — Story 2A.9.

Stores role preference server-side (NOT localStorage) per architecture requirement.
In-memory store for Phase 1; Epic 5A upgrades to PostgreSQL.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.onboarding.roles import ROLE_INTENT_HINTS, ROLE_PLACEHOLDERS, UserRole

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)

# In-memory store: user_id → role (replaced by DB in Epic 5A)
_role_store: dict[str, str] = {}


class RolePreferenceResponse(BaseModel):
    has_preference: bool
    role: str | None = None
    placeholder: str | None = None


class SetRoleRequest(BaseModel):
    role: str


@router.get("/v1/user/role-preference", response_model=RolePreferenceResponse)
async def get_role_preference(principal: JWTClaims = CURRENT_USER_DEP) -> RolePreferenceResponse:
    stored = _role_store.get(principal.sub)
    if stored is None:
        return RolePreferenceResponse(has_preference=False)
    try:
        role = UserRole(stored)
        from orchestration.onboarding.roles import ROLE_PLACEHOLDERS
        return RolePreferenceResponse(has_preference=True, role=role.value, placeholder=ROLE_PLACEHOLDERS[role])
    except ValueError:
        return RolePreferenceResponse(has_preference=False)


@router.post("/v1/user/role-preference")
async def set_role_preference(
    body: SetRoleRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> JSONResponse:
    try:
        role = UserRole(body.role)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"code": "INVALID_ROLE", "detail": f"Unknown role '{body.role}'"},
        )
    _role_store[principal.sub] = role.value
    return JSONResponse(status_code=200, content={
        "role": role.value,
        "placeholder": ROLE_PLACEHOLDERS[role],
        "intent_hint": ROLE_INTENT_HINTS[role],
    })
