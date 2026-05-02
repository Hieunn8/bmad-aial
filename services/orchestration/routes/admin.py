"""Admin routes — Compliance Dashboard (Story 2B.5).

Authorization invariants:
  - admin/data_owner roles: can query all audit records, apply any filter.
  - Regular users: can only see their own records (user_id locked to principal.sub).
  - No route shares the chat-query permission — admin routes require admin/data_owner.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditFilter, get_audit_read_model

router = APIRouter(prefix="/v1/admin")
CURRENT_USER_DEP = Depends(get_current_user)

_ADMIN_ROLES = frozenset({"admin", "data_owner"})


def _require_admin_or_self(principal: JWTClaims, requested_user_id: str | None) -> str | None:
    """Return the effective user_id filter. Raises 403 if non-admin tries to query other users."""
    is_admin = bool(_ADMIN_ROLES & set(principal.roles))
    if is_admin:
        return requested_user_id  # admin sees whatever filter was requested
    if requested_user_id and requested_user_id != principal.sub:
        raise HTTPException(status_code=403, detail="Non-admin users may only view their own audit records")
    return principal.sub  # non-admin always scoped to their own records


class AuditLogResponse(BaseModel):
    records: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


@router.get("/audit-logs", response_model=AuditLogResponse)
async def list_audit_logs(
    user_id: Annotated[str | None, Query()] = None,
    department_id: Annotated[str | None, Query()] = None,
    policy_decision: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> AuditLogResponse:
    """Read-only compliance audit log. Scoped by role:
    - admin/data_owner: full access, any user filter accepted.
    - Others: results locked to caller's own user_id.
    """
    effective_user_id = _require_admin_or_self(principal, user_id)
    audit_filter = AuditFilter(
        user_id=effective_user_id,
        department_id=department_id,
        policy_decision=policy_decision,
        status=status,
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
    )
    model = get_audit_read_model()
    records = model.search(audit_filter, page=page, page_size=page_size)
    total = model.count(audit_filter)
    return AuditLogResponse(
        records=[r.to_response_dict() for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )
