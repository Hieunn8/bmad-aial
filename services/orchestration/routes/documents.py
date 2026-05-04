"""Document management routes — Epic 3 (Stories 3.1, 3.4, 3.5).

Authorization invariant (FR-R5):
  ALL routes require admin or data_owner role.
  Regular chat users (roles=["user"]) are denied with 403.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from rag.ingestion.chunker import DocumentChunker
from rag.ingestion.metadata import Classification, DocumentMetadata, validate_document_metadata
from rag.retrieval.weaviate_store import get_weaviate_document_store
from rag.tasks.ingest import enqueue_sync_index, get_job

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.logger import AuditLogger
from orchestration.audit.read_model import AuditRecord, get_audit_read_model

router = APIRouter(prefix="/v1/admin/documents")
CURRENT_USER_DEP = Depends(get_current_user)

_ADMIN_ROLES = frozenset({"admin", "data_owner"})
_chunker = DocumentChunker()
_documents: dict[str, dict[str, Any]] = {}


class _StdoutWriter:
    def write(self, d: dict[str, Any]) -> None:
        import logging
        logging.getLogger("audit").info("DOC_AUDIT %s", d)


_audit_logger = AuditLogger(writer=_StdoutWriter())


def _require_admin(principal: JWTClaims) -> None:
    """Raise 403 if principal does not hold admin or data_owner role (FR-R5)."""
    if not (_ADMIN_ROLES & set(principal.roles)):
        raise HTTPException(
            status_code=403,
            detail="Document management requires admin or data_owner role",
        )


def _parse_classification(value: int) -> Classification | None:
    """Return Classification enum or None for unknown values."""
    if value in Classification._value2member_map_:
        return Classification(value)
    return None


class DocumentUploadRequest(BaseModel):
    filename: str
    content_text: str = ""
    source_url: str = ""
    department: str = ""
    classification: int = 0
    source_trust: str = ""
    effective_date: str | None = None


@router.post("")
async def upload_document(
    body: DocumentUploadRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> JSONResponse:
    """Accept document upload, validate metadata, enqueue ingestion task."""
    _require_admin(principal)

    try:
        eff_date = date.fromisoformat(body.effective_date) if body.effective_date else None
    except ValueError:
        return JSONResponse(status_code=400, content={"errors": ["effective_date: invalid ISO 8601 date"]})

    # Validate classification before first use — fail with 400, not 500
    classification = _parse_classification(body.classification)
    if classification is None:
        return JSONResponse(
            status_code=400,
            content={"errors": [
                f"classification: '{body.classification}' invalid "
                "(0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=SECRET)"
            ]},
        )

    meta = DocumentMetadata(
        document_id="",
        department=body.department,
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
        department=body.department,
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

    # Preserve the existing job contract while doing real synchronous indexing.
    job = enqueue_sync_index(document_id, [chunk.chunk_text for chunk in chunks])

    _documents[document_id] = {
        "document_id": document_id,
        "filename": body.filename,
        "source_url": body.source_url,
        "department": body.department,
        "classification": body.classification,
        "source_trust": body.source_trust,
        "effective_date": body.effective_date,
        "chunk_count": indexed.chunk_count,
        "status": job.status.value,
        "uploaded_by": principal.sub,
        "indexed_at": indexed.indexed_at,
    }

    # Audit: document uploaded
    _audit_document_event(principal, document_id, action="upload", department=body.department)

    return JSONResponse(status_code=202, content={
        "document_id": document_id,
        "status": job.status.value,
        "chunk_count": indexed.chunk_count,
        "message": "Document indexed into Weaviate",
    })


@router.get("")
async def list_documents(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    _require_admin(principal)
    return {"documents": list(_documents.values()), "total": len(_documents)}


@router.get("/{document_id}")
async def get_document(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    _require_admin(principal)
    doc = _documents.get(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    return JSONResponse(content=doc)


@router.patch("/{document_id}")
async def update_document_metadata(
    document_id: str,
    body: dict[str, Any],
    principal: JWTClaims = CURRENT_USER_DEP,
) -> JSONResponse:
    """Atomic metadata update (Story 3.5). Real impl: Weaviate batch + PostgreSQL in transaction."""
    _require_admin(principal)
    doc = _documents.get(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    allowed_fields = {"department", "classification", "source_trust", "effective_date", "status"}
    updates = {k: v for k, v in body.items() if k in allowed_fields}
    _documents[document_id] = {**doc, **updates}
    _audit_document_event(principal, document_id, action="metadata_update", department=doc.get("department", ""))
    return JSONResponse(content={"document_id": document_id, "status": "updated"})


@router.delete("/{document_id}")
async def delete_document(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    """Soft-delete — retains audit trail (Story 3.5)."""
    _require_admin(principal)
    doc = _documents.get(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    _documents[document_id] = {**doc, "status": "deleted", "deleted_by": principal.sub}
    _audit_document_event(principal, document_id, action="delete", department=doc.get("department", ""))
    return JSONResponse(content={"document_id": document_id, "status": "deleted"})


@router.get("/{document_id}/reindex-status")
async def reindex_status(document_id: str, principal: JWTClaims = CURRENT_USER_DEP) -> JSONResponse:
    """Re-index progress polling every 5s (Story 3.5 AC)."""
    _require_admin(principal)
    doc = _documents.get(document_id)
    if doc is None:
        return JSONResponse(status_code=404, content={"detail": "Document not found"})
    job = get_job(document_id)
    if job:
        return JSONResponse(content={
            "document_id": document_id,
            "status": job.status.value,
            "progress_percent": job.progress_percent,
            "processed_chunks": job.processed_chunks,
            "failed_chunks": job.failed_chunks,
        })
    return JSONResponse(content={
        "document_id": document_id,
        "status": doc.get("status", "unknown"),
        "progress_percent": 100 if doc.get("status") == "indexed" else 0,
        "processed_chunks": doc.get("chunk_count", 0),
        "failed_chunks": 0,
    })


def _audit_document_event(principal: JWTClaims, document_id: str, *, action: str, department: str) -> None:
    """Append a document operation audit record (Story 3.5: all admin ops logged)."""
    model = get_audit_read_model()
    import uuid as _uuid
    model.append(AuditRecord(
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
    ))
