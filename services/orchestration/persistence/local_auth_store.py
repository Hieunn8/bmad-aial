"""Persistent local username/password store for development auth."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

_TABLE_NAME = "aial_local_auth_users"
_HASH_PREFIX = "pbkdf2_sha256"
_DEFAULT_ADMIN_USERNAME = os.getenv("AIAL_LOCAL_ADMIN_USERNAME", "admin")
_DEFAULT_ADMIN_PASSWORD = os.getenv("AIAL_LOCAL_ADMIN_PASSWORD", "admin123!")
_DEFAULT_ADMIN_EMAIL = os.getenv("AIAL_LOCAL_ADMIN_EMAIL", "admin@aial.local")
_DEFAULT_ADMIN_DEPARTMENT = os.getenv("AIAL_LOCAL_ADMIN_DEPARTMENT", "engineering")
_RESET_DEFAULT_ADMIN_ON_START = os.getenv("AIAL_LOCAL_ADMIN_RESET_ON_START", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@dataclass(frozen=True)
class LocalAuthUser:
    username: str
    email: str
    department: str
    roles: tuple[str, ...]
    clearance: int
    password_hash: str
    disabled: bool
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "email": self.email,
            "department": self.department,
            "roles": list(self.roles),
            "clearance": self.clearance,
            "disabled": self.disabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def _hash_password(password: str, *, salt: bytes | None = None) -> str:
    resolved_salt = salt or os.urandom(16)
    iterations = 390_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt, iterations)
    return "$".join(
        [
            _HASH_PREFIX,
            str(iterations),
            base64.b64encode(resolved_salt).decode("ascii"),
            base64.b64encode(digest).decode("ascii"),
        ]
    )


def _verify_password(password: str, password_hash: str) -> bool:
    algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
    if algorithm != _HASH_PREFIX:
        return False
    salt = base64.b64decode(salt_b64.encode("ascii"))
    expected = _hash_password(password, salt=salt)
    return hmac.compare_digest(expected, password_hash)


class LocalAuthStore:
    def __init__(self, *, dsn: str | None) -> None:
        self._dsn = dsn.strip() if dsn else ""
        self._memory_users: dict[str, LocalAuthUser] = {}
        self._seed_default_admin()

    def _connect(self) -> Any | None:
        if not self._dsn:
            return None
        import psycopg

        connection = psycopg.connect(self._dsn)
        connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_TABLE_NAME} (
                username TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                department TEXT NOT NULL,
                roles_json JSONB NOT NULL,
                clearance INTEGER NOT NULL,
                password_hash TEXT NOT NULL,
                disabled BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        connection.commit()
        return connection

    def _seed_default_admin(self) -> None:
        existing_user = self.get_user(_DEFAULT_ADMIN_USERNAME)
        if existing_user is not None:
            if _RESET_DEFAULT_ADMIN_ON_START:
                self.update_user_password(
                    _DEFAULT_ADMIN_USERNAME,
                    _DEFAULT_ADMIN_PASSWORD,
                    email=_DEFAULT_ADMIN_EMAIL,
                    department=_DEFAULT_ADMIN_DEPARTMENT,
                    roles=["admin", "data_owner"],
                    clearance=3,
                    disabled=False,
                )
            return
        self.create_user(
            username=_DEFAULT_ADMIN_USERNAME,
            password=_DEFAULT_ADMIN_PASSWORD,
            email=_DEFAULT_ADMIN_EMAIL,
            department=_DEFAULT_ADMIN_DEPARTMENT,
            roles=["admin", "data_owner"],
            clearance=3,
        )

    def _row_to_user(self, row: Any) -> LocalAuthUser:
        return LocalAuthUser(
            username=str(row[0]),
            email=str(row[1]),
            department=str(row[2]),
            roles=tuple(json.loads(row[3]) if isinstance(row[3], str) else row[3]),
            clearance=int(row[4]),
            password_hash=str(row[5]),
            disabled=bool(row[6]),
            created_at=row[7],
            updated_at=row[8],
        )

    def get_user(self, username: str) -> LocalAuthUser | None:
        normalized = username.strip().casefold()
        connection = self._connect()
        if connection is None:
            return self._memory_users.get(normalized)
        try:
            row = connection.execute(
                f"""
                SELECT
                    username,
                    email,
                    department,
                    roles_json::text,
                    clearance,
                    password_hash,
                    disabled,
                    created_at,
                    updated_at
                FROM {_TABLE_NAME}
                WHERE lower(username) = %s
                """,
                (normalized,),
            ).fetchone()
            return None if row is None else self._row_to_user(row)
        finally:
            connection.close()

    def list_users(self) -> list[LocalAuthUser]:
        connection = self._connect()
        if connection is None:
            return sorted(self._memory_users.values(), key=lambda user: user.username)
        try:
            rows = connection.execute(
                f"""
                SELECT
                    username,
                    email,
                    department,
                    roles_json::text,
                    clearance,
                    password_hash,
                    disabled,
                    created_at,
                    updated_at
                FROM {_TABLE_NAME}
                ORDER BY username
                """
            ).fetchall()
            return [self._row_to_user(row) for row in rows]
        finally:
            connection.close()

    def create_user(
        self,
        *,
        username: str,
        password: str,
        email: str,
        department: str,
        roles: list[str],
        clearance: int,
    ) -> LocalAuthUser:
        normalized = username.strip()
        if not normalized:
            raise ValueError("username is required")
        if not password:
            raise ValueError("password is required")
        if self.get_user(normalized) is not None:
            raise ValueError("local auth user already exists")
        now = datetime.now(UTC)
        user = LocalAuthUser(
            username=normalized,
            email=email.strip(),
            department=department.strip(),
            roles=tuple(sorted({role.strip() for role in roles if role.strip()})),
            clearance=clearance,
            password_hash=_hash_password(password),
            disabled=False,
            created_at=now,
            updated_at=now,
        )
        connection = self._connect()
        if connection is None:
            self._memory_users[normalized.casefold()] = user
            return user
        try:
            connection.execute(
                f"""
                INSERT INTO {_TABLE_NAME} (
                    username, email, department, roles_json, clearance, password_hash, disabled, created_at, updated_at
                )
                VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                """,
                (
                    user.username,
                    user.email,
                    user.department,
                    json.dumps(list(user.roles)),
                    user.clearance,
                    user.password_hash,
                    user.disabled,
                    user.created_at,
                    user.updated_at,
                ),
            )
            connection.commit()
            return user
        finally:
            connection.close()

    def update_user_password(
        self,
        username: str,
        password: str,
        *,
        email: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
        clearance: int | None = None,
        disabled: bool | None = None,
    ) -> LocalAuthUser:
        user = self.get_user(username)
        if user is None:
            raise ValueError("local auth user not found")
        now = datetime.now(UTC)
        next_user = LocalAuthUser(
            username=user.username,
            email=(email.strip() if email is not None else user.email),
            department=(department.strip() if department is not None else user.department),
            roles=tuple(sorted({role.strip() for role in (roles if roles is not None else user.roles) if role.strip()})),
            clearance=clearance if clearance is not None else user.clearance,
            password_hash=_hash_password(password),
            disabled=user.disabled if disabled is None else disabled,
            created_at=user.created_at,
            updated_at=now,
        )
        connection = self._connect()
        if connection is None:
            self._memory_users[user.username.casefold()] = next_user
            return next_user
        try:
            connection.execute(
                f"""
                UPDATE {_TABLE_NAME}
                SET
                    email = %s,
                    department = %s,
                    roles_json = %s::jsonb,
                    clearance = %s,
                    password_hash = %s,
                    disabled = %s,
                    updated_at = %s
                WHERE lower(username) = %s
                """,
                (
                    next_user.email,
                    next_user.department,
                    json.dumps(list(next_user.roles)),
                    next_user.clearance,
                    next_user.password_hash,
                    next_user.disabled,
                    next_user.updated_at,
                    user.username.casefold(),
                ),
            )
            connection.commit()
            return next_user
        finally:
            connection.close()

    def verify_credentials(self, username: str, password: str) -> LocalAuthUser | None:
        user = self.get_user(username)
        if user is None or user.disabled:
            return None
        return user if _verify_password(password, user.password_hash) else None


@lru_cache(maxsize=1)
def get_local_auth_store() -> LocalAuthStore:
    return LocalAuthStore(dsn=os.getenv("DATABASE_URL", ""))
