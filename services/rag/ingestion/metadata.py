"""Document metadata contract — Stories 3.1 + 3.4.

Every document MUST supply these four fields before ingestion.
Missing or empty fields → HTTP 400, no Celery task enqueued, no Weaviate write.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import IntEnum


class Classification(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3


@dataclass
class DocumentMetadata:
    document_id: str
    department: str
    classification: Classification
    source_trust: str
    effective_date: date | None


def validate_document_metadata(meta: DocumentMetadata) -> list[str]:
    """Return list of field-level error strings. Empty list = valid."""
    errors: list[str] = []
    if not meta.department or not meta.department.strip():
        errors.append("department: required, must not be empty")
    if meta.source_trust is None or not str(meta.source_trust).strip():
        errors.append("source_trust: required, must not be empty")
    if meta.effective_date is None:
        errors.append("effective_date: required, must be a valid ISO 8601 date")
    return errors


def is_stale(effective_date: date, *, threshold_days: int = 180) -> bool:
    """Return True if the document is older than threshold (exclusive boundary)."""
    from datetime import date as date_cls
    today = date_cls.today()
    age_days = (today - effective_date).days
    return age_days > threshold_days
