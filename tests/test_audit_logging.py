"""Tests for Story 2A.8 — Query Lifecycle Audit Logging."""

from __future__ import annotations

import hashlib
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from orchestration.audit.logger import AuditEvent, AuditLogger


class TestAuditEvent:
    def test_sql_hash_is_sha256(self) -> None:
        sql = "SELECT * FROM sales"
        expected = hashlib.sha256(sql.encode()).hexdigest()
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text=sql,
            data_sources=["sales_table"],
            rows_returned=5,
            latency_ms=120,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        assert event.sql_hash == expected

    def test_raw_sql_not_stored_for_sensitive_query(self) -> None:
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="PII_TIER_1",
            sql_text="SELECT name, phone FROM customers",
            data_sources=["customers"],
            rows_returned=1,
            latency_ms=50,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        assert event.sql_hash is not None
        assert event.stored_sql is None

    def test_non_sensitive_query_stores_sql(self) -> None:
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text="SELECT revenue FROM sales_summary",
            data_sources=["sales_summary"],
            rows_returned=10,
            latency_ms=80,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        assert event.stored_sql == "SELECT revenue FROM sales_summary"

    def test_denial_event_logs_reason(self) -> None:
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text=None,
            data_sources=[],
            rows_returned=0,
            latency_ms=10,
            policy_decision="DENY",
            status="DENIED",
            denial_reason="department_mismatch",
        )
        assert event.status == "DENIED"
        assert event.denial_reason == "department_mismatch"
        assert event.sql_hash is None

    def test_event_never_stores_raw_result_values(self) -> None:
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text="SELECT 1",
            data_sources=[],
            rows_returned=1,
            latency_ms=5,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        event_dict = event.to_log_dict()
        assert "result_values" not in event_dict
        assert "raw_result" not in event_dict


class TestAuditLogger:
    def test_logger_calls_write_with_event(self) -> None:
        mock_writer = MagicMock()
        logger = AuditLogger(writer=mock_writer)
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text="SELECT 1",
            data_sources=["dual"],
            rows_returned=1,
            latency_ms=5,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        logger.log(event)
        mock_writer.write.assert_called_once()

    def test_logger_write_never_includes_raw_results(self) -> None:
        written: list[dict] = []

        class CapturingWriter:
            def write(self, d: dict) -> None:
                written.append(d)

        logger = AuditLogger(writer=CapturingWriter())
        event = AuditEvent(
            request_id=str(uuid4()),
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="query",
            sensitivity_tier="LOW",
            sql_text="SELECT 1",
            data_sources=[],
            rows_returned=1,
            latency_ms=5,
            policy_decision="ALLOW",
            status="SUCCESS",
        )
        logger.log(event)
        assert written
        assert "raw_result" not in written[0]
        assert "result_values" not in written[0]
