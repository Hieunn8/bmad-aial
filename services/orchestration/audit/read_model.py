"""Audit Read Model — Story 2B.5.

In-memory read model for compliance dashboard. Epic 5A replaces with
PostgreSQL-backed implementation using the append-only audit_events table.
"""

from __future__ import annotations

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


class AuditReadModel:
    def __init__(self) -> None:
        self._records: list[AuditRecord] = []

    def append(self, record: AuditRecord) -> None:
        self._records.append(record)

    def search(
        self,
        audit_filter: AuditFilter,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> list[AuditRecord]:
        results = list(self._records)

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
        if audit_filter.date_from:
            results = [r for r in results if r.timestamp >= audit_filter.date_from]
        if audit_filter.date_to:
            results = [r for r in results if r.timestamp <= audit_filter.date_to]

        results.sort(key=lambda r: r.timestamp, reverse=True)
        start = (page - 1) * page_size
        return results[start : start + page_size]

    def count(self, audit_filter: AuditFilter) -> int:
        return len(self.search(audit_filter, page=1, page_size=10_000))


# Module-level in-memory store (replaced by DB in Epic 5A)
_audit_read_model = AuditReadModel()


def get_audit_read_model() -> AuditReadModel:
    return _audit_read_model
