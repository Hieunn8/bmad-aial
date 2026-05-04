"""Local JWT issuance and verification helpers for development auth."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

LOCAL_AUTH_ISSUER = "aial-local"


def issue_local_token(
    *,
    secret: str,
    subject: str,
    email: str,
    department: str,
    roles: list[str],
    clearance: int,
    token_use: str,
    expires_in_seconds: int,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "iss": LOCAL_AUTH_ISSUER,
        "sub": subject,
        "email": email,
        "department": department,
        "roles": roles,
        "clearance": clearance,
        "token_use": token_use,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_local_token(token: str, *, secret: str, token_use: str | None = None) -> dict[str, Any]:
    payload = jwt.decode(token, secret, algorithms=["HS256"], issuer=LOCAL_AUTH_ISSUER)
    if token_use is not None and payload.get("token_use") != token_use:
        raise jwt.InvalidTokenError(f"expected token_use={token_use}")
    return payload


def peek_token_issuer(token: str) -> str | None:
    payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    issuer = payload.get("iss")
    return str(issuer) if issuer else None
