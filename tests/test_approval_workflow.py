"""Tests for Story 4.4 — Query Approval Workflow (FR-A7)."""

from __future__ import annotations

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


class TestQueryIntent:
    def test_stores_structured_intent_not_raw_sql(self) -> None:
        intent = QueryIntent(
            user_id="user-1",
            department="sales",
            sensitivity_tier=2,
            intent_type="aggregation",
            filters={"year": 2024, "dept": "sales"},
            estimated_row_count=500,
        )
        assert intent.sensitivity_tier == 2
        assert "raw_sql" not in intent.__dict__  # no raw SQL


class TestApprovalWorkflow:
    def test_creates_request_in_approval_requested_state(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="sales", sensitivity_tier=2,
            intent_type="query", filters={}, estimated_row_count=100,
        )
        req = create_approval_request(intent, store=store)
        assert req.state == ApprovalState.APPROVAL_REQUESTED
        assert req.request_id is not None

    def test_approve_transitions_to_approved(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="sales", sensitivity_tier=2,
            intent_type="query", filters={}, estimated_row_count=100,
        )
        req = create_approval_request(intent, store=store)
        store.decide(req.request_id, ApprovalDecision(
            approver_id="approver-1",
            decision="approved",
            reason="Business justified",
        ))
        updated = store.get(req.request_id)
        assert updated.state == ApprovalState.APPROVED

    def test_reject_transitions_to_rejected(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="sales", sensitivity_tier=2,
            intent_type="query", filters={}, estimated_row_count=100,
        )
        req = create_approval_request(intent, store=store)
        store.decide(req.request_id, ApprovalDecision(
            approver_id="approver-1",
            decision="rejected",
            reason="Not justified",
        ))
        assert store.get(req.request_id).state == ApprovalState.REJECTED

    def test_expired_after_sla(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="sales", sensitivity_tier=2,
            intent_type="query", filters={}, estimated_row_count=100,
        )
        req = create_approval_request(intent, store=store)
        # Manually age the request past 4-hour SLA
        req.created_at = datetime.now(UTC) - timedelta(hours=5)
        assert store.is_expired(req)

    def test_expired_request_does_not_auto_resubmit(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="sales", sensitivity_tier=2,
            intent_type="query", filters={}, estimated_row_count=100,
        )
        req = create_approval_request(intent, store=store)
        req.created_at = datetime.now(UTC) - timedelta(hours=5)
        store.expire(req.request_id)
        assert store.get(req.request_id).state == ApprovalState.EXPIRED
        # Resubmit requires explicit new request_id
        new_req = create_approval_request(intent, store=store)
        assert new_req.request_id != req.request_id

    def test_approval_stores_fingerprint_not_raw_sql(self, store: ApprovalStore) -> None:
        intent = QueryIntent(
            user_id="user-1", department="finance", sensitivity_tier=3,
            intent_type="detail_query", filters={"year": 2024},
            estimated_row_count=50,
        )
        req = create_approval_request(intent, store=store)
        store.decide(req.request_id, ApprovalDecision(
            approver_id="appr-1", decision="approved", reason="ok"
        ))
        record = store.get(req.request_id)
        assert record.query_fingerprint is not None
        assert "raw_sql" not in str(record.__dict__)
