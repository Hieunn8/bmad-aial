"""Tests for Epic 6 Story 6.1 — Export Results."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.audit.read_model import AuditFilter, get_audit_read_model
from orchestration.exporting.service import get_export_service, reset_export_service


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "user-123",
            "email": "user@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )


@pytest.fixture()
def client() -> TestClient:
    reset_export_service()
    get_audit_read_model()._records.clear()
    from orchestration.main import app

    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


def _seed_exportable_result(*, claims: JWTClaims, request_id: str, sensitivity_tier: int = 1) -> None:
    get_export_service().register_query_result(
        request_id=request_id,
        owner_user_id=claims.sub,
        department_scope=claims.department,
        sensitivity_tier=sensitivity_tier,
        rows=[
            {"branch": "HCM", "revenue": 1200, "note": "safe summary"},
            {"branch": "HN", "revenue": 980, "note": "safe summary"},
        ],
        trace_id=str(uuid4()),
        data_source="sales-primary",
    )


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_export_preview_returns_row_count_and_sensitivity_warning(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = str(uuid4())
    _seed_exportable_result(claims=sample_claims, request_id=request_id, sensitivity_tier=2)

    resp = client.get(
        f"/v1/chat/query/{request_id}/export-preview?format=xlsx",
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["estimated_row_count"] == 2
    assert body["format"] == "xlsx"
    assert body["sensitivity_tier"] == 2
    assert "sensitivity tier 2" in body["sensitivity_warning"]


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_export_requires_human_review_confirmation(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = str(uuid4())
    _seed_exportable_result(claims=sample_claims, request_id=request_id)

    resp = client.post(
        f"/v1/chat/query/{request_id}/export",
        json={"format": "csv", "human_review_confirmed": False},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 400
    assert "Human review confirmation" in resp.json()["detail"]


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_export_job_returns_queued_then_downloadable_file_and_audit_metadata(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
    request_id = str(uuid4())
    _seed_exportable_result(claims=sample_claims, request_id=request_id, sensitivity_tier=1)

    create_resp = client.post(
        f"/v1/chat/query/{request_id}/export",
        json={"format": "xlsx", "human_review_confirmed": True, "recipient": "finance@aial.local"},
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert create_resp.status_code == 200
    create_body = create_resp.json()
    assert create_body["status"] == "queued"
    assert create_body["queue_name"] == "export-jobs"
    assert create_body["task_name"] == "export.report.generate_excel"

    status_resp = client.get(
        f"/v1/chat/exports/{create_body['job_id']}",
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert status_resp.status_code == 200
    status_body = status_resp.json()
    assert status_body["status"] == "completed"
    assert status_body["download_url"] == f"/v1/chat/exports/{create_body['job_id']}/download"
    assert status_body["expires_at"] is not None

    download_resp = client.get(
        status_body["download_url"],
        headers={"Authorization": "Bearer fake-jwt"},
    )
    assert download_resp.status_code == 200
    assert "attachment;" in download_resp.headers["content-disposition"]
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in download_resp.headers["content-type"]
    assert len(download_resp.content) > 100

    audit_records = get_audit_read_model().search(AuditFilter(action="export:generate"), page=1, page_size=20)
    assert len(audit_records) == 1
    metadata = audit_records[0].metadata or {}
    assert metadata["job_id"] == create_body["job_id"]
    assert metadata["format"] == "xlsx"
    assert metadata["row_count"] == 2
    assert metadata["department_scope"] == sample_claims.department
    assert metadata["sensitivity_tier"] == 1
    assert metadata["recipient"] == "finance@aial.local"
    assert "download_expires_at" in metadata


@patch("aial_shared.auth.fastapi_deps.decode_jwt")
@patch("aial_shared.auth.fastapi_deps.validate_token_claims")
@patch("aial_shared.auth.fastapi_deps.CerbosClient")
def test_export_route_enforces_ownership(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    client: TestClient,
    sample_claims: JWTClaims,
) -> None:
    other_claims = JWTClaims(
        sub="user-999",
        email="other@aial.local",
        department="finance",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "user-999",
            "email": "other@aial.local",
            "department": "finance",
            "roles": ["user"],
            "clearance": 1,
        },
    )
    _auth(mock_cerbos_cls, mock_validate, mock_decode, other_claims)
    request_id = str(uuid4())
    _seed_exportable_result(claims=sample_claims, request_id=request_id)

    resp = client.get(
        f"/v1/chat/query/{request_id}/export-preview?format=csv",
        headers={"Authorization": "Bearer fake-jwt"},
    )

    assert resp.status_code == 403
