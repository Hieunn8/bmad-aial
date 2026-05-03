"""Export routes — Epic 6 Story 6.1."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.exporting.service import ExportFormat, ExportJobStatus, get_export_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class ExportPreviewResponse(BaseModel):
    request_id: str
    format: str
    estimated_row_count: int
    sensitivity_tier: int
    sensitivity_warning: str | None = None
    department_scope: str


class CreateExportRequest(BaseModel):
    format: ExportFormat
    human_review_confirmed: bool
    recipient: str | None = None


class ExportJobHandle(BaseModel):
    job_id: str
    status: str
    queue_name: str
    task_name: str


class ExportJobStatusResponse(BaseModel):
    job_id: str
    request_id: str
    status: str
    format: str
    row_count: int
    department_scope: str
    sensitivity_tier: int
    download_url: str | None = None
    expires_at: str | None = None
    error: str | None = None


@router.get("/v1/chat/query/{request_id}/export-preview", response_model=ExportPreviewResponse)
async def get_export_preview(
    request_id: str,
    format: ExportFormat,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ExportPreviewResponse:
    preview = get_export_service().get_preview(request_id=request_id, principal=principal, export_format=format)
    return ExportPreviewResponse(**preview)


@router.post("/v1/chat/query/{request_id}/export", response_model=ExportJobHandle)
async def create_export_job(
    request_id: str,
    body: CreateExportRequest,
    background_tasks: BackgroundTasks,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ExportJobHandle:
    if not body.human_review_confirmed:
        raise HTTPException(status_code=400, detail="Human review confirmation is required before export")

    job = get_export_service().enqueue_job(
        request_id=request_id,
        principal=principal,
        export_format=body.format,
        recipient=body.recipient,
    )
    background_tasks.add_task(get_export_service().process_job, job.job_id)
    return ExportJobHandle(
        job_id=job.job_id,
        status=ExportJobStatus.QUEUED.value,
        queue_name=job.queue_name,
        task_name=job.task_name,
    )


@router.get("/v1/chat/exports/{job_id}", response_model=ExportJobStatusResponse)
async def get_export_job_status(
    job_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ExportJobStatusResponse:
    job = get_export_service().get_job(job_id=job_id, principal=principal)
    return ExportJobStatusResponse(
        job_id=job.job_id,
        request_id=job.request_id,
        status=job.status.value,
        format=job.format.value,
        row_count=job.row_count,
        department_scope=job.department_scope,
        sensitivity_tier=job.sensitivity_tier,
        download_url=job.download_path,
        expires_at=job.expires_at.isoformat() if job.expires_at else None,
        error=job.error,
    )


@router.get("/v1/chat/exports/{job_id}/download")
async def download_export_file(
    job_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> Response:
    payload, media_type, filename = get_export_service().get_download(job_id=job_id, principal=principal)
    return Response(
        content=payload,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
