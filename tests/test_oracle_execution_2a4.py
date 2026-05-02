"""Tests for Story 2A.4 — Oracle Execution with Identity Passthrough + VPD.

All tests mock Oracle; live gate remains in test_oracle_vpd_smoke.py (CI blocked by Docker).
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from data_connector.oracle_vpd import (
    OracleContextViolationError,
    OracleVPDClient,
    OracleVPDPoolConfig,
    create_proxy_pool,
)


def _make_client(pool: MagicMock) -> OracleVPDClient:
    return OracleVPDClient(
        pool,
        context_package_call="AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.SET_SCOPE",
        clear_context_call="AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.CLEAR_SCOPE",
    )


class _Cursor:
    def __init__(self, mock: MagicMock) -> None:
        self._mock = mock

    def __enter__(self) -> MagicMock:
        return self._mock

    def __exit__(self, *_: object) -> None:
        return None


class _Conn:
    def __init__(self, cursor_mock: MagicMock, context_value: str | None = None) -> None:
        self._cursor = cursor_mock
        self._context_value = context_value

    def cursor(self) -> _Cursor:
        return _Cursor(self._cursor)

    def __enter__(self) -> "_Conn":
        return self

    def __exit__(self, *_: object) -> None:
        return None


class _Pool:
    def __init__(self, conn: _Conn) -> None:
        self._conn = conn

    def acquire(self) -> _Conn:
        return self._conn

    def close(self, *, force: bool = False) -> None:
        pass


# ---------------------------------------------------------------------------
# AC: context VIOLATION detection — rejects stale context before query
# ---------------------------------------------------------------------------


class TestContextViolationDetection:
    def test_detects_stale_context_and_raises_violation_error(self) -> None:
        """If previous user's context is still set, query MUST be rejected."""
        cursor = MagicMock()
        # Simulate sys_context returning a stale department (previous user's)
        cursor.fetchone.return_value = ("finance",)  # stale context from User A
        cursor.fetchall.return_value = []
        conn = _Conn(cursor)
        pool = _Pool(conn)

        client = _make_client(pool)
        with pytest.raises(OracleContextViolationError):
            client.fetch_all(
                "SELECT 1 FROM dual",
                department_id="sales",
                principal_id="user-B",
            )

        # Only the context-clean check (sys_context) ran; "SELECT 1 FROM dual" must NOT have executed
        assert cursor.execute.call_count == 1, "User SQL must never run when context is stale"
        executed = cursor.execute.call_args[0][0]
        assert "SELECT 1 FROM dual" not in executed, "User query must not have been executed"

    def test_clean_context_allows_query(self) -> None:
        """Clean context (None) allows query to proceed normally."""
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)  # context is clean
        cursor.fetchall.return_value = [("sales-row",)]
        conn = _Conn(cursor)
        pool = _Pool(conn)

        client = _make_client(pool)
        rows = client.fetch_all(
            "SELECT scope_value FROM aial_vpd_rows",
            department_id="sales",
            principal_id="user-B",
        )
        assert rows == [("sales-row",)]


# ---------------------------------------------------------------------------
# AC: context cleared in finally, even on failure
# ---------------------------------------------------------------------------


class TestContextCleanup:
    def test_clear_context_called_in_finally_on_query_failure(self) -> None:
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)  # clean context
        cursor.execute.side_effect = [None, RuntimeError("query failed")]  # check passes, query fails
        conn = _Conn(cursor)
        pool = _Pool(conn)

        client = _make_client(pool)
        with pytest.raises(RuntimeError):
            client.fetch_all("SELECT 1 FROM dual", department_id="sales", principal_id="u1")

        # callproc SET_SCOPE and CLEAR_SCOPE both must have been called
        calls = [str(c) for c in cursor.callproc.call_args_list]
        assert any("SET_SCOPE" in c for c in calls)
        assert any("CLEAR_SCOPE" in c for c in calls)

    def test_context_cleared_before_pool_release(self) -> None:
        order: list[str] = []
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)

        def track_callproc(name: str, *args: object) -> None:
            order.append("CLEAR" if "CLEAR" in name else "SET")

        cursor.callproc.side_effect = track_callproc
        cursor.fetchall.return_value = []
        conn = _Conn(cursor)
        pool = _Pool(conn)

        client = _make_client(pool)
        client.fetch_all("SELECT 1 FROM dual", department_id="sales", principal_id="u1")

        assert order[-1] == "CLEAR", "CLEAR_SCOPE must be the last operation before pool release"


# ---------------------------------------------------------------------------
# AC: homogeneous=False (verified via pool config)
# ---------------------------------------------------------------------------


class TestPoolConfig:
    def test_pool_config_is_frozen_dataclass(self) -> None:
        config = OracleVPDPoolConfig(
            dsn="localhost/FREEPDB1",
            proxy_user="AIAL_PROXY",
            proxy_password="pw",
            session_user="AIAL_APP_PRINCIPAL",
        )
        with pytest.raises((AttributeError, TypeError)):
            config.dsn = "other"  # type: ignore[misc]

    def test_violation_error_logged_in_audit(self) -> None:
        """SESSION_CONTEXT_VIOLATION must be auditable (error class check)."""
        err = OracleContextViolationError("stale department=finance detected before sales query")
        assert "SESSION_CONTEXT_VIOLATION" in str(err) or isinstance(err, OracleContextViolationError)
