from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import oracledb


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
            try:
                self._set_scope(connection, department_id=department_id, principal_id=principal_id)
                with connection.cursor() as cursor:
                    cursor.execute(sql, parameters or {})
                    return list(cursor.fetchall())
            finally:
                self._clear_scope(connection)

    def fetch_scalar(self, sql: str) -> Any:
        with self._pool.acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                row = cursor.fetchone()
        return None if row is None else row[0]

    def _set_scope(self, connection: oracledb.Connection, *, department_id: str, principal_id: str) -> None:
        with connection.cursor() as cursor:
            cursor.callproc(self._context_package_call, [department_id, principal_id])

    def _clear_scope(self, connection: oracledb.Connection) -> None:
        with connection.cursor() as cursor:
            cursor.callproc(self._clear_context_call)
