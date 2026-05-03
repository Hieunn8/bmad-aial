"""Tests for Epic 7 Story 7.2 - Anomaly Detection & Alerts."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.anomaly_detection.service import reset_anomaly_detection_service


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="sales-user",
        email="sales.user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "sales-user",
            "email": "sales.user@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )


@pytest.fixture()
def client() -> TestClient:
    reset_anomaly_detection_service()
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
def test_anomaly_scan_creates_alert_and_history_supports_acknowledge_and_dismiss(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    run_resp = client.post(
        "/v1/anomaly-detection/run",
        json={"metric_name": "order_volume", "domain": "sales", "region": "HCM"},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert run_resp.status_code == 200
    run_body = run_resp.json()
    assert run_body["alerts_created"] == 1
    assert run_body["false_positive_rate_30d"] < 0.10
    assert run_body["detection_latency_minutes"] <= 60

    list_resp = client.get("/v1/anomaly-detection/alerts", headers={"Authorization": "Bearer fake-jwt"})
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert list_body["total"] == 1
    alert_id = list_body["alerts"][0]["alert_id"]

    detail_resp = client.get(f"/v1/anomaly-detection/alerts/{alert_id}", headers={"Authorization": "Bearer fake-jwt"})
    assert detail_resp.status_code == 200
    detail_body = detail_resp.json()
    assert detail_body["severity"] == "high"
    assert len(detail_body["suggested_actions"]) == 3
    assert any(point["is_anomaly"] for point in detail_body["series"])

    ack_resp = client.post(f"/v1/anomaly-detection/alerts/{alert_id}/acknowledge", headers={"Authorization": "Bearer fake-jwt"})
    assert ack_resp.status_code == 200
    assert ack_resp.json()["alert"]["status"] == "acknowledged"

    dismiss_resp = client.post(f"/v1/anomaly-detection/alerts/{alert_id}/dismiss", headers={"Authorization": "Bearer fake-jwt"})
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["alert"]["status"] == "dismissed"

    list_again_resp = client.get("/v1/anomaly-detection/alerts", headers={"Authorization": "Bearer fake-jwt"})
    assert list_again_resp.status_code == 200
    assert list_again_resp.json()["alerts"][0]["status"] == "dismissed"


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_anomaly_alert_is_denied_outside_department_scope(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    run_resp = client.post(
        "/v1/anomaly-detection/run",
        json={"metric_name": "order_volume", "domain": "sales", "region": "HCM"},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    alert_id = run_resp.json()["latest_alert_id"]

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

    resp = client.get(
        f"/v1/anomaly-detection/alerts/{alert_id}",
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 403
