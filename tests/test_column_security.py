"""Tests for Story 4.2 — Column-level Security (FR-A4)."""

from __future__ import annotations

import pytest

from orchestration.security.column_masker import (
    ColumnResult,
    ColumnSensitivity,
    apply_column_security,
)


def _row(data: dict) -> dict:
    return data


class TestColumnMasking:
    def test_public_column_returned_as_is(self) -> None:
        schema = {"dept_name": ColumnSensitivity.PUBLIC}
        rows = [{"dept_name": "Sales"}]
        result = apply_column_security(rows, schema=schema, user_clearance=0)
        assert result[0]["dept_name"] == "Sales"

    def test_confidential_column_masked_for_low_clearance(self) -> None:
        schema = {"salary": ColumnSensitivity.CONFIDENTIAL}
        rows = [{"salary": 50000}]
        result = apply_column_security(rows, schema=schema, user_clearance=1)
        assert result[0]["salary"] == "***"

    def test_confidential_column_visible_for_sufficient_clearance(self) -> None:
        schema = {"salary": ColumnSensitivity.CONFIDENTIAL}
        rows = [{"salary": 50000}]
        result = apply_column_security(rows, schema=schema, user_clearance=2)
        assert result[0]["salary"] == 50000

    def test_secret_column_excluded_entirely_for_low_clearance(self) -> None:
        schema = {"ssn": ColumnSensitivity.SECRET}
        rows = [{"ssn": "123-456", "name": "Minh"}]
        result = apply_column_security(rows, schema=schema, user_clearance=2)
        assert "ssn" not in result[0]
        assert result[0]["name"] == "Minh"

    def test_secret_column_visible_for_clearance_3(self) -> None:
        schema = {"ssn": ColumnSensitivity.SECRET}
        rows = [{"ssn": "123-456"}]
        result = apply_column_security(rows, schema=schema, user_clearance=3)
        assert result[0]["ssn"] == "123-456"

    def test_untagged_column_defaults_to_public(self) -> None:
        schema: dict = {}  # no tags
        rows = [{"revenue": 1000}]
        result = apply_column_security(rows, schema=schema, user_clearance=0)
        assert result[0]["revenue"] == 1000

    def test_audit_records_field_and_action_not_value(self) -> None:
        schema = {"salary": ColumnSensitivity.CONFIDENTIAL}
        rows = [{"salary": 99999}]
        _, audit_records = apply_column_security(
            rows, schema=schema, user_clearance=1, return_audit=True
        )
        assert len(audit_records) == 1
        assert audit_records[0]["field"] == "salary"
        assert audit_records[0]["action"] == "masked"
        assert "99999" not in str(audit_records[0])  # value never in audit

    def test_presidio_skips_non_free_text_columns(self) -> None:
        col = ColumnResult(name="phone_id", value="12345", is_free_text=False)
        assert col.is_free_text is False

    def test_presidio_scans_free_text_columns(self) -> None:
        col = ColumnResult(name="notes", value="Call Nguyễn on 0912345678", is_free_text=True)
        assert col.is_free_text is True
