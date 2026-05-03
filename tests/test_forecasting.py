"""Tests for Epic 7 Story 7.1 - Time-series Forecasting."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.forecasting.service import ForecastJobStatus, get_forecast_service, reset_forecast_service


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
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


@pytest.fixture()
def client() -> TestClient:
    reset_forecast_service()
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
def test_forecast_job_returns_queued_then_result_and_download(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    create_resp = client.post(
        "/v1/forecast/run",
        json={"query": "Dự báo doanh thu Q3 2026 theo kênh phân phối"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["status"] == "queued"
    assert create_body["queue_name"] == "forecast-batch"
    assert create_body["task_name"] == "forecast.time_series.generate_report"
    assert create_body["heavy_job"] is False
    assert create_body["estimated_wait_seconds"] is None

    status_resp = client.get(
        f"/v1/forecast/{create_body['job_id']}",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "completed"
    assert status_body["mape"] < 0.15
    assert status_body["download_url"] is not None
    assert status_body["cached_until"] is not None

    result_resp = client.get(
        f"/v1/forecast/{create_body['job_id']}/result",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert result_resp.status_code == 200
    result_body = result_resp.json()
    assert result_body["confidence_state"] == "forecast-uncertainty"
    assert len(result_body["series"]) >= 9
    assert result_body["acknowledgement"]["acks_late"] is True
    assert result_body["acknowledgement"]["reject_on_worker_lost"] is True

    download_resp = client.get(
        status_body["download_url"],
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert download_resp.status_code == 200
    assert "attachment;" in download_resp.headers["content-disposition"]
    assert "application/json" in download_resp.headers["content-type"]


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_forecast_result_enforces_ownership(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    create_resp = client.post(
        "/v1/forecast/run",
        json={"query": "Dự báo doanh thu Q3 2026 theo kênh phân phối"},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    job_id = create_resp.json()["job_id"]

    other_claims = JWTClaims(
        sub="other-user",
        email="other@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "other-user",
            "email": "other@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )
    _auth(mock_cerbos_cls, mock_validate, mock_decode, other_claims)

    resp = client.get(
        f"/v1/forecast/{job_id}/result",
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 403


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_heavy_forecast_job_returns_eta(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

    response = client.post(
        "/v1/forecast/run",
        json={"query": "Dự báo 2 năm cho 50 SKUs doanh thu theo kênh"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["heavy_job"] is True
    assert body["estimated_wait_seconds"] == 180
    assert body["estimated_wait_message"] == "Kết quả dự kiến sau khoảng 3 phút."


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_overloaded_forecast_queue_returns_fifteen_minute_eta(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    service = get_forecast_service()
    for index in range(21):
        service.enqueue_job(query=f"queued-{index}", principal=sample_claims)

    response = client.post(
        "/v1/forecast/run",
        json={"query": "Dự báo 2 year cho 50 SKUs doanh thu theo kênh"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["heavy_job"] is True
    assert body["estimated_wait_seconds"] == 900
    assert body["estimated_wait_message"] == "Kết quả dự kiến sau 15 phút."


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_forecast_result_expires_after_sixty_minutes(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    create_resp = client.post(
        "/v1/forecast/run",
        json={"query": "Dự báo doanh thu Q3 2026 theo kênh phân phối"},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    job_id = create_resp.json()["job_id"]
    job = get_forecast_service().get_job(job_id=job_id, principal=sample_claims)
    job.expires_at = datetime.now(UTC) - timedelta(minutes=1)

    status_resp = client.get(
        f"/v1/forecast/{job_id}",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == ForecastJobStatus.EXPIRED.value

    result_resp = client.get(
        f"/v1/forecast/{job_id}/result",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert result_resp.status_code == 410


def test_process_job_marks_timeout_after_thirty_minutes(sample_claims: JWTClaims) -> None:
    service = get_forecast_service()
    service.reset()
    job = service.enqueue_job(query="Dự báo doanh thu 24 tháng theo khu vực", principal=sample_claims)
    job.created_at = datetime.now(UTC) - timedelta(minutes=31)

    service.process_job(job.job_id)

    timed_out = service.get_job(job_id=job.job_id, principal=sample_claims)
    assert timed_out.status == ForecastJobStatus.FAILED
    assert timed_out.error == "queue_timeout"
