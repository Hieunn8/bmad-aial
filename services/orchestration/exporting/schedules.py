"""Scheduled report service — Epic 6 Story 6.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from aial_shared.auth.keycloak import JWTClaims
from orchestration.approval.workflow import ApprovalState, QueryIntent, create_approval_request, get_approval_store
from orchestration.audit.read_model import AuditRecord, get_audit_read_model
from orchestration.exporting.service import ExportFormat, ExportJobStatus, get_export_service


class ScheduleCadence(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ScheduleStatus(StrEnum):
    APPROVAL_REQUIRED = "approval_required"
    ACTIVE = "active"
    PAUSED = "paused"
    FAILED = "failed"


@dataclass
class ReportSchedule:
    schedule_id: str
    owner_user_id: str
    source_request_id: str
    cadence: ScheduleCadence
    format: ExportFormat
    recipient: str
    department_scope: str
    sensitivity_tier: int
    status: ScheduleStatus
    created_at: datetime
    next_run_at: datetime
    approval_request_id: str | None = None
    last_run_at: datetime | None = None
    last_delivery_status: str | None = None
    last_error: str | None = None


@dataclass
class DeliveryAttempt:
    schedule_id: str
    recipient: str
    status: str
    attempts: int
    message: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ScheduledReportService:
    def __init__(self) -> None:
        self._schedules: dict[str, ReportSchedule] = {}
        self._notifications: list[DeliveryAttempt] = []

    def create_schedule(
        self,
        *,
        principal: JWTClaims,
        source_request_id: str,
        cadence: ScheduleCadence,
        export_format: ExportFormat,
        recipient: str,
        approval_request_id: str | None,
        now: datetime | None = None,
    ) -> ReportSchedule:
        artifact = get_export_service()._artifacts.get(source_request_id)  # existing secured export source
        if artifact is None:
            raise HTTPException(status_code=404, detail="Scheduled report source result not found")
        if artifact.owner_user_id != principal.sub:
            raise HTTPException(status_code=403, detail="Scheduled report source does not belong to this user")
        self._validate_recipient(recipient=recipient, principal=principal)

        current_time = now or datetime.now(UTC)
        status = ScheduleStatus.ACTIVE
        stored_approval_request_id = approval_request_id
        if artifact.sensitivity_tier >= 2:
            stored_approval_request_id = self._resolve_schedule_approval(
                principal=principal,
                artifact=artifact,
                cadence=cadence,
                export_format=export_format,
                recipient=recipient,
                approval_request_id=approval_request_id,
            )
            if approval_request_id is None:
                status = ScheduleStatus.APPROVAL_REQUIRED

        schedule = ReportSchedule(
            schedule_id=str(uuid4()),
            owner_user_id=principal.sub,
            source_request_id=source_request_id,
            cadence=cadence,
            format=export_format,
            recipient=recipient,
            department_scope=artifact.department_scope,
            sensitivity_tier=artifact.sensitivity_tier,
            status=status,
            created_at=current_time,
            next_run_at=self._next_run(cadence=cadence, now=current_time),
            approval_request_id=stored_approval_request_id,
        )
        self._schedules[schedule.schedule_id] = schedule
        return schedule

    def list_schedules(self, *, principal: JWTClaims) -> list[ReportSchedule]:
        return [schedule for schedule in self._schedules.values() if schedule.owner_user_id == principal.sub]

    def run_due_schedules(self, *, now: datetime | None = None) -> list[DeliveryAttempt]:
        current_time = now or datetime.now(UTC)
        attempts: list[DeliveryAttempt] = []
        for schedule in self._schedules.values():
            if schedule.status != ScheduleStatus.ACTIVE or schedule.next_run_at > current_time:
                continue
            attempt = self._deliver_schedule(schedule=schedule, now=current_time)
            attempts.append(attempt)
        self._notifications.extend(attempts)
        return attempts

    def notifications_for_user(self, *, user_id: str) -> list[DeliveryAttempt]:
        return [notification for notification in self._notifications if notification.schedule_id in {
            schedule.schedule_id for schedule in self._schedules.values() if schedule.owner_user_id == user_id
        }]

    def reset(self) -> None:
        self._schedules.clear()
        self._notifications.clear()

    def _resolve_schedule_approval(
        self,
        *,
        principal: JWTClaims,
        artifact: Any,
        cadence: ScheduleCadence,
        export_format: ExportFormat,
        recipient: str,
        approval_request_id: str | None,
    ) -> str:
        store = get_approval_store()
        intent = QueryIntent(
            user_id=principal.sub,
            department=principal.department,
            sensitivity_tier=artifact.sensitivity_tier,
            intent_type="scheduled_report",
            filters={
                "source_request_id": artifact.request_id,
                "cadence": cadence.value,
                "format": export_format.value,
                "recipient": recipient,
            },
            estimated_row_count=len(artifact.rows),
            query_digest=f"{artifact.request_id}:{cadence.value}:{export_format.value}:{recipient}",
        )
        if approval_request_id is None:
            request = create_approval_request(intent, store=store)
            return request.request_id

        request = store.get(approval_request_id)
        if request is None:
            raise HTTPException(status_code=404, detail="Approval request not found")
        if request.intent.user_id != principal.sub:
            raise HTTPException(status_code=403, detail="Approval request does not belong to this user")
        if request.query_fingerprint != intent.fingerprint():
            raise HTTPException(status_code=409, detail="Approval request does not match this scheduled report scope")
        if request.state != ApprovalState.APPROVED:
            raise HTTPException(status_code=409, detail="Scheduled report approval is still pending")
        return request.request_id

    def _deliver_schedule(self, *, schedule: ReportSchedule, now: datetime) -> DeliveryAttempt:
        max_attempts = 3
        attempt_counter = 0
        last_error = ""
        while attempt_counter < max_attempts:
            attempt_counter += 1
            try:
                self._send_report(schedule=schedule)
                schedule.last_run_at = now
                schedule.last_delivery_status = "delivered"
                schedule.last_error = None
                schedule.next_run_at = self._next_run(cadence=schedule.cadence, now=now)
                self._append_delivery_audit(schedule=schedule, status="delivered", timestamp=now)
                return DeliveryAttempt(
                    schedule_id=schedule.schedule_id,
                    recipient=schedule.recipient,
                    status="delivered",
                    attempts=attempt_counter,
                    message="Scheduled report delivered",
                )
            except Exception as exc:
                last_error = str(exc)

        schedule.last_run_at = now
        schedule.last_delivery_status = "failed"
        schedule.last_error = last_error
        self._append_delivery_audit(schedule=schedule, status="failed", timestamp=now, error=last_error)
        return DeliveryAttempt(
            schedule_id=schedule.schedule_id,
            recipient=schedule.recipient,
            status="failed",
            attempts=max_attempts,
            message="Bao cao tuan nay gap su co - lien he IT",
        )

    def _send_report(self, *, schedule: ReportSchedule) -> None:
        job = get_export_service().enqueue_job(
            request_id=schedule.source_request_id,
            principal=JWTClaims(
                sub=schedule.owner_user_id,
                email=schedule.recipient,
                department=schedule.department_scope,
                roles=("user",),
                clearance=1,
                raw={},
            ),
            export_format=schedule.format,
            recipient=schedule.recipient,
        )
        get_export_service().process_job(job.job_id)
        if job.status != ExportJobStatus.COMPLETED:
            raise RuntimeError(job.error or "Scheduled export failed")

    def _append_delivery_audit(
        self,
        *,
        schedule: ReportSchedule,
        status: str,
        timestamp: datetime,
        error: str | None = None,
    ) -> None:
        get_audit_read_model().append(
            AuditRecord(
                request_id=schedule.source_request_id,
                user_id=schedule.owner_user_id,
                department_id=schedule.department_scope,
                session_id=schedule.schedule_id,
                timestamp=timestamp,
                intent_type="export:scheduled_delivery",
                sensitivity_tier=f"TIER_{schedule.sensitivity_tier}",
                sql_hash=None,
                data_sources=[],
                rows_returned=0,
                latency_ms=0,
                policy_decision="ALLOW",
                status="SUCCESS" if status == "delivered" else "FAILED",
                denial_reason=error,
                metadata={
                    "schedule_id": schedule.schedule_id,
                    "recipient": schedule.recipient,
                    "format": schedule.format.value,
                    "cadence": schedule.cadence.value,
                    "status": status,
                    "timestamp": timestamp.isoformat(),
                },
            )
        )

    @staticmethod
    def _validate_recipient(*, recipient: str, principal: JWTClaims) -> None:
        if "@" not in recipient:
            raise HTTPException(status_code=400, detail="Recipient email is invalid")
        domain = principal.email.split("@")[-1]
        if recipient.split("@")[-1] != domain:
            raise HTTPException(status_code=400, detail="Reports may only be sent to internal recipients")

    @staticmethod
    def _next_run(*, cadence: ScheduleCadence, now: datetime) -> datetime:
        if cadence == ScheduleCadence.DAILY:
            return now + timedelta(days=1)
        if cadence == ScheduleCadence.WEEKLY:
            return now + timedelta(days=7)
        return now + timedelta(days=30)


_scheduled_report_service = ScheduledReportService()


def get_scheduled_report_service() -> ScheduledReportService:
    return _scheduled_report_service


def reset_scheduled_report_service() -> None:
    _scheduled_report_service.reset()
