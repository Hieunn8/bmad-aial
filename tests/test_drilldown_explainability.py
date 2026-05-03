"""Tests for Epic 7 Story 7.4 - Drill-down Analytics + Result Explainability."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.explainability.service import reset_drilldown_explainability_service


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="sales-manager",
        email="sales.manager@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "sales-manager",
            "email": "sales.manager@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
        region="HCM",
    )


@pytest.fixture()
def client() -> TestClient:
    reset_drilldown_explainability_service()
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
def test_drilldown_analysis_returns_authorized_region_only_and_top_factors(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    response = client.post(
        "/v1/analytics/drilldown-explainability",
        json={"dimension": "region", "shap_available": True},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["confidence_label"] in {"có khả năng tăng", "khả năng cao giảm", "không rõ xu hướng"}
    assert body["explanation_status"] == "ready"
    assert len(body["top_factors"]) == 3
    assert [row["label"] for row in body["drilldown"]] == ["HCM"]


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_drilldown_analysis_uses_async_fallback_when_shap_unavailable(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    response = client.post(
        "/v1/analytics/drilldown-explainability",
        json={"dimension": "channel", "shap_available": False},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["explanation_status"] == "pending"
    assert body["top_factors"] == []
    job_id = body["explainability_job"]["job_id"]

    status_resp = client.get(
        f"/v1/analytics/explainability-jobs/{job_id}",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "completed"

    result_resp = client.get(
        f"/v1/analytics/explainability-jobs/{job_id}/result",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert result_resp.status_code == 200
    assert len(result_resp.json()["top_factors"]) == 3


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_explainability_job_enforces_owner_scope(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    response = client.post(
        "/v1/analytics/drilldown-explainability",
        json={"dimension": "channel", "shap_available": False},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    job_id = response.json()["explainability_job"]["job_id"]

    other_claims = JWTClaims(
        sub="finance-user",
        email="finance.user@aial.local",
        department="finance",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "finance-user",
            "email": "finance.user@aial.local",
            "department": "finance",
            "roles": ["user"],
            "clearance": 1,
        },
    )
    _auth(mock_cerbos_cls, mock_validate, mock_decode, other_claims)

    status_resp = client.get(
        f"/v1/analytics/explainability-jobs/{job_id}",
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert status_resp.status_code == 403
