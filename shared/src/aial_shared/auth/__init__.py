"""AIAL authentication and authorization utilities."""

from aial_shared.auth.cerbos import AuthzResult, CerbosClient
from aial_shared.auth.fastapi_deps import (
    get_current_user,
    require_permission,
    reset_cerbos_client_cache,
)
from aial_shared.auth.keycloak import JWTClaims, TokenValidationError, decode_jwt, validate_token_claims
from aial_shared.auth.local_tokens import LOCAL_AUTH_ISSUER, decode_local_token, issue_local_token, peek_token_issuer

__all__ = [
    "AuthzResult",
    "CerbosClient",
    "JWTClaims",
    "LOCAL_AUTH_ISSUER",
    "TokenValidationError",
    "decode_jwt",
    "decode_local_token",
    "get_current_user",
    "issue_local_token",
    "peek_token_issuer",
    "require_permission",
    "reset_cerbos_client_cache",
    "validate_token_claims",
]
