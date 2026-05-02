"""Tests for Story 2B.1 — Full SQL Explanation (FR-O5)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.explanation.generator import (
    ExplanationConfidence,
    SqlExplanation,
    SqlExplanationGenerator,
)


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123", email="u@aial.local", department="sales",
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


class TestSqlExplanation:
    def test_explanation_has_required_fields(self) -> None:
        exp = SqlExplanation(
            data_source="Bảng SALES_SUMMARY, chi nhánh HCM",
            formula_description="Tổng doanh thu thuần theo tháng",
            filters_applied=["Tháng: 3/2024", "Chi nhánh: HCM"],
            confidence=ExplanationConfidence.HIGH,
        )
        assert exp.data_source
        assert exp.formula_description
        assert isinstance(exp.filters_applied, list)
        assert exp.confidence == ExplanationConfidence.HIGH

    def test_low_confidence_has_uncertainty_message(self) -> None:
        exp = SqlExplanation(
            data_source="Bảng không xác định",
            formula_description=None,
            filters_applied=[],
            confidence=ExplanationConfidence.MEDIUM,
        )
        assert exp.uncertainty_message is not None
        assert "ước tính" in exp.uncertainty_message.lower() or "Trung bình" in exp.uncertainty_message

    def test_high_confidence_has_no_uncertainty_message(self) -> None:
        exp = SqlExplanation(
            data_source="SALES_SUMMARY",
            formula_description="SUM(NET_REVENUE)",
            filters_applied=["year=2024"],
            confidence=ExplanationConfidence.HIGH,
        )
        assert exp.uncertainty_message is None

    def test_raw_sql_not_exposed_by_default(self) -> None:
        exp = SqlExplanation(
            data_source="SALES",
            formula_description="COUNT(*)",
            filters_applied=[],
            confidence=ExplanationConfidence.HIGH,
            raw_sql="SELECT COUNT(*) FROM sales",
        )
        d = exp.to_response_dict(include_raw_sql=False)
        assert "raw_sql" not in d or d.get("raw_sql") is None

    def test_raw_sql_shown_on_explicit_request(self) -> None:
        exp = SqlExplanation(
            data_source="SALES",
            formula_description="COUNT(*)",
            filters_applied=[],
            confidence=ExplanationConfidence.HIGH,
            raw_sql="SELECT COUNT(*) FROM sales",
        )
        d = exp.to_response_dict(include_raw_sql=True)
        assert d.get("raw_sql") == "SELECT COUNT(*) FROM sales"


class TestSqlExplanationGenerator:
    def test_generates_explanation_from_sql(self) -> None:
        gen = SqlExplanationGenerator()
        result = gen.explain_kw(
            sql="SELECT SUM(net_revenue) FROM sales_summary WHERE dept='sales' AND month=3",
            metric_context={"term": "doanh thu thuần", "formula": "SUM(NET_REVENUE)"},
        )
        assert isinstance(result, SqlExplanation)
        assert result.data_source
        assert result.confidence in ExplanationConfidence

    def test_explanation_cached_alongside_result(self) -> None:
        gen = SqlExplanationGenerator()
        result1 = gen.explain_kw(sql="SELECT 1 FROM dual", metric_context={})
        result2 = gen.explain_kw(sql="SELECT 1 FROM dual", metric_context={})
        assert result1.data_source == result2.data_source


class TestSqlExplanationEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_unknown_request_id_returns_404(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        # Unregistered UUID — must return 404, not a fabricated explanation
        resp = client.get(
            f"/v1/chat/query/{uuid4()}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 404, (
            "Explanation endpoint must return 404 for unregistered request_ids, "
            "not a fabricated provenance response"
        )

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_registered_explanation_returns_real_structure(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        # Register an explanation manually (simulates graph completion)
        from orchestration.explanation.generator import SqlExplanationGenerator
        from orchestration.routes.query import _explanation_store
        req_id = str(uuid4())
        gen = SqlExplanationGenerator()
        exp = gen.explain_kw(sql="SELECT SUM(revenue) FROM sales WHERE year=2024")
        _explanation_store[req_id] = (sample_claims.sub, exp)

        resp = client.get(
            f"/v1/chat/query/{req_id}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data_source" in body
        # Must NOT be the old stub response
        assert body.get("status") != "not_implemented", "Stub response still returned — not replaced"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_explanation_owned_by_different_user_returns_403(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        from orchestration.explanation.generator import SqlExplanationGenerator
        from orchestration.routes.query import _explanation_store
        req_id = str(uuid4())
        gen = SqlExplanationGenerator()
        exp = gen.explain_kw(sql="SELECT 1 FROM dual")
        _explanation_store[req_id] = ("other-user-id", exp)  # owned by someone else

        resp = client.get(
            f"/v1/chat/query/{req_id}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 403

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_explanation_does_not_expose_raw_sql_by_default(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        from orchestration.explanation.generator import SqlExplanationGenerator
        from orchestration.routes.query import _explanation_store
        req_id = str(uuid4())
        gen = SqlExplanationGenerator()
        exp = gen.explain_kw(sql="SELECT revenue FROM sales")
        _explanation_store[req_id] = (sample_claims.sub, exp)

        resp = client.get(
            f"/v1/chat/query/{req_id}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        body = resp.json()
        # raw_sql must NOT be present in default response (progressive disclosure)
        assert body.get("raw_sql") is None, "raw_sql must be None by default (FR-O5 progressive disclosure)"
