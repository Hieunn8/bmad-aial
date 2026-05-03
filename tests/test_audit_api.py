"""Tests for Story 2B.5 — Audit Read Model + Compliance Dashboard API.

Critical invariants verified:
  - Non-admin users cannot read other users' audit records.
  - Admin users can read all records and filter by any user.
  - API returns cross-user data when admin filters; returns only own data otherwise.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditFilter, AuditReadModel, AuditRecord, get_audit_read_model


@pytest.fixture()
def admin_claims() -> JWTClaims:
    return JWTClaims(
        sub="admin-1", email="admin@aial.local", department="engineering",
        roles=("admin",), clearance=3, raw={},
    )


@pytest.fixture()
def regular_user_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-42", email="user@aial.local", department="sales",
        roles=("user",), clearance=1, raw={},
    )


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app
    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = {"sub": claims.sub, "email": claims.email,
                                "department": claims.department, "roles": list(claims.roles), "clearance": claims.clearance}
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


def _seed_audit_model(user_ids: list[str]) -> AuditReadModel:
    """Seed global audit model with records for given user IDs."""
    model = get_audit_read_model()
    now = datetime.now(UTC)
    for uid in user_ids:
        model.append(AuditRecord(
            request_id=str(uuid4()),
            user_id=uid,
            department_id="sales",
            session_id=str(uuid4()),
            timestamp=now,
            intent_type="query",
            sensitivity_tier="LOW",
            sql_hash="hash-" + uid,
            data_sources=["sales_summary"],
            rows_returned=5,
            latency_ms=100,
            policy_decision="ALLOW",
            status="SUCCESS",
        ))
    return model


# ---------------------------------------------------------------------------
# AuditReadModel unit tests
# ---------------------------------------------------------------------------

class TestAuditReadModel:
    @pytest.fixture()
    def model(self) -> AuditReadModel:
        m = AuditReadModel()
        now = datetime.now(UTC)
        for i in range(10):
            m.append(AuditRecord(
                request_id=str(uuid4()),
                user_id=f"user-{i % 3}",
                department_id="sales" if i % 2 == 0 else "finance",
                session_id=str(uuid4()),
                timestamp=now - timedelta(hours=i),
                intent_type="query",
                sensitivity_tier="LOW",
                sql_hash="abc123",
                data_sources=["sales_summary"],
                rows_returned=10,
                latency_ms=120,
                policy_decision="ALLOW" if i != 5 else "DENY",
                status="SUCCESS" if i != 5 else "DENIED",
                denial_reason="dept_mismatch" if i == 5 else None,
            ))
        return m

    def test_filter_by_user(self, model: AuditReadModel) -> None:
        results = model.search(AuditFilter(user_id="user-0"))
        assert len(results) > 0
        assert all(r.user_id == "user-0" for r in results)

    def test_filter_by_policy_decision(self, model: AuditReadModel) -> None:
        results = model.search(AuditFilter(policy_decision="DENY"))
        assert len(results) > 0
        assert all(r.policy_decision == "DENY" for r in results)

    def test_filter_by_action_and_data_source(self, model: AuditReadModel) -> None:
        results = model.search(AuditFilter(action="query", data_source="sales_summary"))
        assert len(results) > 0
        assert all(r.intent_type == "query" for r in results)
        assert all("sales_summary" in r.data_sources for r in results)

    def test_filter_by_date_range(self, model: AuditReadModel) -> None:
        now = datetime.now(UTC)
        results = model.search(AuditFilter(
            date_from=now - timedelta(hours=3),
            date_to=now,
        ))
        assert len(results) <= 4

    def test_results_paginated(self, model: AuditReadModel) -> None:
        results = model.search(AuditFilter(), page=1, page_size=3)
        assert len(results) <= 3

    def test_denied_record_has_denial_reason(self, model: AuditReadModel) -> None:
        denied = model.search(AuditFilter(policy_decision="DENY"))
        assert denied[0].denial_reason is not None

    def test_records_never_expose_raw_result_values(self, model: AuditReadModel) -> None:
        for r in model.search(AuditFilter()):
            d = r.to_response_dict()
            assert "raw_result" not in d
            assert "result_values" not in d

    def test_sensitive_records_hide_raw_sql(self) -> None:
        m = AuditReadModel()
        m.append(AuditRecord(
            request_id=str(uuid4()),
            user_id="user-1", department_id="sales", session_id=str(uuid4()),
            timestamp=datetime.now(UTC), intent_type="query",
            sensitivity_tier="PII_TIER_1", sql_hash="def456",
            data_sources=["customers"], rows_returned=1, latency_ms=50,
            policy_decision="ALLOW", status="SUCCESS",
        ))
        results = m.search(AuditFilter())
        d = results[0].to_response_dict()
        assert d.get("stored_sql") is None


# ---------------------------------------------------------------------------
# API authorization tests — the critical path
# ---------------------------------------------------------------------------

class TestAuditApiAuthorization:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_sees_all_users_records(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        _seed_audit_model(["other-user-1", "other-user-2"])

        resp = client.get("/v1/admin/audit-logs", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        user_ids = {r["user_id"] for r in resp.json()["records"]}
        # Admin should see cross-user records (seeded above)
        assert len(user_ids) > 1 or resp.json()["total"] > 0

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_regular_user_only_sees_own_records(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, regular_user_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, regular_user_claims)
        # Seed records for other users — regular user must NOT see them
        _seed_audit_model(["other-user-X", "other-user-Y"])

        resp = client.get("/v1/admin/audit-logs", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        for record in resp.json()["records"]:
            assert record["user_id"] == regular_user_claims.sub, (
                f"Non-admin user saw another user's record: {record['user_id']}"
            )

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_regular_user_cannot_query_other_users_records(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, regular_user_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, regular_user_claims)

        resp = client.get(
            "/v1/admin/audit-logs?user_id=some-other-user",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 403

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_can_filter_by_specific_user(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        _seed_audit_model(["target-user"])

        resp = client.get(
            "/v1/admin/audit-logs?user_id=target-user",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        for record in resp.json()["records"]:
            assert record["user_id"] == "target-user"
