"""Tests for Story 4.4 - Query Approval Workflow (FR-A7)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest

from orchestration.approval.workflow import (
    ApprovalDecision,
    ApprovalState,
    ApprovalStore,
    QueryIntent,
    create_approval_request,
)


@pytest.fixture()
def store() -> ApprovalStore:
    return ApprovalStore()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class TestQueryIntent:
    def test_stores_structured_intent_not_raw_sql(self) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="aggregation",
            filters={"year": 2024, "dept": "sales"},
            estimated_row_count=500,
            query_digest=_digest("aggregation:sales:2024"),
        )
        assert intent.sensitivity_tier == 2
        assert "raw_sql" not in intent.__dict__


class TestApprovalWorkflow:
    def test_creates_request_in_approval_requested_state(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="query",
            filters={},
            estimated_row_count=100,
            query_digest=_digest("query-1"),
        )
        req = create_approval_request(intent, store=store)
        assert req.state == ApprovalState.APPROVAL_REQUESTED
        assert req.request_id is not None

    def test_approve_transitions_to_approved(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="query",
            filters={},
            estimated_row_count=100,
            query_digest=_digest("query-2"),
        )
        req = create_approval_request(intent, store=store)
        store.decide(
            req.request_id,
            ApprovalDecision(approver_id="approver-1", decision="approved", reason="Business justified"),
        )
        updated = store.get(req.request_id)
        assert updated.state == ApprovalState.APPROVED

    def test_reject_transitions_to_rejected(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="query",
            filters={},
            estimated_row_count=100,
            query_digest=_digest("query-3"),
        )
        req = create_approval_request(intent, store=store)
        store.decide(
            req.request_id,
            ApprovalDecision(approver_id="approver-1", decision="rejected", reason="Not justified"),
        )
        assert store.get(req.request_id).state == ApprovalState.REJECTED

    def test_expired_after_sla(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="query",
            filters={},
            estimated_row_count=100,
            query_digest=_digest("query-4"),
        )
        req = create_approval_request(intent, store=store)
        req.created_at = datetime.now(UTC) - timedelta(hours=5)
        assert store.is_expired(req)

    def test_expired_request_does_not_auto_resubmit(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="query",
            filters={},
            estimated_row_count=100,
            query_digest=_digest("query-5"),
        )
        req = create_approval_request(intent, store=store)
        req.created_at = datetime.now(UTC) - timedelta(hours=5)
        store.expire(req.request_id)
        assert store.get(req.request_id).state == ApprovalState.EXPIRED
        new_req = create_approval_request(intent, store=store)
        assert new_req.request_id != req.request_id

    def test_approval_stores_fingerprint_not_raw_sql(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="finance",
            sensitivity_tier=3,
            intent_type="detail_query",
            filters={"year": 2024},
            estimated_row_count=50,
            query_digest=_digest("detail-query-2024"),
        )
        req = create_approval_request(intent, store=store)
        store.decide(req.request_id, ApprovalDecision(approver_id="appr-1", decision="approved", reason="ok"))
        record = store.get(req.request_id)
        assert record.query_fingerprint is not None
        assert "raw_sql" not in str(record.__dict__)

    def test_distinct_query_digests_produce_distinct_fingerprints(self) -> None:
        left = QueryIntent(
            user_id="user-1",
            department="finance",
            sensitivity_tier=3,
            intent_type="detail_query",
            filters={"query_preview": "same first 80 chars"},
            estimated_row_count=50,
            query_digest=_digest("query-left"),
        )
        right = QueryIntent(
            user_id="user-1",
            department="finance",
            sensitivity_tier=3,
            intent_type="detail_query",
            filters={"query_preview": "same first 80 chars"},
            estimated_row_count=50,
            query_digest=_digest("query-right"),
        )
        assert left.fingerprint() != right.fingerprint()
