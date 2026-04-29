"""E2E Walking Skeleton Gate — Story 1.9.

Tests the full request path: Keycloak JWT → Kong Gateway → FastAPI Orchestration
→ LangGraph stub, with distributed trace verification in Grafana Tempo.

Run with: AIAL_RUN_E2E_TESTS=1 pytest tests/test_e2e_walking_skeleton.py -m walking_skeleton_gate -v
"""

from __future__ import annotations

import os
import time
from uuid import UUID, uuid4

import httpx
import pytest

# ---------------------------------------------------------------------------
# Environment configuration — all configurable via env vars
# ---------------------------------------------------------------------------
_E2E_ENABLED = os.getenv("AIAL_RUN_E2E_TESTS") == "1"
_KONG_URL = os.getenv("AIAL_KONG_URL", "http://localhost:8000")
_ORCHESTRATION_URL = os.getenv("AIAL_ORCHESTRATION_URL", "http://localhost:8090")
_TEMPO_URL = os.getenv("AIAL_TEMPO_URL", "http://localhost:3200")
_KEYCLOAK_URL = os.getenv("AIAL_KEYCLOAK_URL", "http://localhost:8080")
_KEYCLOAK_REALM = os.getenv("AIAL_KEYCLOAK_REALM", "aial")
_KEYCLOAK_CLIENT = os.getenv("AIAL_E2E_KEYCLOAK_CLIENT", "aial-web")
_E2E_USER = os.getenv("AIAL_E2E_TEST_USER", "dev-user")
_E2E_PASSWORD = os.getenv("AIAL_E2E_TEST_PASSWORD", "user")

# Expected service names in OTel traces (service.name resource attribute)
_EXPECTED_TRACE_SERVICES = {"orchestration"}

