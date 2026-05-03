"""Drill-down analytics and result explainability routes for Story 7.4."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditRecord, get_audit_read_model
from orchestration.explainability.service import get_drilldown_explainability_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class DrilldownExplainabilityRequest(BaseModel):
    dimension: Literal["department", "product", "region", "channel"] = "region"
    shap_available: bool = True


@router.post("/v1/analytics/drilldown-explainability")
async def run_drilldown_explainability(
    body: DrilldownExplainabilityRequest,
    background_tasks: BackgroundTasks,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    result = get_drilldown_explainability_service().build_analysis(
        principal=principal,
        dimension=body.dimension,
        shap_available=body.shap_available,
    )
    explainability_job = result.get("explainability_job")
    if isinstance(explainability_job, dict) and explainability_job.get("job_id"):
        background_tasks.add_task(get_drilldown_explainability_service().process_job, explainability_job["job_id"])
    get_audit_read_model().append(
        AuditRecord(
            request_id=str(uuid4()),
            user_id=principal.sub,
            department_id=principal.department,
            session_id="drilldown-session",
            timestamp=datetime.now(UTC),
            intent_type="analytics:drilldown_explainability",
            sensitivity_tier="LOW",
            sql_hash=None,
            data_sources=["forecast-analytics"],
            rows_returned=len(result["drilldown"]),
            latency_ms=0,
            policy_decision="ALLOW",
            status="SUCCESS",
            metadata={
                "dimension": body.dimension,
                "shap_available": body.shap_available,
                "explanation_status": result["explanation_status"],
            },
        )
    )
    return result


@router.get("/v1/analytics/explainability-jobs/{job_id}")
async def get_explainability_job(job_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    job = get_drilldown_explainability_service().get_job(job_id=job_id, principal=principal)
    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "queue_name": job.queue_name,
        "task_name": job.task_name,
        "error": job.error,
    }


@router.get("/v1/analytics/explainability-jobs/{job_id}/result")
async def get_explainability_job_result(job_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    return get_drilldown_explainability_service().get_job_result(job_id=job_id, principal=principal)
