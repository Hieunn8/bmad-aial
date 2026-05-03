"""Export job service — Epic 6 Story 6.1.

Invariants:
  - Exports operate only on already-secured query rows stored for the owning user.
  - Audit logs store export metadata only; raw exported values are never copied into audit.
  - Download links expire after 24 hours.
"""

from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4
from xml.sax.saxutils import escape

from fastapi import HTTPException

from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditRecord, get_audit_read_model


class ExportFormat(StrEnum):
    CSV = "csv"
    XLSX = "xlsx"
    PDF = "pdf"


class ExportJobStatus(StrEnum):
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class ExportArtifact:
    request_id: str
    owner_user_id: str
    department_scope: str
    sensitivity_tier: int
    rows: list[dict[str, Any]]
    trace_id: str
    data_source: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class ExportJob:
    job_id: str
    request_id: str
    owner_user_id: str
    department_scope: str
    sensitivity_tier: int
    format: ExportFormat
    row_count: int
    recipient: str | None
    status: ExportJobStatus = ExportJobStatus.QUEUED
    queue_name: str = "export-jobs"
    task_name: str = "export.report.generate_csv"
    acks_late: bool = True
    reject_on_worker_lost: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    error: str | None = None
    media_type: str | None = None
    filename: str | None = None
    download_bytes: bytes | None = None
    download_path: str | None = None