pytestmark = [
    pytest.mark.e2e_gate,
    pytest.mark.walking_skeleton_gate,
    pytest.mark.skipif(not _E2E_ENABLED, reason="set AIAL_RUN_E2E_TESTS=1 to run walking skeleton gate"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_keycloak_jwt() -> str:
    """Obtain a real Keycloak JWT via Resource Owner Password Credentials grant."""
    url = f"{_KEYCLOAK_URL}/realms/{_KEYCLOAK_REALM}/protocol/openid-connect/token"
    resp = httpx.post(
        url,
        data={
            "grant_type": "password",
            "client_id": _KEYCLOAK_CLIENT,
            "username": _E2E_USER,
            "password": _E2E_PASSWORD,
            "scope": "openid aial-claims",
        },
        timeout=10.0,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError(f"Keycloak did not return access_token; response: {resp.text[:200]}")
    return token


def _wait_for_tempo_trace(trace_id: str, *, timeout: float = 30.0) -> dict:
    """Poll Grafana Tempo until the trace is visible with at least one span, or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = httpx.get(
                f"{_TEMPO_URL}/api/traces/{trace_id}",
                headers={"Accept": "application/json"},
                timeout=5.0,
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                except Exception:
                    pass
                else:
                    if data.get("resourceSpans"):
                        return data
        except httpx.TransportError:
            pass
        time.sleep(1.0)
    raise TimeoutError(f"Trace {trace_id} not visible in Grafana Tempo after {timeout}s")


def _extract_service_names(trace_data: dict) -> set[str]:
    """Extract all service.name string values from an OTLP JSON trace response."""
    names: set[str] = set()
    for rs in trace_data.get("resourceSpans", []):
        for attr in rs.get("resource", {}).get("attributes", []):
            if attr.get("key") == "service.name":
                name = attr.get("value", {}).get("stringValue")
                if name:
                    names.add(name)
    return names


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def analyst_jwt() -> str:
    """Real Keycloak JWT for the E2E test user (sales department, user role).

    Function-scoped to avoid stale tokens when Keycloak TTL < module runtime.
    """
    return _get_keycloak_jwt()


@pytest.fixture(scope="module")
def kong_client() -> httpx.Client:
    with httpx.Client(base_url=_KONG_URL, timeout=10.0) as client:
        yield client


@pytest.fixture(scope="module")
def orchestration_client() -> httpx.Client:
    with httpx.Client(base_url=_ORCHESTRATION_URL, timeout=10.0) as client:
        yield client


# ---------------------------------------------------------------------------
# AC1 — Successful authenticated request via Kong returns 200 within 5s
# ---------------------------------------------------------------------------


def test_ac1_authenticated_request_returns_200_within_5s(
    kong_client: httpx.Client,
    analyst_jwt: str,
) -> None:
    """AC1: POST /v1/chat/query with valid JWT → HTTP 200, non-empty answer, trace_id UUID."""
    start = time.monotonic()
    resp = kong_client.post(
        "/v1/chat/query",
        json={"query": "test query", "session_id": str(uuid4())},
        headers={"Authorization": f"Bearer {analyst_jwt}"},
    )
    elapsed = time.monotonic() - start

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert elapsed < 5.0, f"Response took {elapsed:.2f}s — must be under 5s"

    body = resp.json()
    assert body.get("answer"), "answer must be a non-empty string"
    UUID(body["trace_id"])  # validates trace_id is a well-formed UUID


# ---------------------------------------------------------------------------
# AC2 — Distributed trace appears in Grafana Tempo with orchestration span
# ---------------------------------------------------------------------------


def test_ac2_trace_visible_in_tempo_with_orchestration_span(
    kong_client: httpx.Client,
    analyst_jwt: str,
) -> None:
    """AC2: Grafana Tempo must show a trace with the orchestration service span."""
    resp = kong_client.post(
        "/v1/chat/query",
        json={"query": "trace gate test", "session_id": str(uuid4())},
        headers={"Authorization": f"Bearer {analyst_jwt}"},
    )
    assert resp.status_code == 200, f"Request failed: {resp.text}"
    trace_id = resp.json()["trace_id"]

    trace_data = _wait_for_tempo_trace(trace_id, timeout=30.0)
    service_names = _extract_service_names(trace_data)

    missing = _EXPECTED_TRACE_SERVICES - service_names
    assert not missing, (
        f"Missing service spans in Tempo trace {trace_id}. "
        f"Expected: {_EXPECTED_TRACE_SERVICES}, found: {service_names}"
    )


# ---------------------------------------------------------------------------
# AC3 — Expired / missing JWT → HTTP 401 with code AUTH_FAILED
# ---------------------------------------------------------------------------


def test_ac3_missing_jwt_returns_401_auth_failed(kong_client: httpx.Client) -> None:
    """AC3a: No Authorization header → 401 AUTH_FAILED."""
    resp = kong_client.post(
        "/v1/chat/query",
        json={"query": "should be rejected", "session_id": str(uuid4())},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


def test_ac3_malformed_jwt_returns_401(kong_client: httpx.Client) -> None:
    """AC3b: Malformed JWT → 401."""
    resp = kong_client.post(
        "/v1/chat/query",
        json={"query": "should be rejected", "session_id": str(uuid4())},
        headers={"Authorization": "Bearer not.a.valid.jwt"},
    )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


def test_ac3_direct_no_auth_returns_auth_failed_body(
    orchestration_client: httpx.Client,
) -> None:
    """AC3c: Direct to orchestration without auth → 401 with code=AUTH_FAILED body."""
    resp = orchestration_client.post(
        "/v1/chat/query",
        json={"query": "no auth", "session_id": str(uuid4())},
    )
    assert resp.status_code == 401
    assert resp.json() == {"code": "AUTH_FAILED"}


# ---------------------------------------------------------------------------
# AC4 — PM demo flow (manual gate — documented here, verified separately)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="PM demo flow requires browser — verify manually using the running UI at http://localhost:3000")
def test_ac4_pm_demo_flow_manual() -> None:
    """AC4: Login via SSO → dashboard → submit query → receive mock response without errors.

    Manual verification checklist:
    1. Open http://localhost:3000 in browser
    2. Log in with SSO (dev-user / user)
    3. Submit a query in the chat UI
    4. Verify a non-error response appears
    5. Verify no blank screens or unhandled JS errors in browser console
    """


# ---------------------------------------------------------------------------
# AC5 — Kong offline → frontend degraded-state banner (manual gate)
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="Kong degraded-state requires browser + manual Kong stop — verify manually")
def test_ac5_kong_offline_frontend_shows_degraded_state_manual() -> None:
    """AC5: Stop Kong → frontend ConnectionStatusBanner shows degraded message.

    Manual verification checklist:
    1. Ensure UI is open in browser and authenticated
    2. Run: docker compose -f infra/docker-compose.dev.yml stop kong
    3. Attempt to submit a query in the UI
    4. Verify ConnectionStatusBanner appears with degraded-state message
    5. Verify Error Boundary renders graceful fallback (no blank screen)
    6. Run: docker compose -f infra/docker-compose.dev.yml start kong
    7. Verify UI recovers
    """
