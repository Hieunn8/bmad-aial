"""Persistent document catalog store for RAG governance metadata."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Any

from aial_shared.auth.keycloak import JWTClaims

_TABLE_NAME = "aial_documents"
_INDEXED_STATUS = "indexed"


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_list(values: list[str]) -> list[str]:
    normalized: dict[str, str] = {}
    for value in values:
        text = value.strip()
        if not text:
            continue
        normalized[text.casefold()] = text
    return [normalized[key] for key in sorted(normalized)]


@dataclass(frozen=True)
class ManagedDocumentRecord:
    document_id: str
    filename: str
    source_url: str
    owner_department: str
    allowed_departments: tuple[str, ...]
    allowed_roles: tuple[str, ...]
    visibility: str
    classification: int
    source_trust: str
    effective_date: date
    chunk_count: int
    status: str
    uploaded_by: str
    indexed_at: datetime | None
    deleted_by: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "source_url": self.source_url,
            "owner_department": self.owner_department,
            "department": self.owner_department,
            "allowed_departments": list(self.allowed_departments),
            "allowed_roles": list(self.allowed_roles),
            "visibility": self.visibility,
            "classification": self.classification,
            "source_trust": self.source_trust,
            "effective_date": self.effective_date.isoformat(),
            "chunk_count": self.chunk_count,
            "status": self.status,
            "uploaded_by": self.uploaded_by,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "deleted_by": self.deleted_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class DocumentCatalogStore:
    def __init__(self, *, dsn: str | None) -> None:
        self._dsn = dsn.strip() if dsn else ""
        self._schema_ready = False
        self._memory_documents: dict[str, ManagedDocumentRecord] = {}

    def _connect(self) -> Any | None:
        if not self._dsn:
            return None
        import psycopg

        connection = psycopg.connect(self._dsn)
        if not self._schema_ready:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                    document_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    source_url TEXT NOT NULL,
                    owner_department TEXT NOT NULL,
                    allowed_departments_json JSONB NOT NULL,
                    allowed_roles_json JSONB NOT NULL,
                    visibility TEXT NOT NULL,
                    classification INTEGER NOT NULL,
                    source_trust TEXT NOT NULL,
                    effective_date DATE NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    indexed_at TIMESTAMPTZ NULL,
                    deleted_by TEXT NULL,
                    deleted_at TIMESTAMPTZ NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE_NAME}_status ON {_TABLE_NAME} (status)"
            )
            connection.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{_TABLE_NAME}_owner_department ON {_TABLE_NAME} (owner_department)"
            )
            connection.commit()
            self._schema_ready = True
        return connection

    @staticmethod
    def _row_to_record(row: Any) -> ManagedDocumentRecord:
        allowed_departments = row[4]
        if isinstance(allowed_departments, str):
            allowed_departments = json.loads(allowed_departments)
        allowed_roles = row[5]
        if isinstance(allowed_roles, str):
            allowed_roles = json.loads(allowed_roles)
        return ManagedDocumentRecord(
            document_id=str(row[0]),
            filename=str(row[1]),
            source_url=str(row[2]),
            owner_department=str(row[3]),
            allowed_departments=tuple(_normalize_list(list(allowed_departments))),
            allowed_roles=tuple(_normalize_list(list(allowed_roles))),
            visibility=str(row[6]),
            classification=int(row[7]),
            source_trust=str(row[8]),
            effective_date=row[9],
            chunk_count=int(row[10]),
            status=str(row[11]),
            uploaded_by=str(row[12]),
            indexed_at=row[13],
            deleted_by=str(row[14]) if row[14] is not None else None,
            deleted_at=row[15],
            created_at=row[16],
            updated_at=row[17],
        )

    def save_document(
        self,
        *,
        document_id: str,
        filename: str,
        source_url: str,
        owner_department: str,
        allowed_departments: list[str],
        allowed_roles: list[str],
        visibility: str,
        classification: int,
        source_trust: str,
        effective_date: date,
        chunk_count: int,
        status: str,
        uploaded_by: str,
        indexed_at: datetime | None,
    ) -> ManagedDocumentRecord:
        now = datetime.now(UTC)
        record = ManagedDocumentRecord(
            document_id=document_id,
            filename=_normalize_text(filename),
            source_url=_normalize_text(source_url),
            owner_department=_normalize_text(owner_department),
            allowed_departments=tuple(_normalize_list(allowed_departments)),
            allowed_roles=tuple(_normalize_list(allowed_roles)),
            visibility=_normalize_text(visibility),
            classification=classification,
            source_trust=_normalize_text(source_trust),
            effective_date=effective_date,
            chunk_count=chunk_count,
            status=_normalize_text(status),
            uploaded_by=_normalize_text(uploaded_by),
            indexed_at=indexed_at,
            deleted_by=None,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        connection = self._connect()
        if connection is None:
            self._memory_documents[document_id] = record
            return record
        try:
            connection.execute(
                f"""
                INSERT INTO {_TABLE_NAME} (
                    document_id, filename, source_url, owner_department,
                    allowed_departments_json, allowed_roles_json, visibility,
                    classification, source_trust, effective_date, chunk_count,
                    status, uploaded_by, indexed_at, deleted_by, deleted_at,
                    created_at, updated_at
                )
                VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (document_id) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    source_url = EXCLUDED.source_url,
                    owner_department = EXCLUDED.owner_department,
                    allowed_departments_json = EXCLUDED.allowed_departments_json,
                    allowed_roles_json = EXCLUDED.allowed_roles_json,
                    visibility = EXCLUDED.visibility,
                    classification = EXCLUDED.classification,
                    source_trust = EXCLUDED.source_trust,
                    effective_date = EXCLUDED.effective_date,
                    chunk_count = EXCLUDED.chunk_count,
                    status = EXCLUDED.status,
                    uploaded_by = EXCLUDED.uploaded_by,
                    indexed_at = EXCLUDED.indexed_at,
                    deleted_by = EXCLUDED.deleted_by,
                    deleted_at = EXCLUDED.deleted_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    record.document_id,
                    record.filename,
                    record.source_url,
                    record.owner_department,
                    json.dumps(list(record.allowed_departments)),
                    json.dumps(list(record.allowed_roles)),
                    record.visibility,
                    record.classification,
                    record.source_trust,
                    record.effective_date,
                    record.chunk_count,
                    record.status,
                    record.uploaded_by,
                    record.indexed_at,
                    record.deleted_by,
                    record.deleted_at,
                    record.created_at,
                    record.updated_at,
                ),
            )
            connection.commit()
            return record
        finally:
            connection.close()

    def list_documents(self) -> list[ManagedDocumentRecord]:
        connection = self._connect()
        if connection is None:
            return sorted(self._memory_documents.values(), key=lambda item: item.created_at, reverse=True)
        try:
            rows = connection.execute(
                f"""
                SELECT
                    document_id, filename, source_url, owner_department,
                    allowed_departments_json::text, allowed_roles_json::text, visibility,
                    classification, source_trust, effective_date, chunk_count,
                    status, uploaded_by, indexed_at, deleted_by, deleted_at,
                    created_at, updated_at
                FROM {_TABLE_NAME}
                ORDER BY created_at DESC, document_id DESC
                """
            ).fetchall()
            return [self._row_to_record(row) for row in rows]
        finally:
            connection.close()

    def get_document(self, document_id: str) -> ManagedDocumentRecord | None:
        connection = self._connect()
        if connection is None:
            return self._memory_documents.get(document_id)
        try:
            row = connection.execute(
                f"""
                SELECT
                    document_id, filename, source_url, owner_department,
                    allowed_departments_json::text, allowed_roles_json::text, visibility,
                    classification, source_trust, effective_date, chunk_count,
                    status, uploaded_by, indexed_at, deleted_by, deleted_at,
                    created_at, updated_at
                FROM {_TABLE_NAME}
                WHERE document_id = %s
                """,
                (document_id,),
            ).fetchone()
            return None if row is None else self._row_to_record(row)
        finally:
            connection.close()

    def update_document(
        self,
        document_id: str,
        *,
        owner_department: str | None = None,
        allowed_departments: list[str] | None = None,
        allowed_roles: list[str] | None = None,
        visibility: str | None = None,
        classification: int | None = None,
        source_trust: str | None = None,
        effective_date: date | None = None,
        status: str | None = None,
    ) -> ManagedDocumentRecord:
        current = self.get_document(document_id)
        if current is None:
            raise ValueError("document not found")
        next_record = ManagedDocumentRecord(
            document_id=current.document_id,
            filename=current.filename,
            source_url=current.source_url,
            owner_department=_normalize_text(owner_department) if owner_department is not None else current.owner_department,
            allowed_departments=tuple(_normalize_list(allowed_departments)) if allowed_departments is not None else current.allowed_departments,
            allowed_roles=tuple(_normalize_list(allowed_roles)) if allowed_roles is not None else current.allowed_roles,
            visibility=_normalize_text(visibility) if visibility is not None else current.visibility,
            classification=classification if classification is not None else current.classification,
            source_trust=_normalize_text(source_trust) if source_trust is not None else current.source_trust,
            effective_date=effective_date if effective_date is not None else current.effective_date,
            chunk_count=current.chunk_count,
            status=_normalize_text(status) if status is not None else current.status,
            uploaded_by=current.uploaded_by,
            indexed_at=current.indexed_at,
            deleted_by=current.deleted_by,
            deleted_at=current.deleted_at,
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
        )
        connection = self._connect()
        if connection is None:
            self._memory_documents[document_id] = next_record
            return next_record
        try:
            connection.execute(
                f"""
                UPDATE {_TABLE_NAME}
                SET
                    owner_department = %s,
                    allowed_departments_json = %s::jsonb,
                    allowed_roles_json = %s::jsonb,
                    visibility = %s,
                    classification = %s,
                    source_trust = %s,
                    effective_date = %s,
                    status = %s,
                    updated_at = %s
                WHERE document_id = %s
                """,
                (
                    next_record.owner_department,
                    json.dumps(list(next_record.allowed_departments)),
                    json.dumps(list(next_record.allowed_roles)),
                    next_record.visibility,
                    next_record.classification,
                    next_record.source_trust,
                    next_record.effective_date,
                    next_record.status,
                    next_record.updated_at,
                    document_id,
                ),
            )
            connection.commit()
            return next_record
        finally:
            connection.close()

    def soft_delete_document(self, document_id: str, *, deleted_by: str) -> ManagedDocumentRecord:
        current = self.get_document(document_id)
        if current is None:
            raise ValueError("document not found")
        next_record = ManagedDocumentRecord(
            document_id=current.document_id,
            filename=current.filename,
            source_url=current.source_url,
            owner_department=current.owner_department,
            allowed_departments=current.allowed_departments,
            allowed_roles=current.allowed_roles,
            visibility=current.visibility,
            classification=current.classification,
            source_trust=current.source_trust,
            effective_date=current.effective_date,
            chunk_count=current.chunk_count,
            status="deleted",
            uploaded_by=current.uploaded_by,
            indexed_at=current.indexed_at,
            deleted_by=deleted_by,
            deleted_at=datetime.now(UTC),
            created_at=current.created_at,
            updated_at=datetime.now(UTC),
        )
        connection = self._connect()
        if connection is None:
            self._memory_documents[document_id] = next_record
            return next_record
        try:
            connection.execute(
                f"""
                UPDATE {_TABLE_NAME}
                SET status = %s, deleted_by = %s, deleted_at = %s, updated_at = %s
                WHERE document_id = %s
                """,
                (
                    next_record.status,
                    next_record.deleted_by,
                    next_record.deleted_at,
                    next_record.updated_at,
                    document_id,
                ),
            )
            connection.commit()
            return next_record
        finally:
            connection.close()

    def filter_accessible_documents(self, document_ids: list[str], principal: JWTClaims) -> set[str]:
        unique_ids = sorted({document_id for document_id in document_ids if document_id})
        if not unique_ids:
            return set()
        records = self._load_documents_by_ids(unique_ids)
        return {
            record.document_id
            for record in records
            if self._can_access_document(record, principal)
        }

    def _load_documents_by_ids(self, document_ids: list[str]) -> list[ManagedDocumentRecord]:
        connection = self._connect()
        if connection is None:
            return [
                record
                for document_id in document_ids
                if (record := self._memory_documents.get(document_id)) is not None
            ]
        try:
            rows = connection.execute(
                f"""
                SELECT
                    document_id, filename, source_url, owner_department,
                    allowed_departments_json::text, allowed_roles_json::text, visibility,
                    classification, source_trust, effective_date, chunk_count,
                    status, uploaded_by, indexed_at, deleted_by, deleted_at,
                    created_at, updated_at
                FROM {_TABLE_NAME}
                WHERE document_id = ANY(%s)
                """,
                (document_ids,),
            ).fetchall()
            return [self._row_to_record(row) for row in rows]
        finally:
            connection.close()

    @staticmethod
    def _can_access_document(record: ManagedDocumentRecord, principal: JWTClaims) -> bool:
        if record.status != _INDEXED_STATUS:
            return False
        if record.classification > principal.clearance:
            return False
        allowed_roles = {role.casefold() for role in record.allowed_roles}
        if allowed_roles and not any(role.casefold() in allowed_roles for role in principal.roles):
            return False
        if record.visibility == "company-wide":
            return True
        allowed_departments = {department.casefold() for department in record.allowed_departments}
        return principal.department.casefold() in allowed_departments


@lru_cache(maxsize=1)
def get_document_catalog_store() -> DocumentCatalogStore:
    return DocumentCatalogStore(dsn=os.getenv("DATABASE_URL", ""))
