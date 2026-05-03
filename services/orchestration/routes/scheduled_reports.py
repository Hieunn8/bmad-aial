"""Scheduled report routes — Epic 6 Story 6.2."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.exporting.service import ExportFormat
from orchestration.exporting.schedules import (
    ScheduleCadence,
    ScheduleStatus,
    get_scheduled_report_service,
)

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class CreateScheduledReportRequest(BaseModel):
    source_request_id: str
    cadence: ScheduleCadence
    format: ExportFormat
    recipient: str
    approval_request_id: str | None = None


class ScheduledReportResponse(BaseModel):
    schedule_id: str
    status: str
    cadence: str
    format: str
    recipient: str
    next_run_at: str
    approval_request_id: str | None = None


class RunDueSchedulesRequest(BaseModel):
    now: str | None = None


@router.post("/v1/chat/report-schedules", response_model=ScheduledReportResponse)
async def create_scheduled_report(
    body: CreateScheduledReportRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ScheduledReportResponse:
    schedule = get_scheduled_report_service().create_schedule(
        principal=principal,
        source_request_id=body.source_request_id,
        cadence=body.cadence,
        export_format=body.format,
        recipient=body.recipient,
        approval_request_id=body.approval_request_id,
    )
    return ScheduledReportResponse(
        schedule_id=schedule.schedule_id,
        status=schedule.status.value,
        cadence=schedule.cadence.value,
        format=schedule.format.value,
        recipient=schedule.recipient,
        next_run_at=schedule.next_run_at.isoformat(),
        approval_request_id=schedule.approval_request_id if schedule.status == ScheduleStatus.APPROVAL_REQUIRED else None,
    )


@router.get("/v1/chat/report-schedules")
async def list_scheduled_reports(
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, object]:
    schedules = get_scheduled_report_service().list_schedules(principal=principal)
    return {
        "schedules": [
            {
                "schedule_id": schedule.schedule_id,
                "status": schedule.status.value,
                "cadence": schedule.cadence.value,
                "format": schedule.format.value,
                "recipient": schedule.recipient,
                "next_run_at": schedule.next_run_at.isoformat(),
                "last_delivery_status": schedule.last_delivery_status,
            }
            for schedule in schedules
        ]
    }


@router.post("/v1/chat/report-schedules/run-due")
async def run_due_schedules(
    body: RunDueSchedulesRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, object]:
    now = datetime.fromisoformat(body.now) if body.now else datetime.now(UTC)
    attempts = get_scheduled_report_service().run_due_schedules(now=now)
    visible_schedule_ids = {schedule.schedule_id for schedule in get_scheduled_report_service().list_schedules(principal=principal)}
    visible_attempts = [attempt for attempt in attempts if attempt.schedule_id in visible_schedule_ids]
    return {
        "deliveries": [
            {
                "schedule_id": attempt.schedule_id,
                "recipient": attempt.recipient,
                "status": attempt.status,
                "attempts": attempt.attempts,
                "message": attempt.message,
            }
            for attempt in visible_attempts
        ]
    }
