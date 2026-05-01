"""Tests for Story 2A.9 — Onboarding Shell + First-Query Scaffold."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.onboarding.roles import (
    ROLE_PLACEHOLDERS,
    UserRole,
    get_role_placeholder,
)


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
    mock_decode.return_value = {
        "sub": claims.sub, "email": claims.email, "department": claims.department,
        "roles": list(claims.roles), "clearance": claims.clearance,
    }
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


class TestUserRoles:
    def test_all_three_roles_defined(self) -> None:
        assert UserRole.REPORTING in UserRole.__members__.values()
        assert UserRole.ANSWERING in UserRole.__members__.values()
        assert UserRole.ANALYSIS in UserRole.__members__.values()

    def test_sales_role_placeholder_is_vietnamese(self) -> None:
        placeholder = get_role_placeholder(UserRole.REPORTING, department="sales")
        assert "VD:" in placeholder or "Doanh thu" in placeholder

    def test_all_roles_have_placeholder(self) -> None:
        for role in UserRole:
            assert get_role_placeholder(role) != ""

    def test_placeholder_map_covers_all_roles(self) -> None:
        for role in UserRole:
            assert role in ROLE_PLACEHOLDERS


class TestRolePreferenceApi:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_new_user_has_no_role_preference(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.get("/v1/user/role-preference", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("has_preference") is False or body.get("role") is None

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_set_role_preference_returns_200(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/user/role-preference",
            json={"role": "reporting"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        assert resp.json().get("role") == "reporting"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_invalid_role_returns_400(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/user/role-preference",
            json={"role": "invalid_role"},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 400
