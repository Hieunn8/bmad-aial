"""Tests for orchestration service health and readiness endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app

    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_returns_status_healthy(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert body == {"status": "healthy"}


class TestReadinessEndpoint:
    def test_readiness_returns_200_when_all_deps_reachable(self, client: TestClient) -> None:
        with patch("orchestration.routes.health._tcp_check", return_value=True):
            resp = client.get("/readiness")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body["checks"]["postgres"] == "ok"
        assert body["checks"]["redis"] == "ok"
        assert body["checks"]["cerbos"] == "ok"

    def test_readiness_returns_503_when_dep_unreachable(self, client: TestClient) -> None:
        def selective_check(host: str, port: int, timeout: float = 2.0) -> bool:
            return port != 5432

        with patch("orchestration.routes.health._tcp_check", side_effect=selective_check):
            resp = client.get("/readiness")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"
        assert body["checks"]["postgres"] == "unreachable"
        assert body["checks"]["redis"] == "ok"

    def test_readiness_returns_503_when_all_deps_down(self, client: TestClient) -> None:
        with patch("orchestration.routes.health._tcp_check", return_value=False):
            resp = client.get("/readiness")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "not_ready"

    def test_readiness_checks_three_deps(self, client: TestClient) -> None:
        with patch("orchestration.routes.health._tcp_check", return_value=True):
            resp = client.get("/readiness")
        checks = resp.json()["checks"]
        assert set(checks.keys()) == {"postgres", "redis", "cerbos"}
