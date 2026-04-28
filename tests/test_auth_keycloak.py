"""Tests for Keycloak JWT validation helpers."""

import pytest

from aial_shared.auth.keycloak import (
    JWTClaims,
    TokenValidationError,
    validate_token_claims,
)

VALID_CLAIMS = {
    "sub": "user-123",
    "email": "user@aial.local",
    "department": "sales",
    "roles": ["user"],
    "clearance": 1,
}


class TestValidateTokenClaims:
    def test_valid_claims_returns_jwt_claims(self) -> None:
        result = validate_token_claims(VALID_CLAIMS)

        assert isinstance(result, JWTClaims)
        assert result.sub == "user-123"
        assert result.email == "user@aial.local"
        assert result.department == "sales"
        assert result.roles == ("user",)
        assert result.clearance == 1
        assert result.raw == VALID_CLAIMS

    def test_admin_role_detected(self) -> None:
        claims = {**VALID_CLAIMS, "roles": ["admin", "user"]}
        result = validate_token_claims(claims)
        assert result.is_admin is True

    def test_non_admin_role_detected(self) -> None:
        result = validate_token_claims(VALID_CLAIMS)
        assert result.is_admin is False

    def test_missing_sub_raises_error(self) -> None:
        claims = {k: v for k, v in VALID_CLAIMS.items() if k != "sub"}
        with pytest.raises(TokenValidationError, match="sub"):
            validate_token_claims(claims)

    def test_missing_email_raises_error(self) -> None:
        claims = {k: v for k, v in VALID_CLAIMS.items() if k != "email"}
        with pytest.raises(TokenValidationError, match="email"):
            validate_token_claims(claims)

    def test_missing_department_raises_error(self) -> None:
        claims = {k: v for k, v in VALID_CLAIMS.items() if k != "department"}
        with pytest.raises(TokenValidationError, match="department"):
            validate_token_claims(claims)

    def test_missing_roles_raises_error(self) -> None:
        claims = {k: v for k, v in VALID_CLAIMS.items() if k != "roles"}
        with pytest.raises(TokenValidationError, match="roles"):
            validate_token_claims(claims)

    def test_missing_clearance_raises_error(self) -> None:
        claims = {k: v for k, v in VALID_CLAIMS.items() if k != "clearance"}
        with pytest.raises(TokenValidationError, match="clearance"):
            validate_token_claims(claims)

    def test_empty_department_raises_error(self) -> None:
        claims = {**VALID_CLAIMS, "department": ""}
        with pytest.raises(TokenValidationError, match="Empty required claims"):
            validate_token_claims(claims)

    def test_empty_roles_raises_error(self) -> None:
        claims = {**VALID_CLAIMS, "roles": []}
        with pytest.raises(TokenValidationError, match="Empty required claims"):
            validate_token_claims(claims)

    def test_roles_as_string_converted_to_list(self) -> None:
        claims = {**VALID_CLAIMS, "roles": "admin"}
        result = validate_token_claims(claims)
        assert result.roles == ("admin",)

    def test_invalid_roles_type_raises_error(self) -> None:
        claims = {**VALID_CLAIMS, "roles": 42}
        with pytest.raises(TokenValidationError, match="roles must be a list"):
            validate_token_claims(claims)

    def test_clearance_as_string_converted(self) -> None:
        claims = {**VALID_CLAIMS, "clearance": "2"}
        result = validate_token_claims(claims)
        assert result.clearance == 2

    def test_invalid_clearance_raises_error(self) -> None:
        claims = {**VALID_CLAIMS, "clearance": "not-a-number"}
        with pytest.raises(TokenValidationError, match="clearance must be an integer"):
            validate_token_claims(claims)

    def test_jwt_claims_is_immutable(self) -> None:
        result = validate_token_claims(VALID_CLAIMS)
        with pytest.raises(AttributeError):
            result.sub = "other"  # type: ignore[misc]

    def test_multiple_missing_claims_reported(self) -> None:
        claims = {"sub": "user-123"}
        with pytest.raises(TokenValidationError, match="Missing required claims"):
            validate_token_claims(claims)
