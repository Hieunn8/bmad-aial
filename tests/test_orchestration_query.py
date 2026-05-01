"""Tests for the orchestration chat query endpoint — Story 2A.1."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims


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
    from orchestration.main import app

    return TestClient(app)


def _auth_mocks(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


class TestChatQueryEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_returns_stream_handle_with_request_id_and_trace_id(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Doanh thu HCM tháng 3?", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "streaming"
        UUID(body["request_id"])
        UUID(body["trace_id"])

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_empty_query_returns_400_invalid_query(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "   ", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "invalid-query" in body.get("type", "")
        assert "detail" in body

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_query_too_long_returns_400(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "x" * 2001, "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 400
        assert "invalid-query" in resp.json().get("type", "")

    def test_missing_auth_header_returns_auth_failed_code(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/chat/query",
            json={"query": "test query", "session_id": str(uuid4())},
        )
        assert resp.status_code == 401
        assert resp.json() == {"code": "AUTH_FAILED"}

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    def test_invalid_jwt_returns_auth_failed_code(
        self,
        mock_decode: MagicMock,
        client: TestClient,
    ) -> None:
        mock_decode.side_effect = Exception("invalid token signature")
        resp = client.post(
            "/v1/chat/query",
            json={"query": "test query", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer bad-jwt"},
        )
        assert resp.status_code == 401
        assert resp.json() == {"code": "AUTH_FAILED"}


class TestSqlExplanationStub:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_sql_explanation_returns_data_source(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.get(
            f"/v1/chat/query/{uuid4()}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        # Real explanation replaces stub (Story 2B.1)
        assert "data_source" in body
        assert "raw_sql" not in body or body.get("raw_sql") is None
