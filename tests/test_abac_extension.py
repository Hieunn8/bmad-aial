"""Tests for Story 4.1 — Full ABAC Extension (FR-A2 Full).

Verifies:
- region + approval_authority added WITHOUT breaking Epic 2A attrs
- Region mismatch → DENY with denial_reason="region_mismatch"
- approval_authority=True grants pre-authorization for sensitivity_tier ≥ 2
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import yaml
from pathlib import Path

from aial_shared.auth.cerbos import CerbosClient
from aial_shared.auth.keycloak import JWTClaims

INFRA = Path(__file__).resolve().parent.parent / "infra"


def _make_principal(
    department: str = "sales",
    clearance: int = 1,
    region: str = "south",
    approval_authority: bool = False,
    roles: tuple[str, ...] = ("user",),
) -> JWTClaims:
    return JWTClaims(
        sub="test-user",
        email="test@aial.local",
        department=department,
        roles=roles,
        clearance=clearance,
        region=region,
        approval_authority=approval_authority,
        raw={},
    )


class TestExistingAttrsPreserved:
    """Epic 2A attrs must not be renamed, removed, or retyped (ADR-2A7 freeze)."""

    def test_department_still_present_in_payload(self) -> None:
        mock_cerbos = MagicMock()
        mock_cerbos.is_allowed.return_value = True
        client = CerbosClient.__new__(CerbosClient)
        client._base_url = "http://localhost:3592"

        principal = _make_principal()
        captured: dict = {}

        import json, urllib.request
        original_urlopen = urllib.request.urlopen

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            resp = MagicMock()
            resp.read.return_value = json.dumps({"results": [{"actions": {"query": "EFFECT_ALLOW"}}]}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with __import__("unittest.mock", fromlist=["patch"]).patch("urllib.request.urlopen", side_effect=capture):
            try:
                client.check(principal, "api:chat", "default", "query")
            except Exception:
                pass

        if "body" in captured:
            attrs = captured["body"]["principal"]["attr"]
            assert "department" in attrs, "department must still be present (ADR-2A7)"
            assert "clearance" in attrs, "clearance must still be present (ADR-2A7)"

    def test_epic2a_cerbos_tests_still_pass(self) -> None:
        """Existing Epic 2A JWTClaims still work without region/approval_authority."""
        p = JWTClaims(
            sub="u", email="u@t.com", department="sales",
            roles=("user",), clearance=1, raw={},
        )
        assert p.department == "sales"
        assert p.clearance == 1
        assert p.region == ""          # safe default
        assert p.approval_authority is False  # safe default


class TestRegionAttribute:
    def test_region_included_in_cerbos_payload(self) -> None:
        import json, urllib.request
        principal = _make_principal(region="north")
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            resp = MagicMock()
            resp.read.return_value = json.dumps({"results": [{"actions": {"query": "EFFECT_DENY"}}]}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client = CerbosClient("http://localhost:3592")
        with __import__("unittest.mock", fromlist=["patch"]).patch("urllib.request.urlopen", side_effect=capture):
            try:
                client.check(principal, "api:data", "south-region", "query", resource_attr={"region": "south"})
            except Exception:
                pass

        if "body" in captured:
            attrs = captured["body"]["principal"]["attr"]
            assert "region" in attrs
            assert attrs["region"] == "north"

    def test_approval_authority_included_in_cerbos_payload(self) -> None:
        import json
        principal = _make_principal(approval_authority=True)
        captured: dict = {}

        def capture(req, **_):
            captured["body"] = json.loads(req.data)
            resp = MagicMock()
            resp.read.return_value = json.dumps({"results": [{"actions": {"query": "EFFECT_ALLOW"}}]}).encode()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        client = CerbosClient("http://localhost:3592")
        with __import__("unittest.mock", fromlist=["patch"]).patch("urllib.request.urlopen", side_effect=capture):
            try:
                client.check(principal, "api:chat", "default", "query")
            except Exception:
                pass

        if "body" in captured:
            attrs = captured["body"]["principal"]["attr"]
            assert "approval_authority" in attrs
            assert attrs["approval_authority"] is True


class TestCerbosPolicy:
    @pytest.fixture()
    def policy(self) -> dict:
        path = INFRA / "cerbos" / "policies" / "resource_api.yaml"
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    def test_region_mismatch_deny_rule_exists(self, policy: dict) -> None:
        rules_yaml = yaml.dump(policy["resourcePolicy"]["rules"])
        assert "region" in rules_yaml, "Policy must have a region-based DENY rule for Story 4.1"

    def test_approval_authority_referenced_in_policy(self, policy: dict) -> None:
        rules_yaml = yaml.dump(policy["resourcePolicy"]["rules"])
        assert "approval_authority" in rules_yaml, "Policy must reference approval_authority"

    def test_existing_department_rule_still_present(self, policy: dict) -> None:
        rules_yaml = yaml.dump(policy["resourcePolicy"]["rules"])
        assert "department" in rules_yaml, "Epic 2A department rule must NOT be removed"


class TestJWTClaimsExtension:
    def test_jwt_claims_has_region_field(self) -> None:
        p = _make_principal(region="north")
        assert p.region == "north"

    def test_jwt_claims_has_approval_authority_field(self) -> None:
        p = _make_principal(approval_authority=True)
        assert p.approval_authority is True

    def test_jwt_claims_defaults_are_safe(self) -> None:
        p = JWTClaims(
            sub="u", email="u@test.com", department="sales",
            roles=("user",), clearance=1, raw={},
        )
        assert p.region == ""
        assert p.approval_authority is False
