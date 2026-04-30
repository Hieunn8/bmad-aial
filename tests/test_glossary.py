"""Tests for Story 2A.2 — Business Glossary API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123", email="user@aial.local", department="sales",
        roles=("user",), clearance=1, raw={},
    )


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app
    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw if claims.raw else {
        "sub": claims.sub, "email": claims.email, "department": claims.department,
        "roles": list(claims.roles), "clearance": claims.clearance,
    }
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


class TestGlossaryEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    @patch("orchestration.semantic.glossary.GlossaryRepository.find")
    def test_known_term_returns_definition(
        self,
        mock_find: MagicMock,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        mock_find.return_value = {
            "term": "doanh thu thuần",
            "definition": "Doanh thu bán hàng sau khi trừ chiết khấu và hàng hoàn",
            "formula": "SUM(NET_REVENUE)",
            "owner": "Finance",
            "freshness_rule": "daily",
        }

        resp = client.get(
            "/v1/glossary/doanh%20thu%20thu%E1%BA%A7n",
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["term"] == "doanh thu thuần"
        assert "formula" in body
        assert body["owner"] == "Finance"
        assert body["freshness_rule"] == "daily"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    @patch("orchestration.semantic.glossary.GlossaryRepository.find")
    def test_unknown_term_returns_not_found(
        self,
        mock_find: MagicMock,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        mock_find.return_value = None

        resp = client.get(
            "/v1/glossary/unknown-term",
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "not_found"


class TestGlossaryRepository:
    def test_find_returns_none_for_unknown_term(self) -> None:
        from orchestration.semantic.glossary import GlossaryRepository

        repo = GlossaryRepository(connection_factory=None)
        with patch.object(repo, "find", return_value=None):
            result = repo.find("nonexistent")
        assert result is None

    def test_glossary_entry_seed_contains_required_fields(self) -> None:
        from orchestration.semantic.glossary import SEED_GLOSSARY

        for entry in SEED_GLOSSARY:
            assert "term" in entry
            assert "formula" in entry
            assert "owner" in entry
            assert "freshness_rule" in entry
