"""Query lifecycle audit logger — Story 2A.8.

Writes append-only audit events. Design rules:
  - Raw SQL text NEVER stored for PII_TIER_1/PII_TIER_2 queries.
  - Raw result values NEVER stored in any event.
  - sql_hash (SHA-256) always present when SQL was generated.
  - Denial events are logged even when no Oracle connection was opened.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

_SENSITIVE_TIERS = frozenset({"PII_TIER_1", "PII_TIER_2"})


@dataclass(frozen=True)
class AuditEvent:
    request_id: str
    user_id: str
    department_id: str
    session_id: str
    intent_type: str
    sensitivity_tier: str
    sql_text: str | None
    data_sources: list[str]
    rows_returned: int
    latency_ms: int
    policy_decision: str
    status: str
    denial_reason: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def sql_hash(self) -> str | None:
        if self.sql_text is None:
            return None
        return hashlib.sha256(self.sql_text.encode()).hexdigest()

    @property
    def stored_sql(self) -> str | None:
        if self.sensitivity_tier in _SENSITIVE_TIERS:
            return None
        return self.sql_text

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "intent_type": self.intent_type,
            "sensitivity_tier": self.sensitivity_tier,
            "sql_hash": self.sql_hash,
            "stored_sql": self.stored_sql,
            "data_sources": self.data_sources,
            "rows_returned": self.rows_returned,
            "latency_ms": self.latency_ms,
            "policy_decision": self.policy_decision,
            "status": self.status,
            "denial_reason": self.denial_reason,
        }


class AuditWriter(Protocol):
    def write(self, event_dict: dict[str, Any]) -> None: ...


class AuditLogger:
    def __init__(self, writer: AuditWriter) -> None:
        self._writer = writer

    def log(self, event: AuditEvent) -> None:
        self._writer.write(event.to_log_dict())
