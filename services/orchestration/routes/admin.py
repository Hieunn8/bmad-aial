"""Admin routes - compliance dashboard + user and role management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.admin_control.user_role_management import (
    RoleDefinition,
    get_user_role_management_service,
)
from orchestration.audit.read_model import AuditFilter, AuditRecord, get_audit_read_model
from orchestration.semantic.management import get_semantic_layer_service

router = APIRouter(prefix="/v1/admin")
CURRENT_USER_DEP = Depends(get_current_user)

_ADMIN_ROLES = frozenset({"admin", "data_owner"})


def _require_admin_or_self(principal: JWTClaims, requested_user_id: str | None) -> str | None:
    """Return the effective user_id filter. Raises 403 if non-admin tries to query other users."""
    is_admin = bool(_ADMIN_ROLES & set(principal.roles))
    if is_admin:
        return requested_user_id
    if requested_user_id and requested_user_id != principal.sub:
        raise HTTPException(status_code=403, detail="Non-admin users may only view their own audit records")
    return principal.sub


def _require_admin(principal: JWTClaims) -> None:
    if "admin" not in principal.roles:
        raise HTTPException(status_code=403, detail="Admin role required")


def _require_data_owner_or_admin(principal: JWTClaims) -> None:
    if not _ADMIN_ROLES.intersection(principal.roles):
        raise HTTPException(status_code=403, detail="Admin or data_owner role required")


class AuditLogResponse(BaseModel):
    records: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class RoleCreateRequest(BaseModel):
    name: str
    schema_allowlist: list[str]


class UserCreateRequest(BaseModel):
    user_id: str
    email: str
    department: str
    roles: list[str] = []
    ldap_groups: list[str] = []


class UserUpdateRequest(BaseModel):
    email: str | None = None
    department: str | None = None
    roles: list[str] | None = None
    ldap_groups: list[str] | None = None


class BulkImportRequest(BaseModel):
    csv_content: str


class LdapSyncUserUpdate(BaseModel):
    user_id: str
    department: str
    roles: list[str] = []
    ldap_groups: list[str] = []


class LdapSyncRequest(BaseModel):
    updates: list[LdapSyncUserUpdate]
    interval_minutes: int | None = None


class DataSourceCreateRequest(BaseModel):
    name: str
    host: str
    port: int
    service_name: str
    username: str
    password: str
    schema_allowlist: list[str]
    query_timeout_seconds: int = 30
    row_limit: int = 50_000


class DataSourceUpdateRequest(BaseModel):
    host: str | None = None
    port: int | None = None
    service_name: str | None = None
    username: str | None = None
    password: str | None = None
    schema_allowlist: list[str] | None = None
    query_timeout_seconds: int | None = None
    row_limit: int | None = None


class AlertSettingRequest(BaseModel):
    scope_type: str
    scope_id: str
    metric_name: str
    threshold: float


class SemanticMetricPublishRequest(BaseModel):
    term: str
    definition: str
    formula: str
    owner: str
    freshness_rule: str


class SemanticMetricRollbackRequest(BaseModel):
    version_id: str
    reason: str | None = None


@router.get("/audit-logs", response_model=AuditLogResponse)
async def list_audit_logs(
    user_id: Annotated[str | None, Query()] = None,
    department_id: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    data_source: Annotated[str | None, Query()] = None,
    policy_decision: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> AuditLogResponse:
    effective_user_id = _require_admin_or_self(principal, user_id)
    audit_filter = AuditFilter(
        user_id=effective_user_id,
        department_id=department_id,
        action=action,
        data_source=data_source,
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


@router.get("/audit-logs/export", response_class=PlainTextResponse)
async def export_audit_logs(
    user_id: Annotated[str | None, Query()] = None,
    department_id: Annotated[str | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    data_source: Annotated[str | None, Query()] = None,
    policy_decision: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
    request_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> PlainTextResponse:
    effective_user_id = _require_admin_or_self(principal, user_id)
    audit_filter = AuditFilter(
        user_id=effective_user_id,
        department_id=department_id,
        action=action,
        data_source=data_source,
        policy_decision=policy_decision,
        status=status,
        request_id=request_id,
        date_from=date_from,
        date_to=date_to,
    )
    model = get_audit_read_model()
    records = [record.to_response_dict() for record in model.search_all(audit_filter)]
    csv_content = get_user_role_management_service().export_audit_records_csv(records)
    _append_admin_audit(
        principal,
        intent_type="admin:audit_export",
        data_sources=[data_source] if data_source else [],
        status="SUCCESS",
        metadata={"exported_rows": len(records)},
    )
    return PlainTextResponse(content=csv_content, media_type="text/csv")


@router.get("/audit-logs/{request_id}/lifecycle")
async def get_audit_lifecycle(
    request_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    effective_user_id = _require_admin_or_self(principal, None)
    model = get_audit_read_model()
    records = model.search(
        AuditFilter(request_id=request_id, user_id=effective_user_id if "admin" not in principal.roles else None),
        page=1,
        page_size=500,
    )
    if not records:
        raise HTTPException(status_code=404, detail="Request lifecycle not found")
    ordered = sorted(records, key=lambda record: record.timestamp)
    return {
        "request_id": request_id,
        "events": [record.to_response_dict() for record in ordered],
        "event_count": len(ordered),
    }


@router.post("/roles", status_code=201)
async def create_role(
    body: RoleCreateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        role = service.create_role(name=body.name, schema_allowlist=body.schema_allowlist, actor=principal.sub)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:role_create",
        data_sources=role.schema_allowlist,
        status="SUCCESS",
    )
    return {"role": _role_to_dict(role)}


@router.get("/roles")
async def list_roles(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    roles = get_user_role_management_service().list_roles()
    return {"roles": [_role_to_dict(role) for role in roles], "total": len(roles)}


@router.post("/users", status_code=201)
async def create_user(
    body: UserCreateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        user = service.create_user(
            user_id=body.user_id,
            email=body.email,
            department=body.department,
            roles=body.roles,
            ldap_groups=body.ldap_groups,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:user_create",
        data_sources=[user.user_id],
        status="SUCCESS",
    )
    return {"user": user.to_dict()}


@router.get("/users")
async def list_users(
    include_deleted: bool = False,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    users = get_user_role_management_service().list_users(include_deleted=include_deleted)
    return {"users": [user.to_dict() for user in users], "total": len(users)}


@router.post("/users/import/preview")
async def preview_bulk_import(
    body: BulkImportRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    return get_user_role_management_service().preview_bulk_import(body.csv_content)


@router.post("/users/import/commit", status_code=201)
async def commit_bulk_import(
    body: BulkImportRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        imported = service.commit_bulk_import(body.csv_content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:user_bulk_import",
        data_sources=[user.user_id for user in imported],
        status="SUCCESS",
        rows_returned=len(imported),
    )
    return {"imported": len(imported), "users": [user.to_dict() for user in imported]}


@router.get("/users/sync-status")
async def ldap_sync_status(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    return get_user_role_management_service().get_sync_status().to_dict()


@router.post("/users/ldap-sync")
async def run_ldap_sync(
    body: LdapSyncRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    status = get_user_role_management_service().run_ldap_sync(
        updates=[update.model_dump() for update in body.updates],
        interval_minutes=body.interval_minutes,
    )
    _append_admin_audit(
        principal,
        intent_type="admin:ldap_sync",
        data_sources=[update.user_id for update in body.updates],
        status="SUCCESS",
        rows_returned=status.synced_users,
    )
    return {"sync": status.to_dict()}


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    user = get_user_role_management_service().get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user.to_dict()}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        user = service.update_user(
            user_id,
            email=body.email,
            department=body.department,
            roles=body.roles,
            ldap_groups=body.ldap_groups,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:user_update",
        data_sources=[user.user_id],
        status="SUCCESS",
    )
    return {"user": user.to_dict(), "status": "updated"}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        user = service.soft_delete_user(user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User not found") from exc
    _append_admin_audit(
        principal,
        intent_type="admin:user_delete",
        data_sources=[user.user_id],
        status="SUCCESS",
    )
    return {"status": "deleted", "user": user.to_dict()}


@router.post("/data-sources", status_code=201)
async def create_data_source(
    body: DataSourceCreateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        config = service.create_data_source(
            name=body.name,
            host=body.host,
            port=body.port,
            service_name=body.service_name,
            username=body.username,
            password=body.password,
            schema_allowlist=body.schema_allowlist,
            query_timeout_seconds=body.query_timeout_seconds,
            row_limit=body.row_limit,
            actor=principal.sub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:data_source_create",
        data_sources=[config.name],
        status="SUCCESS",
        metadata={
            "row_limit": config.row_limit,
            "query_timeout_seconds": config.query_timeout_seconds,
            "status": config.status,
        },
    )
    return {"data_source": config.to_dict()}


@router.get("/data-sources")
async def list_data_sources(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    data_sources = get_user_role_management_service().list_data_sources()
    return {
        "data_sources": [data_source.to_dict() for data_source in data_sources],
        "total": len(data_sources),
    }


@router.get("/data-sources/{name}")
async def get_data_source(
    name: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    config = get_user_role_management_service().get_data_source(name)
    if config is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {
        "data_source": config.to_dict(),
        "query_execution": get_user_role_management_service().get_query_execution_settings(name),
    }


@router.patch("/data-sources/{name}")
async def update_data_source(
    name: str,
    body: DataSourceUpdateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        config, changes = service.update_data_source(
            name,
            host=body.host,
            port=body.port,
            service_name=body.service_name,
            username=body.username,
            password=body.password,
            schema_allowlist=body.schema_allowlist,
            query_timeout_seconds=body.query_timeout_seconds,
            row_limit=body.row_limit,
            actor=principal.sub,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Data source not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:data_source_update",
        data_sources=[config.name],
        status="SUCCESS",
        metadata=changes,
    )
    return {"data_source": config.to_dict(), "changes": changes}


@router.get("/system-health")
async def get_system_health(
    time_range: Annotated[str, Query()] = "last_30_minutes",
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    dashboard = service.get_health_dashboard(time_range=time_range)
    for alert in service.drain_pending_alert_audits():
        _append_admin_audit(
            principal,
            intent_type="admin:health_alert_fired",
            data_sources=[],
            status="SUCCESS",
            metadata=alert.to_dict(),
        )
    return dashboard


@router.put("/system-health/alert-settings")
async def upsert_alert_setting(
    body: AlertSettingRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        setting = service.upsert_alert_setting(
            scope_type=body.scope_type,
            scope_id=body.scope_id,
            metric_name=body.metric_name,
            threshold=body.threshold,
            actor=principal.sub,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _append_admin_audit(
        principal,
        intent_type="admin:health_alert_setting_update",
        data_sources=[],
        status="SUCCESS",
        metadata=setting.to_dict(),
    )
    return {"alert_setting": setting.to_dict()}


@router.post("/system-health/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_admin(principal)
    service = get_user_role_management_service()
    try:
        alert = service.acknowledge_alert(alert_id, actor=principal.sub)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Alert not found") from exc
    _append_admin_audit(
        principal,
        intent_type="admin:health_alert_acknowledge",
        data_sources=[],
        status="SUCCESS",
        metadata=alert.to_dict(),
    )
    return {"alert": alert.to_dict()}


@router.get("/semantic-layer/metrics")
async def list_semantic_metrics(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_data_owner_or_admin(principal)
    metrics = get_semantic_layer_service().list_metrics()
    return {"metrics": metrics, "total": len(metrics)}


@router.get("/semantic-layer/metrics/{term}/versions")
async def list_semantic_metric_versions(
    term: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_data_owner_or_admin(principal)
    versions = [version.to_dict() for version in get_semantic_layer_service().get_versions(term)]
    if not versions:
        raise HTTPException(status_code=404, detail="Metric not found")
    return {"versions": versions, "total": len(versions)}


@router.post("/semantic-layer/metrics/publish", status_code=201)
async def publish_semantic_metric(
    body: SemanticMetricPublishRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_data_owner_or_admin(principal)
    version = get_semantic_layer_service().publish_metric(
        term=body.term,
        definition=body.definition,
        formula=body.formula,
        owner=body.owner,
        freshness_rule=body.freshness_rule,
        changed_by=principal.sub,
    )
    _append_admin_audit(
        principal,
        intent_type="admin:semantic_metric_publish",
        data_sources=[body.term],
        status="SUCCESS",
        metadata={
            "version_id": version.version_id,
            "previous_formula": version.previous_formula,
            "new_formula": version.formula,
            "cache_invalidated_at": get_semantic_layer_service().cache_invalidated_at.isoformat(),
        },
    )
    return {"version": version.to_dict()}


@router.get("/semantic-layer/metrics/{term}/diff")
async def diff_semantic_metric_versions(
    term: str,
    from_version_id: str,
    to_version_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_data_owner_or_admin(principal)
    try:
        return get_semantic_layer_service().diff_versions(
            term=term,
            left_version_id=from_version_id,
            right_version_id=to_version_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc


@router.post("/semantic-layer/metrics/{term}/rollback", status_code=201)
async def rollback_semantic_metric(
    term: str,
    body: SemanticMetricRollbackRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    _require_data_owner_or_admin(principal)
    try:
        version = get_semantic_layer_service().rollback_metric(
            term=term,
            target_version_id=body.version_id,
            changed_by=principal.sub,
            reason=body.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Version not found") from exc
    _append_admin_audit(
        principal,
        intent_type="admin:semantic_metric_rollback",
        data_sources=[term],
        status="SUCCESS",
        metadata={
            "version_id": version.version_id,
            "rollback_reason": body.reason,
            "new_formula": version.formula,
            "cache_invalidated_at": get_semantic_layer_service().cache_invalidated_at.isoformat(),
        },
    )
    return {"version": version.to_dict()}


def _role_to_dict(role: RoleDefinition) -> dict[str, Any]:
    return {
        "name": role.name,
        "schema_allowlist": role.schema_allowlist,
        "created_by": role.created_by,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
        "cerbos_policy_status": role.cerbos_policy_status,
        "data_source_config_status": role.data_source_config_status,
    }


def _append_admin_audit(
    principal: JWTClaims,
    *,
    intent_type: str,
    data_sources: list[str],
    status: str,
    rows_returned: int = 0,
    denial_reason: str | None = None,
    cerbos_rule: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    get_audit_read_model().append(
        AuditRecord(
            request_id=request_id or str(uuid4()),
            user_id=principal.sub,
            department_id=principal.department,
            session_id="admin-session",
            timestamp=datetime.now(UTC),
            intent_type=intent_type,
            sensitivity_tier="LOW",
            sql_hash=None,
            data_sources=data_sources,
            rows_returned=rows_returned,
            latency_ms=0,
            policy_decision="ALLOW",
            status=status,
            denial_reason=denial_reason,
            cerbos_rule=cerbos_rule,
            metadata=metadata,
        )
    )
