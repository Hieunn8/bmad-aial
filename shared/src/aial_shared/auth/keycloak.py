"""Keycloak JWT validation helpers.

Decodes and validates JWTs issued by Keycloak for the AIAL platform.
Enforces the principal attribute contract: sub, email, department, roles[], clearance.
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

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


class TokenValidationError(Exception):
    pass


@lru_cache(maxsize=4)
def _fetch_jwks(jwks_uri: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(jwks_uri)


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
    if not isinstance(roles, (list, tuple)):
        raise TokenValidationError(f"roles must be a list, got {type(roles).__name__}")

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
    )
