"""Forecast routes for Epic 7 Story 7.1."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Response
from pydantic import BaseModel, Field

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.forecasting.service import ForecastJobStatus, get_forecast_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class ForecastRunRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class ForecastJobHandle(BaseModel):
    job_id: str
    status: str
    queue_name: str
    task_name: str
    heavy_job: bool
    estimated_wait_seconds: int | None = None
    estimated_wait_message: str | None = None


class ForecastJobStatusResponse(BaseModel):
    job_id: str
    status: str
    queue_name: str
    task_name: str
    heavy_job: bool
    estimated_wait_seconds: int | None = None
    estimated_wait_message: str | None = None
    provider_used: str | None = None
    mape: float | None = None
    download_url: str | None = None
    cached_until: str | None = None
    error: str | None = None


@router.post("/v1/forecast/run", response_model=ForecastJobHandle)
async def run_forecast(
    body: ForecastRunRequest,
    background_tasks: BackgroundTasks,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ForecastJobHandle:
    job = get_forecast_service().enqueue_job(query=body.query, principal=principal)
    background_tasks.add_task(get_forecast_service().process_job, job.job_id)
    return ForecastJobHandle(
        job_id=job.job_id,
        status=ForecastJobStatus.QUEUED.value,
        queue_name=job.queue_name,
        task_name=job.task_name,
        heavy_job=job.is_heavy,
        estimated_wait_seconds=job.estimated_wait_seconds,
        estimated_wait_message=_estimated_wait_message(job.estimated_wait_seconds),
    )


@router.get("/v1/forecast/{job_id}", response_model=ForecastJobStatusResponse)
async def get_forecast_status(job_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> ForecastJobStatusResponse:
    job = get_forecast_service().get_job(job_id=job_id, principal=principal)
    return ForecastJobStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        queue_name=job.queue_name,
        task_name=job.task_name,
        heavy_job=job.is_heavy,
        estimated_wait_seconds=job.estimated_wait_seconds,
        estimated_wait_message=_estimated_wait_message(job.estimated_wait_seconds),
        provider_used=job.provider_used,
        mape=job.mape,
        download_url=job.download_path,
        cached_until=job.expires_at.isoformat() if job.expires_at else None,
        error=job.error,
    )


@router.get("/v1/forecast/{job_id}/result")
async def get_forecast_result(job_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> dict:
    return get_forecast_service().get_result(job_id=job_id, principal=principal)


@router.get("/v1/forecast/{job_id}/download")
async def download_forecast_result(job_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> Response:
    payload, media_type, filename = get_forecast_service().get_download(job_id=job_id, principal=principal)
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _estimated_wait_message(estimated_wait_seconds: int | None) -> str | None:
    if estimated_wait_seconds is None:
        return None
    minutes = max(1, round(estimated_wait_seconds / 60))
    if minutes >= 15:
        return f"Kết quả dự kiến sau {minutes} phút."
    return f"Kết quả dự kiến sau khoảng {minutes} phút."
