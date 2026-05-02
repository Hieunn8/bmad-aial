"""Oracle VPD connector — Story 1.8 (pool) + Story 2A.4 (identity passthrough + violation detection).

Security invariants (2A.4 ACs):
  1. Before setting User B's context, DETECT if User A's context is still present.
     If stale → OracleContextViolationError raised, Oracle query NEVER executes.
  2. _clear_scope called in finally block (not else) — guaranteed cleanup on any exit.
  3. Pool uses homogeneous=False — each request sets its own proxy context.
  4. Service account is per-service read-only, never shared DBA.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import oracledb

logger = logging.getLogger(__name__)

_VPD_CTX_NAMESPACE = "AIAL_VPD_CTX"
_CTX_CHECK_SQL = f"SELECT sys_context('{_VPD_CTX_NAMESPACE}', 'DEPARTMENT_ID') FROM dual"  # noqa: S608


class OracleContextViolationError(RuntimeError):
    """Raised when SESSION_CONTEXT_VIOLATION detected (stale context from previous user).

    Oracle query is NEVER executed when this is raised. Must be audited.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(f"SESSION_CONTEXT_VIOLATION: {detail}")


@dataclass(frozen=True)
class OracleVPDPoolConfig:
    dsn: str
    proxy_user: str
    proxy_password: str
    session_user: str
    min_connections: int = 1
    max_connections: int = 1
    increment: int = 0


def create_proxy_pool(config: OracleVPDPoolConfig) -> oracledb.ConnectionPool:
    return oracledb.create_pool(
        user=f"{config.proxy_user}[{config.session_user}]",
        password=config.proxy_password,
        dsn=config.dsn,
        min=config.min_connections,
        max=config.max_connections,
        increment=config.increment,
        homogeneous=False,
    )


class OracleVPDClient:
    def __init__(
        self,
        pool: oracledb.ConnectionPool,
        *,
        context_package_call: str,
        clear_context_call: str,
    ) -> None:
        self._pool = pool
        self._context_package_call = context_package_call
        self._clear_context_call = clear_context_call

    @property
    def pool(self) -> oracledb.ConnectionPool:
        return self._pool

    def close(self) -> None:
        self._pool.close(force=True)

    def fetch_all(
        self,
        sql: str,
        *,
        department_id: str,
        principal_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[tuple[Any, ...]]:
        with self._pool.acquire() as connection:
            # AC 2A.4 #1: Detect stale context BEFORE setting new context
            self._assert_context_clean(connection, expected_principal=principal_id)
            try:
                self._set_scope(connection, department_id=department_id, principal_id=principal_id)
                with connection.cursor() as cursor:
                    cursor.execute(sql, parameters or {})
                    return list(cursor.fetchall())
            finally:
                # AC 2A.4 #2: clear in finally — guaranteed even on exception
                self._clear_scope(connection)

    def fetch_scalar(self, sql: str) -> Any:
        with self._pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
        return None if row is None else row[0]

    def _assert_context_clean(self, connection: oracledb.Connection, *, expected_principal: str) -> None:
        """Raise OracleContextViolationError if a previous user's context is still set."""
        with connection.cursor() as cursor:
            cursor.execute(_CTX_CHECK_SQL)
            row = cursor.fetchone()
        stale = row[0] if row else None
        if stale is not None:
            logger.error(
                "SESSION_CONTEXT_VIOLATION stale=%s principal=%s", stale, expected_principal
            )
            raise OracleContextViolationError(
                f"stale department={stale!r} found before context set for principal={expected_principal!r}"
            )

    def _set_scope(self, connection: oracledb.Connection, *, department_id: str, principal_id: str) -> None:
        with connection.cursor() as cursor:
            cursor.callproc(self._context_package_call, [department_id, principal_id])

    def _clear_scope(self, connection: oracledb.Connection) -> None:
        with connection.cursor() as cursor:
            cursor.callproc(self._clear_context_call)
