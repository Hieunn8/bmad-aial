from __future__ import annotations

from unittest.mock import MagicMock, call

from data_connector.oracle_vpd import OracleVPDClient


class _CursorContext:
    def __init__(self, cursor: MagicMock) -> None:
        self._cursor = cursor

    def __enter__(self) -> MagicMock:
        return self._cursor

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _ConnectionContext:
    def __init__(self, connection: MagicMock) -> None:
        self._connection = connection

    def __enter__(self) -> MagicMock:
        return self._connection

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _build_client() -> tuple[OracleVPDClient, MagicMock, MagicMock]:
    pool = MagicMock()
    connection = MagicMock()
    cursor = MagicMock()
    connection.cursor.return_value = _CursorContext(cursor)
    pool.acquire.return_value = _ConnectionContext(connection)
    client = OracleVPDClient(
        pool,
        context_package_call="AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.SET_SCOPE",
        clear_context_call="AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.CLEAR_SCOPE",
    )
    return client, connection, cursor


def test_fetch_all_sets_and_clears_context() -> None:
    client, connection, cursor = _build_client()
    cursor.fetchall.return_value = [("sales",)]

    rows = client.fetch_all(
        "select scope_value from aial_vpd_owner.aial_vpd_rows",
        department_id="sales",
        principal_id="user-123",
    )

    assert rows == [("sales",)]
    assert cursor.callproc.mock_calls[:2] == [
        call("AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.SET_SCOPE", ["sales", "user-123"]),
        call("AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.CLEAR_SCOPE"),
    ]
    cursor.execute.assert_called_once()
    connection.cursor.assert_called()


def test_fetch_all_clears_context_on_query_failure() -> None:
    client, _, cursor = _build_client()
    cursor.execute.side_effect = RuntimeError("boom")

    try:
        client.fetch_all(
            "select scope_value from aial_vpd_owner.aial_vpd_rows",
            department_id="sales",
            principal_id="user-123",
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")

    assert cursor.callproc.mock_calls[:2] == [
        call("AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.SET_SCOPE", ["sales", "user-123"]),
        call("AIAL_VPD_OWNER.AIAL_VPD_CTX_PKG.CLEAR_SCOPE"),
    ]
