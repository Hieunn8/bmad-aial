"""Tests for Epic 6 Story 6.2 — Scheduled Reports."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.approval.workflow import ApprovalDecision, get_approval_store
from orchestration.audit.read_model import AuditFilter, get_audit_read_model
from orchestration.exporting.schedules import reset_scheduled_report_service
from orchestration.exporting.service import get_export_service, reset_export_service


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="finance-user",
        email="finance.user@aial.local",
        department="finance",
        roles=("user",),
        clearance=2,
        raw={
            "sub": "finance-user",
            "email": "finance.user@aial.local",
            "department": "finance",
            "roles": ["user"],
            "clearance": 2,
        },
    )


@pytest.fixture()
def client() -> TestClient:
    reset_export_service()
    reset_scheduled_report_service()
    get_audit_read_model()._records.clear()
    from orchestration.main import app

    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


def _seed_export_source(*, claims: JWTClaims, sensitivity_tier: int = 1) -> str:
    request_id = str(uuid4())
    get_export_service().register_query_result(
        request_id=request_id,
        owner_user_id=claims.sub,
        department_scope=claims.department,
        sensitivity_tier=sensitivity_tier,
        rows=[{"department": "FIN", "amount": 1200}],
        trace_id=str(uuid4()),
        data_source="finance-primary",
    )
    return request_id


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_low_sensitivity_schedule_becomes_active_immediately(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = _seed_export_source(claims=sample_claims, sensitivity_tier=1)

    resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "weekly",
            "format": "xlsx",
            "recipient": sample_claims.email,
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_high_sensitivity_schedule_requires_approval_then_activates(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = _seed_export_source(claims=sample_claims, sensitivity_tier=2)

    first_resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "weekly",
            "format": "pdf",
            "recipient": sample_claims.email,
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert first_resp.status_code == 200
    assert first_resp.json()["status"] == "approval_required"
    approval_request_id = first_resp.json()["approval_request_id"]

    store = get_approval_store()
    store.decide(
        approval_request_id,
        ApprovalDecision(approver_id="approval-officer", decision="approved", reason="ok"),
    )

    second_resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "weekly",
            "format": "pdf",
            "recipient": sample_claims.email,
            "approval_request_id": approval_request_id,
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert second_resp.status_code == 200
    assert second_resp.json()["status"] == "active"


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_external_recipient_is_rejected(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = _seed_export_source(claims=sample_claims)

    resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "daily",
            "format": "csv",
            "recipient": "external@gmail.com",
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 400
    assert "internal recipients" in resp.json()["detail"]


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_run_due_schedule_delivers_and_audits(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = _seed_export_source(claims=sample_claims)
    create_resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "daily",
            "format": "xlsx",
            "recipient": sample_claims.email,
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert create_resp.status_code == 200

    due_time = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    run_resp = client.post(
        "/v1/chat/report-schedules/run-due",
        json={"now": due_time},
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert run_resp.status_code == 200
    delivery = run_resp.json()["deliveries"][0]
    assert delivery["status"] == "delivered"

    audit_records = get_audit_read_model().search(AuditFilter(action="export:scheduled_delivery"), page=1, page_size=20)
    assert len(audit_records) == 1
    assert audit_records[0].metadata["recipient"] == sample_claims.email


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_delivery_failure_retries_three_times_and_logs_failure(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = _seed_export_source(claims=sample_claims)
    create_resp = client.post(
        "/v1/chat/report-schedules",
        json={
            "source_request_id": request_id,
            "cadence": "monthly",
            "format": "pdf",
            "recipient": sample_claims.email,
        },
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert create_resp.status_code == 200

    with patch("orchestration.exporting.schedules.ScheduledReportService._send_report", side_effect=RuntimeError("smtp down")):
        run_resp = client.post(
            "/v1/chat/report-schedules/run-due",
            json={"now": (datetime.now(UTC) + timedelta(days=31)).isoformat()},
            headers={"Authorization": "Bearer fake-jwt"},
        )

    assert run_resp.status_code == 200
    delivery = run_resp.json()["deliveries"][0]
    assert delivery["status"] == "failed"
    assert delivery["attempts"] == 3

    failure_records = get_audit_read_model().search(AuditFilter(action="export:scheduled_delivery"), page=1, page_size=20)
    assert failure_records[0].status == "FAILED"
