"""Tests for Story 2A.3 — SQL Generation Guardrails + Query Governor."""

from __future__ import annotations

import pytest

from orchestration.sql_governor.guardrails import (
    QueryGovernor,
    SqlGuardrails,
    SqlGuardResult,
)


class TestSqlGuardrails:
    def test_blocks_drop_table(self) -> None:
        result = SqlGuardrails.validate("DROP TABLE employees")
        assert not result.allowed
        assert result.code == "SQL_UNSAFE_OPERATION"

    def test_blocks_insert(self) -> None:
        result = SqlGuardrails.validate("INSERT INTO orders VALUES (1, 'test')")
        assert not result.allowed
        assert result.code == "SQL_UNSAFE_OPERATION"

    def test_blocks_update(self) -> None:
        result = SqlGuardrails.validate("UPDATE accounts SET balance = 0")
        assert not result.allowed

    def test_blocks_delete(self) -> None:
        result = SqlGuardrails.validate("DELETE FROM audit_log")
        assert not result.allowed

    def test_blocks_dbms_injection(self) -> None:
        result = SqlGuardrails.validate("SELECT DBMS_PIPE.RECEIVE_MESSAGE('a', 1) FROM dual")
        assert not result.allowed
        assert result.code == "SQL_UNSAFE_OPERATION"

    def test_blocks_execute_immediate(self) -> None:
        result = SqlGuardrails.validate("BEGIN EXECUTE IMMEDIATE 'DROP TABLE x'; END;")
        assert not result.allowed

    def test_blocks_flashback(self) -> None:
        result = SqlGuardrails.validate("SELECT * FROM employees AS OF TIMESTAMP FLASHBACK")
        assert not result.allowed

    def test_blocks_database_links(self) -> None:
        result = SqlGuardrails.validate("SELECT * FROM employees@remote_db")
        assert not result.allowed

    def test_allows_valid_select(self) -> None:
        result = SqlGuardrails.validate(
            "SELECT department_id, SUM(salary) FROM employees WHERE year = 2024 GROUP BY department_id"
        )
        assert result.allowed

    def test_allows_select_with_join(self) -> None:
        result = SqlGuardrails.validate(
            "SELECT e.name, d.dept_name FROM employees e JOIN departments d ON e.dept_id = d.id WHERE e.active = 1"
        )
        assert result.allowed

    def test_case_insensitive_blocking(self) -> None:
        assert not SqlGuardrails.validate("drop table SENSITIVE_DATA").allowed
        assert not SqlGuardrails.validate("DbMs_Output.put_line('x')").allowed


class TestQueryGovernor:
    def test_appends_row_limit_when_absent(self) -> None:
        sql = "SELECT * FROM sales WHERE dept_id = 10"
        governed = QueryGovernor.apply(sql)
        assert "FETCH FIRST" in governed.upper() or "ROWNUM" in governed.upper()

    def test_does_not_duplicate_row_limit(self) -> None:
        sql = "SELECT * FROM sales FETCH FIRST 100 ROWS ONLY"
        governed = QueryGovernor.apply(sql)
        count = governed.upper().count("FETCH FIRST")
        assert count == 1

    def test_allowed_result_has_correct_type(self) -> None:
        result = SqlGuardrails.validate("SELECT 1 FROM dual")
        assert isinstance(result, SqlGuardResult)
        assert result.allowed
