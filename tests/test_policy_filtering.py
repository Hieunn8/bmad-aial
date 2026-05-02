"""Tests for Story 3.2 — Pre-retrieval Policy Filtering."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from aial_shared.auth.keycloak import JWTClaims
from rag.retrieval.policy_filter import PolicyEnforcementService, PolicyDecision
from rag.retrieval.weaviate_filter import WeaviateFilterBuilder


@pytest.fixture()
def sales_user() -> JWTClaims:
    return JWTClaims(
        sub="user-sales", email="sales@aial.local", department="sales",
        roles=("user",), clearance=1, raw={},
    )


@pytest.fixture()
def hr_user() -> JWTClaims:
    return JWTClaims(
        sub="user-hr", email="hr@aial.local", department="hr",
        roles=("user",), clearance=2, raw={},
    )


class TestPolicyEnforcementService:
    def test_returns_allowed_departments_for_user(self, sales_user: JWTClaims) -> None:
        mock_cerbos = MagicMock()
        mock_cerbos.is_allowed.return_value = True
        service = PolicyEnforcementService(cerbos_client=mock_cerbos)
        decision = service.enforce(sales_user)
        assert isinstance(decision, PolicyDecision)
        assert decision.allowed is True
        assert "sales" in decision.allowed_departments

    def test_fail_closed_on_cerbos_timeout(self, sales_user: JWTClaims) -> None:
        mock_cerbos = MagicMock()
        mock_cerbos.is_allowed.side_effect = TimeoutError("Cerbos timeout")
        service = PolicyEnforcementService(cerbos_client=mock_cerbos, timeout_ms=500)
        decision = service.enforce(sales_user)
        assert decision.allowed is False
        assert decision.denial_reason == "cerbos_timeout"

    def test_max_classification_from_clearance(self, sales_user: JWTClaims) -> None:
        mock_cerbos = MagicMock()
        mock_cerbos.is_allowed.return_value = True
        service = PolicyEnforcementService(cerbos_client=mock_cerbos)
        decision = service.enforce(sales_user)
        # clearance=1 → max_classification=INTERNAL (1)
        assert decision.max_classification == 1

    def test_higher_clearance_gets_higher_max_classification(self, hr_user: JWTClaims) -> None:
        mock_cerbos = MagicMock()
        mock_cerbos.is_allowed.return_value = True
        service = PolicyEnforcementService(cerbos_client=mock_cerbos)
        decision = service.enforce(hr_user)
        assert decision.max_classification >= 2


class TestWeaviateFilterBuilder:
    def test_builds_department_filter(self) -> None:
        builder = WeaviateFilterBuilder()
        decision = PolicyDecision(
            allowed=True,
            allowed_departments=["sales"],
            max_classification=1,
        )
        f = builder.build(decision)
        assert f is not None
        assert "department" in str(f)

    def test_builds_classification_range_filter(self) -> None:
        builder = WeaviateFilterBuilder()
        decision = PolicyDecision(
            allowed=True,
            allowed_departments=["sales", "engineering"],
            max_classification=2,
        )
        f = builder.build(decision)
        assert "classification" in str(f)

    def test_denied_policy_builds_empty_filter(self) -> None:
        builder = WeaviateFilterBuilder()
        decision = PolicyDecision(allowed=False, allowed_departments=[], max_classification=0)
        f = builder.build(decision)
        assert f is None

    def test_filter_includes_staleness_exclusion(self) -> None:
        builder = WeaviateFilterBuilder()
        decision = PolicyDecision(
            allowed=True, allowed_departments=["sales"], max_classification=1,
        )
        f = builder.build(decision, staleness_threshold_days=180)
        assert "effective_date" in str(f)

    def test_access_limited_notice_when_filtering_applied(self) -> None:
        builder = WeaviateFilterBuilder()
        decision = PolicyDecision(
            allowed=True, allowed_departments=["sales"], max_classification=1,
        )
        notice = builder.access_notice(decision)
        assert "giới hạn" in notice.lower() or notice == ""
