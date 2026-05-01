"""Admin routes — Compliance Dashboard (Story 2B.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditFilter, get_audit_read_model

router = APIRouter(prefix="/v1/admin")
CURRENT_USER_DEP = Depends(get_current_user)


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
    """Read-only compliance audit log. No edit/delete operations available."""
    audit_filter = AuditFilter(
        user_id=user_id,
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
