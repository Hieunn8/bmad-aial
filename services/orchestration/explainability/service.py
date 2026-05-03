"""Drill-down analytics and explainability service for Story 7.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from aial_shared.auth.keycloak import JWTClaims


class ExplainabilityJobStatus(StrEnum):
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ContributionFactor:
    label: str
    contribution_percent: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "contribution_percent": self.contribution_percent,
        }


@dataclass
class ExplainabilityJob:
    job_id: str
    owner_user_id: str
    department_scope: str
    status: ExplainabilityJobStatus = ExplainabilityJobStatus.QUEUED
    queue_name: str = "analytics-batch"
    task_name: str = "analytics.explainability.generate"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DrilldownExplainabilityService:
    def __init__(self) -> None:
        self._jobs: dict[str, ExplainabilityJob] = {}

    def build_analysis(
        self,
        *,
        principal: JWTClaims,
        dimension: str,
        shap_available: bool,
    ) -> dict[str, Any]:
        rows = self._drilldown_rows(principal=principal, dimension=dimension)
        base = {
            "dimension": dimension,
            "department_scope": principal.department,
            "forecast_metric": "total_revenue",
            "drilldown": rows,
            "confidence_label": "có khả năng tăng",
            "explanation_status": "ready" if shap_available else "pending",
        }
        if shap_available:
            base["top_factors"] = [
                ContributionFactor("Mùa vụ", 45).to_dict(),
                ContributionFactor("Xu hướng thị trường", 30).to_dict(),
                ContributionFactor("Chiến dịch marketing", 15).to_dict(),
            ]
            base["business_labels_mapped"] = True
            return base

        job = ExplainabilityJob(
            job_id=str(uuid4()),
            owner_user_id=principal.sub,
            department_scope=principal.department,
        )
        self._jobs[job.job_id] = job
        base["top_factors"] = []
        base["explainability_job"] = {
            "job_id": job.job_id,
            "status": job.status.value,
            "queue_name": job.queue_name,
            "task_name": job.task_name,
            "message": "Giải thích chi tiết đang được xử lý",
        }
        return base

    def process_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None or job.status != ExplainabilityJobStatus.QUEUED:
            return
        job.result = {
            "top_factors": [
                ContributionFactor("Mùa vụ", 45).to_dict(),
                ContributionFactor("Xu hướng thị trường", 30).to_dict(),
                ContributionFactor("Chiến dịch marketing", 15).to_dict(),
            ],
            "confidence_label": "có khả năng tăng",
        }
        job.status = ExplainabilityJobStatus.COMPLETED

    def get_job(self, *, job_id: str, principal: JWTClaims) -> ExplainabilityJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Explainability job not found")
        if job.owner_user_id != principal.sub or job.department_scope != principal.department:
            raise HTTPException(status_code=403, detail="Explainability job is outside your permitted scope")
        return job

    def get_job_result(self, *, job_id: str, principal: JWTClaims) -> dict[str, Any]:
        job = self.get_job(job_id=job_id, principal=principal)
        if job.status != ExplainabilityJobStatus.COMPLETED or job.result is None:
            raise HTTPException(status_code=409, detail="Explainability result is not ready")
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            **job.result,
        }

    def reset(self) -> None:
        self._jobs.clear()

    @staticmethod
    def _drilldown_rows(*, principal: JWTClaims, dimension: str) -> list[dict[str, Any]]:
        if dimension == "region":
            all_rows = [
                {"label": "HCM", "forecast_value": 4_800, "share_percent": 38},
                {"label": "Hà Nội", "forecast_value": 4_050, "share_percent": 32},
                {"label": "Đà Nẵng", "forecast_value": 3_750, "share_percent": 30},
            ]
            if principal.region:
                return [row for row in all_rows if row["label"].casefold() == principal.region.casefold()] or all_rows[:1]
            return all_rows
        if dimension == "product":
            return [
                {"label": "Sản phẩm A", "forecast_value": 5_400, "share_percent": 43},
                {"label": "Sản phẩm B", "forecast_value": 4_150, "share_percent": 33},
                {"label": "Sản phẩm C", "forecast_value": 3_050, "share_percent": 24},
            ]
        if dimension == "channel":
            return [
                {"label": "Retail", "forecast_value": 5_250, "share_percent": 42},
                {"label": "Online", "forecast_value": 4_200, "share_percent": 33},
                {"label": "Distributor", "forecast_value": 3_150, "share_percent": 25},
            ]
        return [
            {"label": principal.department.upper(), "forecast_value": 12_600, "share_percent": 100},
        ]


_service = DrilldownExplainabilityService()


def get_drilldown_explainability_service() -> DrilldownExplainabilityService:
    return _service


def reset_drilldown_explainability_service() -> None:
    _service.reset()
