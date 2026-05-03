"""Keycloak JWT validation helpers.

Decodes and validates JWTs issued by Keycloak for the AIAL platform.
Enforces the principal attribute contract:
  Required (Epic 2A freeze): sub, email, department, roles[], clearance
  Optional extensions (Epic 4 ABAC): region, approval_authority
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

REQUIRED_CLAIMS = frozenset({"sub", "email", "department", "roles", "clearance"})


@dataclass(frozen=True)
class JWTClaims:
    sub: str
    email: str
    department: str
    roles: tuple[str, ...]
    clearance: int
    raw: dict[str, Any]
    # Epic 4 ABAC extensions — default-safe, never break Epic 2A code paths
    region: str = ""
    approval_authority: bool = False

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


class TokenValidationError(Exception):
    pass


@lru_cache(maxsize=4)
def _fetch_jwks(jwks_uri: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_uri)


@lru_cache(maxsize=4)
def _get_well_known_config(issuer: str) -> dict[str, Any]:
    url = f"{issuer}/.well-known/openid-configuration"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read())


def decode_jwt(
    token: str,
    *,
    issuer: str,
    audience: str | None = None,
    verify: bool = True,
) -> dict[str, Any]:
    if verify:
        config = _get_well_known_config(issuer)
        jwks_client = _fetch_jwks(config["jwks_uri"])
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        options: dict[str, Any] = {}
        if audience is None:
            options["verify_aud"] = False
        return jwt.decode(
            token,
            key=signing_key.key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            options=options,
        )
    return jwt.decode(token, options={"verify_signature": False})


def _parse_optional_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off", ""}:
            return False
        raise TokenValidationError("approval_authority must be a boolean-compatible value")
    if isinstance(value, int):
        if value in (0, 1):
            return bool(value)
        raise TokenValidationError("approval_authority integer claims must be 0 or 1")
    if value is None:
        return False
    raise TokenValidationError("approval_authority must be a boolean-compatible value")


def validate_token_claims(claims: dict[str, Any]) -> JWTClaims:
    missing = REQUIRED_CLAIMS - set(claims.keys())
    if missing:
        raise TokenValidationError(f"Missing required claims: {sorted(missing)}")

    empty = [c for c in REQUIRED_CLAIMS if claims.get(c) is None or claims.get(c) == ""]
    if empty:
        raise TokenValidationError(f"Empty required claims: {sorted(empty)}")

    roles = claims["roles"]
    if isinstance(roles, str):
        roles = [roles]
    if not isinstance(roles, list | tuple):
        raise TokenValidationError(f"roles must be a list, got {type(roles).__name__}")
    if not roles:
        raise TokenValidationError("Empty required claims: ['roles']")

    try:
        clearance = int(claims["clearance"])
    except (ValueError, TypeError) as e:
        raise TokenValidationError(f"clearance must be an integer: {e}") from e

    return JWTClaims(
        sub=str(claims["sub"]),
        email=str(claims["email"]),
        department=str(claims["department"]),
        roles=tuple(str(r) for r in roles),
        clearance=clearance,
        raw=claims,
        region=str(claims.get("region", "")),
        approval_authority=_parse_optional_bool(claims.get("approval_authority", False)),
    )
