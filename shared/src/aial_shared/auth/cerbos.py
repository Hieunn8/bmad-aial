"""Cerbos authorization client for AIAL.

Provides a thin wrapper around the Cerbos HTTP API (v0.38+) for checking
resource permissions using the principal attributes contract.

Uses POST /api/check/resources — the current CheckResources endpoint.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any

from aial_shared.auth.keycloak import JWTClaims


@dataclass(frozen=True)
class AuthzResult:
    allowed: bool
    resource: str
    action: str
    principal_id: str


class CerbosClient:
    def __init__(self, base_url: str = "http://localhost:3592") -> None:
        self._base_url = base_url.rstrip("/")

    def check(
        self,
        principal: JWTClaims,
        resource_kind: str,
        resource_id: str,
        action: str,
        *,
        resource_attr: dict[str, str] | None = None,
    ) -> AuthzResult:
        resource_entry: dict[str, Any] = {
            "kind": resource_kind,
            "id": resource_id,
        }
        if resource_attr:
            resource_entry["attr"] = resource_attr

        payload = {
            "requestId": f"{principal.sub}:{resource_kind}:{action}",
            "principal": {
                "id": principal.sub,
                "roles": list(principal.roles),
                "attr": {
                    "department": principal.department,
                    "clearance": str(principal.clearance),
                },
            },
            "resources": [{"resource": resource_entry, "actions": [action]}],
        }

        url = f"{self._base_url}/api/check/resources"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())

        effect = _extract_effect(result, action)
        return AuthzResult(
            allowed=effect == "EFFECT_ALLOW",
            resource=resource_kind,
            action=action,
            principal_id=principal.sub,
        )

    def is_allowed(
        self,
        principal: JWTClaims,
        resource_kind: str,
        resource_id: str,
        action: str,
        *,
        resource_attr: dict[str, str] | None = None,
    ) -> bool:
        return self.check(principal, resource_kind, resource_id, action, resource_attr=resource_attr).allowed


def _extract_effect(result: dict[str, Any], action: str) -> str:
    results = result.get("results", [])
    if not results:
        return "EFFECT_DENY"
    actions = results[0].get("actions", {})
    return actions.get(action, "EFFECT_DENY")
