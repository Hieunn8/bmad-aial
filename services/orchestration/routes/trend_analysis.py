"""Trend analysis routes for Epic 7 Story 7.3."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditRecord, get_audit_read_model
from orchestration.trend_analysis.service import get_trend_analysis_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class TrendRunRequest(BaseModel):
    metric_name: str = Field(min_length=1, max_length=200)
    comparison_type: Literal["yoy", "mom", "qoq"] = "yoy"
    dimension: Literal["department", "product", "region"] = "region"


@router.post("/v1/trend-analysis/run")
async def run_trend_analysis(body: TrendRunRequest, principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    result = get_trend_analysis_service().run_analysis(
        metric_name=body.metric_name,
        comparison_type=body.comparison_type,
        dimension=body.dimension,
        principal=principal,
    )
    get_audit_read_model().append(
        AuditRecord(
            request_id=str(uuid4()),
            user_id=principal.sub,
            department_id=principal.department,
            session_id="trend-session",
            timestamp=datetime.now(UTC),
            intent_type="trend:run",
            sensitivity_tier="LOW",
            sql_hash=None,
            data_sources=["semantic-trend"],
            rows_returned=len(result["drilldown"]),
            latency_ms=0,
            policy_decision="ALLOW",
            status="SUCCESS",
            metadata={
                "metric_name": body.metric_name,
                "comparison_type": body.comparison_type,
                "dimension": body.dimension,
                "cache_hit": result["cache_hit"],
                "provider_used": result["provider_used"],
            },
        )
    )
    return result
