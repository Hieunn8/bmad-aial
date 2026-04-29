"""Tests for Cerbos authorization client.

Validates the client against the Cerbos 0.38+ /api/check/resources contract.
"""

import json
from unittest.mock import MagicMock, patch

from aial_shared.auth.cerbos import AuthzResult, CerbosClient, _extract_effect
from aial_shared.auth.keycloak import JWTClaims


def _make_principal(
    sub: str = "user-123",
    roles: tuple[str, ...] = ("user",),
    department: str = "sales",
    clearance: int = 1,
) -> JWTClaims:
    return JWTClaims(
        sub=sub,
        email=f"{sub}@aial.local",
        department=department,
        roles=roles,
        clearance=clearance,
        raw={},
    )


def _mock_cerbos_response(effect: str = "EFFECT_ALLOW", action: str = "query") -> bytes:
    """Matches the real Cerbos /api/check/resources response format."""
    return json.dumps(
        {
            "requestId": "test",
            "results": [
                {
                    "resource": {"kind": "api:chat", "id": "default"},
                    "actions": {action: effect},
                }
            ],
        }
    ).encode()


def _make_mock_urlopen(response_bytes: bytes) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = response_bytes
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestExtractEffect:
    def test_extracts_allow(self) -> None:
        result = json.loads(_mock_cerbos_response("EFFECT_ALLOW"))
        assert _extract_effect(result, "query") == "EFFECT_ALLOW"

    def test_extracts_deny(self) -> None:
        result = json.loads(_mock_cerbos_response("EFFECT_DENY"))
        assert _extract_effect(result, "query") == "EFFECT_DENY"

    def test_missing_results_returns_deny(self) -> None:
        assert _extract_effect({}, "query") == "EFFECT_DENY"

    def test_missing_action_returns_deny(self) -> None:
        result = {"results": [{"actions": {}}]}
        assert _extract_effect(result, "query") == "EFFECT_DENY"

    def test_empty_results_list_returns_deny(self) -> None:
        assert _extract_effect({"results": []}, "query") == "EFFECT_DENY"


class TestCerbosClient:
    def test_check_returns_authz_result(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_ALLOW"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.check(principal, "api:chat", "default", "query")

        assert isinstance(result, AuthzResult)
        assert result.allowed is True
        assert result.resource == "api:chat"
        assert result.action == "query"
        assert result.principal_id == "user-123"

    def test_check_denied_returns_false(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal(roles=("viewer",))
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_DENY"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = client.check(principal, "api:chat", "default", "query")

        assert result.allowed is False

    def test_is_allowed_shorthand(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_ALLOW"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            assert client.is_allowed(principal, "api:chat", "default", "query") is True

    def test_uses_check_resources_endpoint(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_ALLOW"))

        captured_request = None

        def capture_urlopen(req, **kwargs):
            nonlocal captured_request
            captured_request = req
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            client.check(principal, "api:chat", "default", "query")

        assert captured_request is not None
        assert captured_request.full_url == "http://localhost:3592/api/check/resources"

    def test_sends_resources_array_format(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal(department="engineering", clearance=3)
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_ALLOW"))

        captured_body = None

        def capture_urlopen(req, **kwargs):
            nonlocal captured_body
            captured_body = json.loads(req.data)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            client.check(principal, "api:chat", "default", "query")

        assert captured_body is not None
        assert "resources" in captured_body, "Must use resources[] array, not top-level resource"
        assert len(captured_body["resources"]) == 1
        res_entry = captured_body["resources"][0]
        assert res_entry["resource"]["kind"] == "api:chat"
        assert res_entry["resource"]["id"] == "default"
        assert res_entry["actions"] == ["query"]

    def test_sends_correct_principal_attrs(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal(department="engineering", clearance=3)
        mock_resp = _make_mock_urlopen(_mock_cerbos_response("EFFECT_ALLOW"))

        captured_body = None

        def capture_urlopen(req, **kwargs):
            nonlocal captured_body
            captured_body = json.loads(req.data)
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=capture_urlopen):
            client.check(principal, "api:chat", "default", "query")

        assert captured_body is not None
        attrs = captured_body["principal"]["attr"]
        assert attrs["department"] == "engineering"
        assert attrs["clearance"] == "3"
        assert captured_body["principal"]["roles"] == ["user"]
