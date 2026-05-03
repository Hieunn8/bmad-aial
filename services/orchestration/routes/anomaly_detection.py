"""Anomaly detection routes for Epic 7 Story 7.2."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.anomaly_detection.service import get_anomaly_detection_service
from orchestration.audit.read_model import AuditRecord, get_audit_read_model

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class AnomalyRunRequest(BaseModel):
    metric_name: str = Field(min_length=1, max_length=200)
    domain: str = Field(default="sales", min_length=1, max_length=100)
    region: str = Field(default="HCM", min_length=1, max_length=100)


def _append_anomaly_audit(
    principal: JWTClaims,
    *,
    intent_type: str,
    metadata: dict[str, Any],
) -> None:
    get_audit_read_model().append(
        AuditRecord(
            request_id=str(uuid4()),
            user_id=principal.sub,
            department_id=principal.department,
            session_id="anomaly-session",
            timestamp=datetime.now(UTC),
            intent_type=intent_type,
            sensitivity_tier="LOW",
            sql_hash=None,
            data_sources=[metadata.get("domain", "sales")],
            rows_returned=0,
            latency_ms=0,
            policy_decision="ALLOW",
            status="SUCCESS",
            metadata=metadata,
        )
    )


@router.post("/v1/anomaly-detection/run")
async def run_anomaly_detection(
    body: AnomalyRunRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    result = get_anomaly_detection_service().run_detection(
        metric_name=body.metric_name,
        principal=principal,
        domain=body.domain,
        region=body.region,
    )
    _append_anomaly_audit(principal, intent_type="anomaly:run", metadata={**result, "domain": body.domain, "region": body.region})
    return result


@router.get("/v1/anomaly-detection/alerts")
async def list_anomaly_alerts(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    alerts = get_anomaly_detection_service().list_alerts(principal=principal)
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/v1/anomaly-detection/alerts/{alert_id}")
async def get_anomaly_alert(alert_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    return get_anomaly_detection_service().get_alert(alert_id=alert_id, principal=principal)


@router.post("/v1/anomaly-detection/alerts/{alert_id}/acknowledge")
async def acknowledge_anomaly_alert(alert_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    alert = get_anomaly_detection_service().acknowledge_alert(alert_id=alert_id, principal=principal)
    _append_anomaly_audit(principal, intent_type="anomaly:acknowledge", metadata={"alert_id": alert_id, "domain": alert["domain"]})
    return {"alert": alert}


@router.post("/v1/anomaly-detection/alerts/{alert_id}/dismiss")
async def dismiss_anomaly_alert(alert_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    alert = get_anomaly_detection_service().dismiss_alert(alert_id=alert_id, principal=principal)
    _append_anomaly_audit(principal, intent_type="anomaly:dismiss", metadata={"alert_id": alert_id, "domain": alert["domain"]})
    return {"alert": alert}