class ExportService:
    def __init__(self) -> None:
        self._artifacts: dict[str, ExportArtifact] = {}
        self._jobs: dict[str, ExportJob] = {}

    def register_query_result(
        self,
        *,
        request_id: str,
        owner_user_id: str,
        department_scope: str,
        sensitivity_tier: int,
        rows: list[dict[str, Any]],
        trace_id: str,
        data_source: str | None,
    ) -> None:
        self._artifacts[request_id] = ExportArtifact(
            request_id=request_id,
            owner_user_id=owner_user_id,
            department_scope=department_scope,
            sensitivity_tier=sensitivity_tier,
            rows=[dict(row) for row in rows],
            trace_id=trace_id,
            data_source=data_source,
        )

    def get_preview(self, *, request_id: str, principal: JWTClaims, export_format: ExportFormat) -> dict[str, Any]:
        artifact = self._get_owned_artifact(request_id=request_id, principal=principal)
        return {
            "request_id": artifact.request_id,
            "format": export_format.value,
            "estimated_row_count": len(artifact.rows),
            "sensitivity_tier": artifact.sensitivity_tier,
            "sensitivity_warning": self._build_sensitivity_warning(artifact.sensitivity_tier),
            "department_scope": artifact.department_scope,
        }

    def enqueue_job(
        self,
        *,
        request_id: str,
        principal: JWTClaims,
        export_format: ExportFormat,
        recipient: str | None,
    ) -> ExportJob:
        artifact = self._get_owned_artifact(request_id=request_id, principal=principal)
        job_id = str(uuid4())
        job = ExportJob(
            job_id=job_id,
            request_id=request_id,
            owner_user_id=principal.sub,
            department_scope=artifact.department_scope,
            sensitivity_tier=artifact.sensitivity_tier,
            format=export_format,
            row_count=len(artifact.rows),
            recipient=recipient,
            task_name=self._task_name_for_format(export_format),
        )
        self._jobs[job_id] = job
        return job

    def process_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if job is None or job.status != ExportJobStatus.QUEUED:
            return

        artifact = self._artifacts.get(job.request_id)
        if artifact is None:
            job.status = ExportJobStatus.FAILED
            job.error = "Source query result is no longer available"
            return

        try:
            payload, media_type, filename = self._render_export(
                rows=artifact.rows,
                export_format=job.format,
                trace_id=artifact.trace_id,
            )
        except Exception as exc:
            job.status = ExportJobStatus.FAILED
            job.error = str(exc)
            return

        job.status = ExportJobStatus.COMPLETED
        job.expires_at = datetime.now(UTC) + timedelta(hours=24)
        job.media_type = media_type
        job.filename = filename
        job.download_bytes = payload
        job.download_path = f"/v1/chat/exports/{job.job_id}/download"
        self._append_audit_record(job=job, artifact=artifact)

    def get_job(self, *, job_id: str, principal: JWTClaims) -> ExportJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Export job not found")
        if job.owner_user_id != principal.sub:
            raise HTTPException(status_code=403, detail="Export job does not belong to this user")
        if job.expires_at and datetime.now(UTC) > job.expires_at and job.status == ExportJobStatus.COMPLETED:
            job.status = ExportJobStatus.EXPIRED
            job.download_bytes = None
            job.download_path = None
        return job

    def get_download(self, *, job_id: str, principal: JWTClaims) -> tuple[bytes, str, str]:
        job = self.get_job(job_id=job_id, principal=principal)
        if job.status == ExportJobStatus.EXPIRED:
            raise HTTPException(status_code=410, detail="Download link has expired")
        if job.status != ExportJobStatus.COMPLETED or not job.download_bytes or not job.media_type or not job.filename:
            raise HTTPException(status_code=409, detail="Export file is not ready")
        return job.download_bytes, job.media_type, job.filename

    def reset(self) -> None:
        self._artifacts.clear()
        self._jobs.clear()

    def _get_owned_artifact(self, *, request_id: str, principal: JWTClaims) -> ExportArtifact:
        artifact = self._artifacts.get(request_id)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Export source result not found")
        if artifact.owner_user_id != principal.sub:
            raise HTTPException(status_code=403, detail="Export source does not belong to this user")
        return artifact

    @staticmethod
    def _build_sensitivity_warning(sensitivity_tier: int) -> str | None:
        if sensitivity_tier >= 2:
            return f"Kết quả có sensitivity tier {sensitivity_tier}; kiểm tra kỹ trước khi chia sẻ."
        return None

    @staticmethod
    def _task_name_for_format(export_format: ExportFormat) -> str:
        if export_format == ExportFormat.XLSX:
            return "export.report.generate_excel"
        if export_format == ExportFormat.PDF:
            return "export.report.generate_pdf"
        return "export.report.generate_csv"

    def _append_audit_record(self, *, job: ExportJob, artifact: ExportArtifact) -> None:
        get_audit_read_model().append(
            AuditRecord(
                request_id=job.request_id,
                user_id=job.owner_user_id,
                department_id=job.department_scope,
                session_id=job.job_id,
                timestamp=datetime.now(UTC),
                intent_type="export:generate",
                sensitivity_tier=f"TIER_{job.sensitivity_tier}",
                sql_hash=None,
                data_sources=[artifact.data_source] if artifact.data_source else [],
                rows_returned=job.row_count,
                latency_ms=0,
                policy_decision="ALLOW",
                status="SUCCESS",
                metadata={
                    "job_id": job.job_id,
                    "format": job.format.value,
                    "row_count": job.row_count,
                    "department_scope": job.department_scope,
                    "sensitivity_tier": job.sensitivity_tier,
                    "recipient": job.recipient,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "download_expires_at": job.expires_at.isoformat() if job.expires_at else None,
                },
            )
        )

    def _render_export(
        self,
        *,
        rows: list[dict[str, Any]],
        export_format: ExportFormat,
        trace_id: str,
    ) -> tuple[bytes, str, str]:
        if export_format == ExportFormat.CSV:
            return self._render_csv(rows), "text/csv", f"aial-export-{trace_id[:8]}.csv"
        if export_format == ExportFormat.XLSX:
            return self._render_xlsx(rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"aial-export-{trace_id[:8]}.xlsx"
        return self._render_pdf(rows), "application/pdf", f"aial-export-{trace_id[:8]}.pdf"

    @staticmethod
    def _headers_for_rows(rows: list[dict[str, Any]]) -> list[str]:
        if not rows:
            return ["result"]
        seen: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.append(key)
        return seen

    def _render_csv(self, rows: list[dict[str, Any]]) -> bytes:
        output = io.StringIO()
        headers = self._headers_for_rows(rows)
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})
        return output.getvalue().encode("utf-8")

    def _render_xlsx(self, rows: list[dict[str, Any]]) -> bytes:
        headers = self._headers_for_rows(rows)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_rels_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml())
            archive.writestr("xl/worksheets/sheet1.xml", self._worksheet_xml(headers=headers, rows=rows))
        return buffer.getvalue()

    def _render_pdf(self, rows: list[dict[str, Any]]) -> bytes:
        headers = self._headers_for_rows(rows)
        lines = ["AIAL Export Report", "", " | ".join(headers)]
        for row in rows:
            lines.append(" | ".join(str(row.get(header, "")) for header in headers))
        return self._build_simple_pdf(lines[:120])

    @staticmethod
    def _content_types_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        )

    @staticmethod
    def _root_rels_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    @staticmethod
    def _workbook_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Results" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        )

    @staticmethod
    def _workbook_rels_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            "</Relationships>"
        )

    def _worksheet_xml(self, *, headers: list[str], rows: list[dict[str, Any]]) -> str:
        row_xml: list[str] = []
        all_rows = [{header: header for header in headers}, *rows]
        for row_index, row in enumerate(all_rows, start=1):
            cells: list[str] = []
            for column_index, header in enumerate(headers, start=1):
                cell_ref = f"{self._excel_column_name(column_index)}{row_index}"
                value = row.get(header, "")
                cells.append(self._excel_cell_xml(cell_ref=cell_ref, value=value))
            row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(row_xml)}</sheetData>'
            "</worksheet>"
        )

    @staticmethod
    def _excel_cell_xml(*, cell_ref: str, value: Any) -> str:
        if isinstance(value, bool):
            return f'<c r="{cell_ref}" t="b"><v>{1 if value else 0}</v></c>'
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{cell_ref}"><v>{value}</v></c>'
        text = escape(str(value))
        return f'<c r="{cell_ref}" t="inlineStr"><is><t>{text}</t></is></c>'

    @staticmethod
    def _excel_column_name(index: int) -> str:
        name = ""
        current = index
        while current > 0:
            current, remainder = divmod(current - 1, 26)
            name = chr(65 + remainder) + name
        return name

    @staticmethod
    def _build_simple_pdf(lines: list[str]) -> bytes:
        escaped_lines = [
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            for line in lines
        ]
        content = "BT /F1 10 Tf 50 790 Td 12 TL " + " ".join(f"({line}) Tj T*" for line in escaped_lines) + " ET"
        objects = [
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj",
            b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj",
            b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj",
            b"4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj",
            f"5 0 obj << /Length {len(content.encode('latin-1', errors='replace'))} >> stream\n{content}\nendstream endobj".encode("latin-1", errors="replace"),
        ]
        output = io.BytesIO()
        output.write(b"%PDF-1.4\n")
        offsets: list[int] = [0]
        for obj in objects:
            offsets.append(output.tell())
            output.write(obj + b"\n")
        xref_start = output.tell()
        output.write(f"xref\n0 {len(objects) + 1}\n".encode())
        output.write(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            output.write(f"{offset:010d} 00000 n \n".encode())
        output.write(
            (
                f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
                f"startxref\n{xref_start}\n%%EOF"
            ).encode()
        )
        return output.getvalue()


_export_service = ExportService()


def get_export_service() -> ExportService:
    return _export_service


def reset_export_service() -> None:
    _export_service.reset()
