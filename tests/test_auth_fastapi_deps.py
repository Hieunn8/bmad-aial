"""Tests for FastAPI auth dependencies.

Validates that:
- get_current_user extracts and validates JWT from Authorization header
- require_permission calls CerbosClient and returns 403 on deny
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from aial_shared.auth.fastapi_deps import get_current_user, require_permission
from aial_shared.auth.keycloak import JWTClaims


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={"sub": "user-123", "email": "user@aial.local", "department": "sales", "roles": ["user"], "clearance": 1},
    )


@pytest.fixture()
def admin_claims() -> JWTClaims:
    return JWTClaims(
        sub="admin-456",
        email="admin@aial.local",
        department="engineering",
        roles=("admin", "user"),
        clearance=3,
        raw={
            "sub": "admin-456",
            "email": "admin@aial.local",
            "department": "engineering",
            "roles": ["admin", "user"],
            "clearance": 3,
        },
    )


@pytest.fixture()
def viewer_claims() -> JWTClaims:
    return JWTClaims(
        sub="viewer-789",
        email="viewer@aial.local",
        department="hr",
        roles=("viewer",),
        clearance=0,
        raw={"sub": "viewer-789", "email": "viewer@aial.local", "department": "hr", "roles": ["viewer"], "clearance": 0},
    )


class TestGetCurrentUser:
    def test_missing_auth_header_returns_401(self) -> None:
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user: JWTClaims = pytest.importorskip("fastapi").Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test")
        assert resp.status_code == 401

    def test_invalid_bearer_prefix_returns_401(self) -> None:
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user: JWTClaims = pytest.importorskip("fastapi").Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test", headers={"Authorization": "Basic abc"})
        assert resp.status_code == 401

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    def test_valid_token_returns_claims(
        self,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        sample_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = sample_claims.raw
        mock_validate.return_value = sample_claims

        app = FastAPI()

        @app.get("/test")
        async def endpoint(user: JWTClaims = pytest.importorskip("fastapi").Depends(get_current_user)):
            return {"sub": user.sub, "department": user.department}

        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        assert resp.json()["sub"] == "user-123"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt", side_effect=Exception("bad token"))
    def test_decode_failure_returns_401(self, mock_decode: MagicMock) -> None:
        app = FastAPI()

        @app.get("/test")
        async def endpoint(user: JWTClaims = pytest.importorskip("fastapi").Depends(get_current_user)):
            return {"sub": user.sub}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/test", headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401


class TestRequirePermission:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_allowed_request_passes(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        sample_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = sample_claims.raw
        mock_validate.return_value = sample_claims
        mock_cerbos = MagicMock()
        mock_cerbos.check.return_value = MagicMock(allowed=True)
        mock_cerbos_cls.return_value = mock_cerbos

        dep = require_permission("api:chat", "default", "query")
        app = FastAPI()

        @app.post("/v1/chat/query", dependencies=[pytest.importorskip("fastapi").Depends(dep)])
        async def chat_query():
            return {"answer": "stub"}

        client = TestClient(app)
        resp = client.post("/v1/chat/query", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_denied_request_returns_403(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        viewer_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = viewer_claims.raw
        mock_validate.return_value = viewer_claims
        mock_cerbos = MagicMock()
        mock_cerbos.check.return_value = MagicMock(allowed=False, principal_id="viewer-789", resource="api:chat", action="query")
        mock_cerbos_cls.return_value = mock_cerbos

        dep = require_permission("api:chat", "default", "query")
        app = FastAPI()

        @app.post("/v1/chat/query", dependencies=[pytest.importorskip("fastapi").Depends(dep)])
        async def chat_query():
            return {"answer": "stub"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/v1/chat/query", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 403

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_allowed_for_chat_query(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        admin_claims: JWTClaims,
    ) -> None:
        mock_decode.return_value = admin_claims.raw
        mock_validate.return_value = admin_claims
        mock_cerbos = MagicMock()
        mock_cerbos.check.return_value = MagicMock(allowed=True)
        mock_cerbos_cls.return_value = mock_cerbos

        dep = require_permission("api:chat", "default", "query")
        app = FastAPI()

        @app.post("/v1/chat/query", dependencies=[pytest.importorskip("fastapi").Depends(dep)])
        async def chat_query():
            return {"answer": "stub"}

        client = TestClient(app)
        resp = client.post("/v1/chat/query", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200

    def test_no_auth_header_returns_401(self) -> None:
        dep = require_permission("api:chat", "default", "query")
        app = FastAPI()

        @app.post("/v1/chat/query", dependencies=[pytest.importorskip("fastapi").Depends(dep)])
        async def chat_query():
            return {"answer": "stub"}

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/v1/chat/query")
        assert resp.status_code == 401
