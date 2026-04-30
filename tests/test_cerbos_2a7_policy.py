"""Tests for Story 2A.7 — Cerbos principal.attr schema freeze.

Verifies:
- resource_attr forwarded to Cerbos payload
- dept-domain match/mismatch routing
- DENY without required principal attrs
- ADR-freeze contract: dept and clearance always present in payload
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pathlib import Path

from aial_shared.auth.cerbos import AuthzResult, CerbosClient
from aial_shared.auth.keycloak import JWTClaims

INFRA = Path(__file__).resolve().parent.parent / "infra"


def _make_principal(
    department: str = "sales",
    clearance: int = 1,
    roles: tuple[str, ...] = ("user",),
) -> JWTClaims:
    return JWTClaims(
        sub="test-user",
        email="test@aial.local",
        department=department,
        roles=roles,
        clearance=clearance,
        raw={},
    )


def _mock_cerbos(effect: str = "EFFECT_ALLOW", action: str = "query") -> MagicMock:
    body = json.dumps({
        "results": [{"resource": {"kind": "api:chat", "id": "default"}, "actions": {action: effect}}]
    }).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ---------------------------------------------------------------------------
# Principal attr contract (freeze verification)
# ---------------------------------------------------------------------------


class TestPrincipalAttrContract:
    def test_check_always_sends_department_in_principal_attr(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal(department="sales")
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            return _mock_cerbos()

        with patch("urllib.request.urlopen", side_effect=capture):
            client.check(principal, "api:chat", "default", "query")

        attrs = captured["body"]["principal"]["attr"]
        assert "department" in attrs
        assert attrs["department"] == "sales"

    def test_check_always_sends_clearance_in_principal_attr(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal(clearance=2)
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            return _mock_cerbos()

        with patch("urllib.request.urlopen", side_effect=capture):
            client.check(principal, "api:chat", "default", "query")

        attrs = captured["body"]["principal"]["attr"]
        assert "clearance" in attrs
        assert attrs["clearance"] == "2"


# ---------------------------------------------------------------------------
# resource_attr forwarding
# ---------------------------------------------------------------------------


class TestResourceAttrForwarding:
    def test_resource_attr_included_in_payload_when_provided(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            return _mock_cerbos()

        with patch("urllib.request.urlopen", side_effect=capture):
            client.check(
                principal, "api:chat", "default", "query",
                resource_attr={"domain": "sales"},
            )

        resource = captured["body"]["resources"][0]["resource"]
        assert resource.get("attr") == {"domain": "sales"}

    def test_resource_attr_absent_from_payload_when_not_provided(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            return _mock_cerbos()

        with patch("urllib.request.urlopen", side_effect=capture):
            client.check(principal, "api:chat", "default", "query")

        resource = captured["body"]["resources"][0]["resource"]
        assert "attr" not in resource

    def test_is_allowed_accepts_resource_attr(self) -> None:
        client = CerbosClient("http://localhost:3592")
        principal = _make_principal()

        with patch("urllib.request.urlopen", return_value=_mock_cerbos("EFFECT_ALLOW")):
            result = client.is_allowed(
                principal, "api:chat", "default", "query",
                resource_attr={"domain": "sales"},
            )
        assert result is True


# ---------------------------------------------------------------------------
# Policy YAML structure (validates the freeze contract is in the file)
# ---------------------------------------------------------------------------


class TestCerbosPolicyStructure:
    @pytest.fixture()
    def policy(self) -> dict:
        path = INFRA / "cerbos" / "policies" / "resource_api.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_policy_checks_department_in_allow_condition(self, policy: dict) -> None:
        rules = policy["resourcePolicy"]["rules"]
        allow_rules = [r for r in rules if r["effect"] == "EFFECT_ALLOW" and "query" in r["actions"]]
        assert allow_rules, "No ALLOW rule for query action"
        all_conditions = " ".join(
            str(r.get("condition", "")) for r in allow_rules
        )
        assert "department" in all_conditions, "ALLOW rules must reference P.attr.department"

    def test_policy_checks_clearance_in_allow_condition(self, policy: dict) -> None:
        rules = policy["resourcePolicy"]["rules"]
        allow_rules = [r for r in rules if r["effect"] == "EFFECT_ALLOW" and "query" in r["actions"]]
        all_conditions = " ".join(str(r.get("condition", "")) for r in allow_rules)
        assert "clearance" in all_conditions, "ALLOW rules must reference P.attr.clearance"

    def test_policy_has_domain_mismatch_deny_rule(self, policy: dict) -> None:
        rules = policy["resourcePolicy"]["rules"]
        deny_rules_yaml = yaml.dump(
            [r for r in rules if r["effect"] == "EFFECT_DENY" and "query" in r["actions"]]
        )
        assert "domain" in deny_rules_yaml, "Must have a DENY rule for domain mismatch"

    def test_policy_denies_viewer_role(self, policy: dict) -> None:
        rules = policy["resourcePolicy"]["rules"]
        viewer_deny = [
            r for r in rules
            if r["effect"] == "EFFECT_DENY" and "viewer" in r.get("roles", [])
        ]
        assert viewer_deny, "Viewer role must be explicitly denied"
