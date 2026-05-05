"""Document management routes with persisted access-scoped catalog records."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from rag.ingestion.chunker import DocumentChunker
from rag.ingestion.metadata import Classification, DocumentMetadata, validate_document_metadata
from rag.retrieval.weaviate_store import get_weaviate_document_store
from rag.tasks.ingest import enqueue_sync_index, get_job

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.logger import AuditLogger
from orchestration.audit.read_model import AuditRecord, get_audit_read_model
from orchestration.persistence.document_catalog_store import get_document_catalog_store

router = APIRouter(prefix="/v1/admin/documents")
CURRENT_USER_DEP = Depends(get_current_user)

_ADMIN_ROLES = frozenset({"admin", "data_owner"})
_VISIBILITY_VALUES = frozenset({"restricted", "company-wide"})
_chunker = DocumentChunker()


class _StdoutWriter:
    def write(self, d: dict[str, Any]) -> None:
        import logging

        logging.getLogger("audit").info("DOC_AUDIT %s", d)


_audit_logger = AuditLogger(writer=_StdoutWriter())


def _require_admin(principal: JWTClaims) -> None:
    if not (_ADMIN_ROLES & set(principal.roles)):
        raise HTTPException(
            status_code=403,
            detail="Document management requires admin or data_owner role",
        )


def _parse_classification(value: int) -> Classification | None:
    if value in Classification._value2member_map_:
        return Classification(value)
    return None


def _normalize_items(values: list[str]) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        text = value.strip()
        if not text:
            continue
        normalized[text.casefold()] = text
    return [normalized[key] for key in sorted(normalized)]


def _resolve_visibility(value: str) -> str | None:
    normalized = value.strip().lower()
    return normalized if normalized in _VISIBILITY_VALUES else None


def _resolve_owner_department(owner_department: str | None, department: str | None) -> str:
    return (owner_department or department or "").strip()


def _resolve_allowed_departments(owner_department: str, visibility: str, values: list[str]) -> list[str]:
    departments = _normalize_items(values)
    if visibility != "company-wide":
        known = {department.casefold() for department in departments}
        if owner_department and owner_department.casefold() not in known:
            departments.append(owner_department)
    return _normalize_items(departments)


class DocumentUploadRequest(BaseModel):
    filename: str
    content_text: str = ""
    source_url: str = ""
    owner_department: str = ""
    department: str | None = None
    allowed_departments: list[str] = Field(default_factory=list)
    allowed_roles: list[str] = Field(default_factory=list)
    visibility: str = "restricted"
    classification: int = 0
    source_trust: str = ""
    effective_date: str | None = None


@router.post("")
async def upload_document(
    body: DocumentUploadRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> JSONResponse:
    _require_admin(principal)

    try:
        eff_date = date.fromisoformat(body.effective_date) if body.effective_date else None
    except ValueError:
        return JSONResponse(status_code=400, content={"errors": ["effective_date: invalid ISO 8601 date"]})

    classification = _parse_classification(body.classification)
    if classification is None:
        return JSONResponse(
            status_code=400,
            content={
                "errors": [
                    f"classification: '{body.classification}' invalid "
                    "(0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=SECRET)"
                ]
            },
        )

    owner_department = _resolve_owner_department(body.owner_department, body.department)
    visibility = _resolve_visibility(body.visibility)
    if visibility is None:
        return JSONResponse(
            status_code=400,
            content={"errors": ["visibility: invalid (use restricted or company-wide)"]},
        )
    allowed_departments = _resolve_allowed_departments(
        owner_department,
        visibility,
        body.allowed_departments,
    )
    allowed_roles = _normalize_items(body.allowed_roles)

    meta = DocumentMetadata(
        document_id="",
        department=owner_department,
        classification=classification,
        source_trust=body.source_trust,
        effective_date=eff_date,
    )
    errors = validate_document_metadata(meta)
    if errors:
        return JSONResponse(status_code=400, content={"errors": errors})

    document_id = str(uuid.uuid4())
    meta = DocumentMetadata(
        document_id=document_id,
        department=owner_department,
        classification=classification,
        source_trust=body.source_trust,
        effective_date=eff_date,
    )
    chunks = _chunker.chunk_text(body.content_text, document_id=document_id, metadata=meta)
    if not chunks:
        return JSONResponse(status_code=400, content={"errors": ["content_text: required, must not be empty"]})

    try:
        indexed = await get_weaviate_document_store().index_document(
            document_id=document_id,
            filename=body.filename,
            source_url=body.source_url,
            uploaded_by=principal.sub,
            chunks=chunks,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={"detail": f"Failed to index document into Weaviate: {exc}"},
        )

    job = enqueue_sync_index(document_id, [chunk.chunk_text for chunk in chunks])
    record = get_document_catalog_store().save_document(
        document_id=document_id,
        filename=body.filename,
        source_url=body.source_url,
        owner_department=owner_department,
        allowed_departments=allowed_departments,
        allowed_roles=allowed_roles,
        visibility=visibility,
        classification=body.classification,
        source_trust=body.source_trust,
        effective_date=eff_date,
        chunk_count=indexed.chunk_count,
        status=job.status.value,
        uploaded_by=principal.sub,
        indexed_at=datetime.fromisoformat(indexed.indexed_at),
    )

    _audit_document_event(principal, document_id, action="upload", department=owner_department)
    return JSONResponse(
        status_code=202,
        content={
            "document_id": document_id,
            "status": record.status,
            "chunk_count": record.chunk_count,
            "message": "Document indexed into Weaviate",
        },
    )


@router.get("")
async def list_documents(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    records = [record.to_dict() for record in get_document_catalog_store().list_documents()]
    return {"documents": records, "total": len(records)}


@router.get("/{document_id}")
async def get_document(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    _require_admin(principal)
    doc = get_document_catalog_store().get_document(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    return JSONResponse(content=doc.to_dict())


@router.patch("/{document_id}")
async def update_document_metadata(
    document_id: str,
    body: dict[str, Any],
    principal: JWTClaims = CURRENT_USER_DEP,
) -> JSONResponse:
    _require_admin(principal)
    existing = get_document_catalog_store().get_document(document_id)
    if existing is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})

    classification = None
    if "classification" in body:
        parsed = _parse_classification(int(body["classification"]))
        if parsed is None:
            return JSONResponse(status_code=400, content={"errors": ["classification: invalid"]})
        classification = int(parsed)

    eff_date = None
    if "effective_date" in body and body["effective_date"] is not None:
        try:
            eff_date = date.fromisoformat(str(body["effective_date"]))
        except ValueError:
            return JSONResponse(status_code=400, content={"errors": ["effective_date: invalid ISO 8601 date"]})

    owner_department = _resolve_owner_department(
        str(body.get("owner_department", "")) if body.get("owner_department") is not None else None,
        str(body.get("department", "")) if body.get("department") is not None else None,
    ) or existing.owner_department
    visibility = existing.visibility
    if "visibility" in body:
        next_visibility = _resolve_visibility(str(body["visibility"]))
        if next_visibility is None:
            return JSONResponse(
                status_code=400,
                content={"errors": ["visibility: invalid (use restricted or company-wide)"]},
            )
        visibility = next_visibility

    allowed_departments = None
    if "allowed_departments" in body:
        raw_allowed_departments = [str(value) for value in body.get("allowed_departments", [])]
        allowed_departments = _resolve_allowed_departments(owner_department, visibility, raw_allowed_departments)

    allowed_roles = None
    if "allowed_roles" in body:
        allowed_roles = _normalize_items([str(value) for value in body.get("allowed_roles", [])])

    updated = get_document_catalog_store().update_document(
        document_id,
        owner_department=owner_department,
        allowed_departments=allowed_departments,
        allowed_roles=allowed_roles,
        visibility=visibility,
        classification=classification,
        source_trust=str(body["source_trust"]) if "source_trust" in body else None,
        effective_date=eff_date,
        status=str(body["status"]) if "status" in body else None,
    )
    _audit_document_event(principal, document_id, action="metadata_update", department=updated.owner_department)
    return JSONResponse(content={"document_id": document_id, "status": "updated"})


@router.delete("/{document_id}")
async def delete_document(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    _require_admin(principal)
    try:
        deleted = get_document_catalog_store().soft_delete_document(document_id, deleted_by=principal.sub)
    except ValueError:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    _audit_document_event(principal, document_id, action="delete", department=deleted.owner_department)
    return JSONResponse(content={"document_id": document_id, "status": "deleted"})


@router.get("/{document_id}/reindex-status")
async def reindex_status(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    _require_admin(principal)
    doc = get_document_catalog_store().get_document(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    job = get_job(document_id)
    if job:
        return JSONResponse(
            content={
                "document_id": document_id,
                "status": job.status.value,
                "progress_percent": job.progress_percent,
                "processed_chunks": job.processed_chunks,
                "failed_chunks": job.failed_chunks,
            }
        )
    return JSONResponse(
        content={
            "document_id": document_id,
            "status": doc.status,
            "progress_percent": 100 if doc.status == "indexed" else 0,
            "processed_chunks": doc.chunk_count,
            "failed_chunks": 0,
        }
    )


def _audit_document_event(principal: JWTClaims, document_id: str, *, action: str, department: str) -> None:
    model = get_audit_read_model()
    import uuid as _uuid

    model.append(
        AuditRecord(
            request_id=str(_uuid.uuid4()),
            user_id=principal.sub,
            department_id=department,
            session_id="admin-session",
            timestamp=datetime.now(UTC),
            intent_type=f"doc:{action}",
            sensitivity_tier="LOW",
            sql_hash=None,
            data_sources=[document_id],
            rows_returned=0,
            latency_ms=0,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
    )
