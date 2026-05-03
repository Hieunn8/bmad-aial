"""Tests for Epic 7 Story 7.3 - Trend Analysis."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import fakeredis
import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.cache.query_result_cache import reset_query_result_cache


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="sales-analyst",
        email="sales.analyst@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "sales-analyst",
            "email": "sales.analyst@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )


@pytest.fixture()
def client() -> TestClient:
    reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))
    from orchestration.main import app

    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_trend_analysis_returns_plain_language_and_drilldown(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    response = client.post(
        "/v1/trend-analysis/run",
        json={"metric_name": "doanh thu", "comparison_type": "yoy", "dimension": "region"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["comparison_type"] == "yoy"
    assert body["provider_used"] == "statsmodels-trend"
    assert body["contains_jargon"] is False
    assert body["direction"] in {"tăng", "giảm"}
    assert body["current_period"] == "Q1 2026"
    assert body["previous_period"] == "Q1 2025"
    assert len(body["drilldown"]) >= 1
    assert body["department_scope"] == "sales"
    assert body["cache_hit"] is False


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_trend_analysis_second_request_hits_cache(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    first = client.post(
        "/v1/trend-analysis/run",
        json={"metric_name": "doanh thu", "comparison_type": "mom", "dimension": "product"},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    second = client.post(
        "/v1/trend-analysis/run",
        json={"metric_name": "doanh thu", "comparison_type": "mom", "dimension": "product"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["cache_hit"] is True
    assert second.json()["cache_similarity"] >= 0.85


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_trend_analysis_supports_department_drilldown_and_manual_uat_gate(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    response = client.post(
        "/v1/trend-analysis/run",
        json={"metric_name": "chi phí", "comparison_type": "qoq", "dimension": "department"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["comparison_type"] == "qoq"
    assert body["dimension"] == "department"
    assert len(body["drilldown"]) == 1
    assert body["uat_gate"]["status"] == "pending-manual-review"
    assert body["uat_gate"]["minimum_clarity_score"] == 4
