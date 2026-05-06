"""Audit Read Model — Story 2B.5.

In-memory read model for compliance dashboard. Epic 5A replaces with
PostgreSQL-backed implementation using the append-only audit_events table.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

_SENSITIVE_TIERS = frozenset({"PII_TIER_1", "PII_TIER_2"})


@dataclass(frozen=True)
class AuditRecord:
    request_id: str
    user_id: str
    department_id: str
    session_id: str
    timestamp: datetime
    intent_type: str
    sensitivity_tier: str
    sql_hash: str | None
    data_sources: list[str]
    rows_returned: int
    latency_ms: int
    policy_decision: str
    status: str
    denial_reason: str | None = None
    stored_sql: str | None = None
    cerbos_rule: str | None = None
    metadata: dict[str, Any] | None = None

    def to_response_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "intent_type": self.intent_type,
            "sensitivity_tier": self.sensitivity_tier,
            "sql_hash": self.sql_hash,
            "stored_sql": None if self.sensitivity_tier in _SENSITIVE_TIERS else self.stored_sql,
            "data_sources": self.data_sources,
            "rows_returned": self.rows_returned,
            "latency_ms": self.latency_ms,
            "policy_decision": self.policy_decision,
            "status": self.status,
            "denial_reason": self.denial_reason,
            "cerbos_rule": self.cerbos_rule,
            "metadata": self.metadata or {},
        }


@dataclass
class AuditFilter:
    user_id: str | None = None
    department_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    policy_decision: str | None = None
    status: str | None = None
    request_id: str | None = None
    action: str | None = None
    data_source: str | None = None


class AuditReadModel:
    def __init__(self, *, dsn: str | None = None) -> None:
        self._records: list[AuditRecord] = []
        self._dsn = dsn.strip() if dsn else ""
        self._schema_ready = False

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)
        self._persist(record)

    def search(
        self,
        audit_filter: AuditFilter,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditRecord]:
        results = self.search_all(audit_filter)
        results.sort(key=lambda r: r.timestamp, reverse=True)
        start = (page - 1) * page_size
        return results[start : start + page_size]

    def count(self, audit_filter: AuditFilter) -> int:
        return len(self.search_all(audit_filter))

    def search_all(self, audit_filter: AuditFilter) -> list[AuditRecord]:
        results = self._load_records()

        if audit_filter.request_id:
            results = [r for r in results if r.request_id == audit_filter.request_id]
        if audit_filter.user_id:
            results = [r for r in results if r.user_id == audit_filter.user_id]
        if audit_filter.department_id:
            results = [r for r in results if r.department_id == audit_filter.department_id]
        if audit_filter.policy_decision:
            results = [r for r in results if r.policy_decision == audit_filter.policy_decision]
        if audit_filter.status:
            results = [r for r in results if r.status == audit_filter.status]
        if audit_filter.action:
            results = [r for r in results if r.intent_type == audit_filter.action]
        if audit_filter.data_source:
            results = [r for r in results if audit_filter.data_source in r.data_sources]
        if audit_filter.date_from:
            results = [r for r in results if r.timestamp >= audit_filter.date_from]
        if audit_filter.date_to:
            results = [r for r in results if r.timestamp <= audit_filter.date_to]
        return results

    def _connect(self) -> Any | None:
        if not self._dsn:
            return None
        import psycopg

        connection = psycopg.connect(self._dsn)
        if not self._schema_ready:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS aial_audit_records (
                    request_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    department_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    payload JSONB NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_aial_audit_records_user_time ON aial_audit_records (user_id, timestamp DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_aial_audit_records_department_time ON aial_audit_records (department_id, timestamp DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_aial_audit_records_request ON aial_audit_records (request_id)"
            )
            connection.commit()
            self._schema_ready = True
        return connection

    def _persist(self, record: AuditRecord) -> None:
        connection = self._connect()
        if connection is None:
            return
        try:
            connection.execute(
                """
                INSERT INTO aial_audit_records (request_id, user_id, department_id, session_id, timestamp, payload)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    record.request_id,
                    record.user_id,
                    record.department_id,
                    record.session_id,
                    record.timestamp,
                    json.dumps(_record_to_payload(record)),
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _load_records(self) -> list[AuditRecord]:
        connection = self._connect()
        if connection is None:
            return list(self._records)
        try:
            rows = connection.execute("SELECT payload FROM aial_audit_records").fetchall()
            return [_record_from_payload(dict(row[0])) for row in rows]
        finally:
            connection.close()


def _record_to_payload(record: AuditRecord) -> dict[str, Any]:
    payload = record.to_response_dict()
    payload["stored_sql"] = record.stored_sql
    return payload


def _record_from_payload(payload: dict[str, Any]) -> AuditRecord:
    return AuditRecord(
        request_id=str(payload["request_id"]),
        user_id=str(payload["user_id"]),
        department_id=str(payload["department_id"]),
        session_id=str(payload["session_id"]),
        timestamp=datetime.fromisoformat(str(payload["timestamp"])),
        intent_type=str(payload["intent_type"]),
        sensitivity_tier=str(payload["sensitivity_tier"]),
        sql_hash=str(payload["sql_hash"]) if payload.get("sql_hash") is not None else None,
        data_sources=[str(item) for item in payload.get("data_sources", [])],
        rows_returned=int(payload["rows_returned"]),
        latency_ms=int(payload["latency_ms"]),
        policy_decision=str(payload["policy_decision"]),
        status=str(payload["status"]),
        denial_reason=str(payload["denial_reason"]) if payload.get("denial_reason") is not None else None,
        stored_sql=str(payload["stored_sql"]) if payload.get("stored_sql") is not None else None,
        cerbos_rule=str(payload["cerbos_rule"]) if payload.get("cerbos_rule") is not None else None,
        metadata=dict(payload.get("metadata", {})),
    )


_audit_read_model = AuditReadModel(dsn=os.getenv("DATABASE_URL", ""))


def get_audit_read_model() -> AuditReadModel:
    return _audit_read_model
