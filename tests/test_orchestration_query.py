"""Tests for the orchestration chat query endpoint."""

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


class TestChatQueryEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_returns_stub_answer_and_trace_id(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = sample_claims.raw
        mock_validate.return_value = sample_claims
        mock_cerbos = MagicMock()
        mock_cerbos.check.return_value = MagicMock(allowed=True)
        mock_cerbos_cls.return_value = mock_cerbos

        resp = client.post(
            "/v1/chat/query",
            json={"query": "test query", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["answer"] == "stub"
        UUID(body["trace_id"])

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_rejects_empty_query(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = sample_claims.raw
        mock_validate.return_value = sample_claims
        mock_cerbos = MagicMock()
        mock_cerbos.check.return_value = MagicMock(allowed=True)
        mock_cerbos_cls.return_value = mock_cerbos

        resp = client.post(
            "/v1/chat/query",
            json={"query": "   ", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 422
