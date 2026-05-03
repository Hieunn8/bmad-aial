"""Query Approval Workflow — Story 4.4 (FR-A7).

Lifecycle: ApprovalRequested → PendingReview → Approved | Rejected | Expired

Design constraints:
  - QueryIntent stores structured intent (NOT raw SQL).
  - Approved execution uses stored QueryIntent only — no user-modified SQL.
  - Expired does NOT auto-resubmit; analyst must explicitly create new request.
  - 4-hour SLA; both analyst and approver notified on expiry.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

_SLA_HOURS = 4


class ApprovalState(StrEnum):
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class QueryIntent:
    """Structured query intent — never stores raw SQL."""

    user_id: str
    department: str
    sensitivity_tier: int
    intent_type: str
    filters: dict[str, Any]
    estimated_row_count: int
    query_digest: str

    def fingerprint(self) -> str:
        canonical = json.dumps(
            {
                "user": self.user_id,
                "dept": self.department,
                "type": self.intent_type,
                "tier": self.sensitivity_tier,
                "filters": self.filters,
                "query_digest": self.query_digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


@dataclass
class ApprovalDecision:
    approver_id: str
    decision: str  # "approved" | "rejected"
    reason: str


@dataclass
class ApprovalRequest:
    request_id: str
    intent: QueryIntent
    state: ApprovalState
    created_at: datetime
    decided_at: datetime | None = None
    decision: ApprovalDecision | None = None
    query_fingerprint: str | None = None


class ApprovalStore:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def save(self, request: ApprovalRequest) -> None:
        self._requests[request.request_id] = request

    def get(self, request_id: str) -> ApprovalRequest | None:
        return self._requests.get(request_id)

    def decide(self, request_id: str, decision: ApprovalDecision) -> None:
        req = self._requests[request_id]
        new_state = ApprovalState.APPROVED if decision.decision == "approved" else ApprovalState.REJECTED
        self._requests[request_id] = ApprovalRequest(
            request_id=req.request_id,
            intent=req.intent,
            state=new_state,
            created_at=req.created_at,
            decided_at=datetime.now(UTC),
            decision=decision,
            query_fingerprint=req.query_fingerprint,
        )

    def expire(self, request_id: str) -> None:
        req = self._requests[request_id]
        self._requests[request_id] = ApprovalRequest(
            request_id=req.request_id,
            intent=req.intent,
            state=ApprovalState.EXPIRED,
            created_at=req.created_at,
            query_fingerprint=req.query_fingerprint,
        )

    def is_expired(self, request: ApprovalRequest) -> bool:
        return (datetime.now(UTC) - request.created_at) > timedelta(hours=_SLA_HOURS)


_approval_store = ApprovalStore()


def get_approval_store() -> ApprovalStore:
    return _approval_store


def create_approval_request(intent: QueryIntent, *, store: ApprovalStore) -> ApprovalRequest:
    request = ApprovalRequest(
        request_id=str(uuid.uuid4()),
        intent=intent,
        state=ApprovalState.APPROVAL_REQUESTED,
        created_at=datetime.now(UTC),
        query_fingerprint=intent.fingerprint(),
    )
    store.save(request)
    return request
