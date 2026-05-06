"""Tests for time_parser — regex fallback (no LLM required).

Validates:
  - ParsedTimeFilter.to_sql_clause() generates correct SQL
  - _regex_parse handles diverse Vietnamese time expressions
  - LLM path gracefully skipped when AIAL_TIME_PARSER_PROVIDER is unset
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from orchestration.semantic.time_parser import (
    ParsedTimeFilter,
    _LATEST_RECORD,
    _NO_FILTER,
    _regex_parse,
    parse_time_expression,
)

TODAY = date(2026, 5, 6)  # fixed anchor for deterministic tests


# ─── ParsedTimeFilter.to_sql_clause ───────────────────────────────────────────

def test_to_sql_clause_today() -> None:
    tf = ParsedTimeFilter("today", date(2026, 5, 6), date(2026, 5, 7))
    assert tf.to_sql_clause() == "PERIOD_DATE >= DATE '2026-05-06' AND PERIOD_DATE < DATE '2026-05-07'"


def test_to_sql_clause_none_filter_returns_none() -> None:
    assert _NO_FILTER.to_sql_clause() is None


def test_to_sql_clause_latest_record_returns_none() -> None:
    assert _LATEST_RECORD.to_sql_clause() is None


def test_to_dict_none_returns_none() -> None:
    assert _NO_FILTER.to_dict() is None


def test_to_dict_latest_record() -> None:
    d = _LATEST_RECORD.to_dict()
    assert d is not None
    assert d["kind"] == "latest_record"
    assert "start" not in d or d.get("start") is None


def test_to_dict_has_start_end() -> None:
    tf = ParsedTimeFilter("today", date(2026, 5, 6), date(2026, 5, 7))
    d = tf.to_dict()
    assert d is not None
    assert d["start"] == "2026-05-06"
    assert d["end"] == "2026-05-07"


# ─── Regex: latest record ─────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Doanh thu có dữ liệu gần đây nhất là ngày nào?",
    "doanh thu gần đây nhất",
    "dữ liệu gần nhất là ngày nào",
    "thu nhập mới nhất",
    "du lieu gan nhat la ngay nao",
    "moi nhat la ngay nao",
])
def test_regex_latest_record(query: str) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "latest_record"
    assert result.to_sql_clause() is None


# ─── Regex: today / yesterday ─────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "Doanh thu hôm nay",
    "thu nhập hôm nay là bao nhiêu",
    "doanh thu hom nay",
    "ngày hôm nay doanh thu",
])
def test_regex_today(query: str) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "today"
    assert result.start == TODAY
    assert result.end == TODAY + timedelta(days=1)


@pytest.mark.parametrize("query", [
    "thu nhập hôm qua",
    "doanh thu hom qua",
    "ngày hôm qua",
    "bán hàng hôm qua",
])
def test_regex_yesterday(query: str) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "yesterday"
    assert result.start == TODAY - timedelta(days=1)
    assert result.end == TODAY


# ─── Regex: N days ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_n", [
    ("doanh thu 7 ngày gần đây", 7),
    ("7 ngay gan day", 7),
    ("30 ngày qua", 30),
    ("doanh thu 14 ngay truoc", 14),
])
def test_regex_n_days(query: str, expected_n: int) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "recent_days"
    assert result.start == TODAY - timedelta(days=expected_n - 1)
    assert result.end == TODAY + timedelta(days=1)


@pytest.mark.parametrize("query", [
    "mấy ngày nay",
    "gần đây",
    "vừa qua",
])
def test_regex_recent_7_days_generic(query: str) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "recent_days"
    assert result.start == TODAY - timedelta(days=6)


# ─── Regex: week ─────────────────────────────────────────────────────────────

def test_regex_current_week() -> None:
    # TODAY = 2026-05-06 (Wednesday, weekday=2)
    result = _regex_parse("doanh thu tuần này", today=TODAY)
    assert result.kind == "current_week"
    assert result.start == date(2026, 5, 4)   # Monday
    assert result.end == date(2026, 5, 11)    # next Monday


def test_regex_previous_week() -> None:
    result = _regex_parse("doanh thu tuần trước", today=TODAY)
    assert result.kind == "previous_week"
    assert result.start == date(2026, 4, 27)  # prev Monday
    assert result.end == date(2026, 5, 4)


# ─── Regex: N months ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_start_month", [
    ("doanh thu 3 tháng qua", 2),   # May 2026 - 3 months = Feb 2026
    ("3 thang qua", 2),
    ("doanh thu 6 tháng gần đây", 11),  # May 2026 - 6 months = Nov 2025
])
def test_regex_n_months(query: str, expected_start_month: int) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind in ("recent_months", "last_N_months")
    assert result.start is not None
    assert result.start.month == expected_start_month


# ─── Regex: month ────────────────────────────────────────────────────────────

def test_regex_current_month() -> None:
    result = _regex_parse("doanh thu tháng này", today=TODAY)
    assert result.kind == "current_month"
    assert result.start == date(2026, 5, 1)
    assert result.end == date(2026, 6, 1)


def test_regex_previous_month() -> None:
    result = _regex_parse("doanh thu tháng trước", today=TODAY)
    assert result.kind == "previous_month"
    assert result.start == date(2026, 4, 1)
    assert result.end == date(2026, 5, 1)


def test_regex_specific_month_number() -> None:
    result = _regex_parse("doanh thu tháng 3", today=TODAY)
    assert result.kind == "specific_month"
    assert result.start == date(2026, 3, 1)
    assert result.end == date(2026, 4, 1)


# ─── Regex: year ─────────────────────────────────────────────────────────────

def test_regex_current_year() -> None:
    result = _regex_parse("doanh thu năm nay", today=TODAY)
    assert result.kind == "current_year"
    assert result.start == date(2026, 1, 1)
    assert result.end == date(2027, 1, 1)


def test_regex_previous_year() -> None:
    result = _regex_parse("doanh thu năm trước", today=TODAY)
    assert result.kind == "previous_year"
    assert result.start == date(2025, 1, 1)
    assert result.end == date(2026, 1, 1)


def test_regex_nam_ngoai() -> None:
    result = _regex_parse("doanh thu năm ngoái", today=TODAY)
    assert result.kind == "previous_year"
    assert result.start == date(2025, 1, 1)


# ─── Regex: year + quarter ───────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_start,expected_end", [
    ("doanh thu quý 1 2026", date(2026, 1, 1), date(2026, 4, 1)),
    ("doanh thu Q2 2026", date(2026, 4, 1), date(2026, 7, 1)),
    ("doanh thu quý 3 2025", date(2025, 7, 1), date(2025, 10, 1)),
    ("doanh thu Q4 2025", date(2025, 10, 1), date(2026, 1, 1)),
])
def test_regex_quarter(query: str, expected_start: date, expected_end: date) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "quarter"
    assert result.start == expected_start
    assert result.end == expected_end


def test_regex_year_only() -> None:
    result = _regex_parse("doanh thu 2025", today=TODAY)
    assert result.kind == "year"
    assert result.start == date(2025, 1, 1)
    assert result.end == date(2026, 1, 1)


# ─── Regex: no filter ────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", [
    "doanh thu là gì",
    "định nghĩa doanh thu",
    "doanh thu thuần",
    "SUM NET REVENUE",
])
def test_regex_no_time_filter(query: str) -> None:
    result = _regex_parse(query, today=TODAY)
    assert result.kind == "none"
    assert result.to_sql_clause() is None


# ─── parse_time_expression (public API) ──────────────────────────────────────

def test_public_api_uses_regex_when_no_provider_configured(monkeypatch) -> None:
    monkeypatch.delenv("AIAL_TIME_PARSER_PROVIDER", raising=False)
    result = parse_time_expression("Doanh thu hôm nay", today=TODAY)
    assert result.kind == "today"
    assert result.start == TODAY


def test_public_api_latest_record_no_filter(monkeypatch) -> None:
    monkeypatch.delenv("AIAL_TIME_PARSER_PROVIDER", raising=False)
    result = parse_time_expression("dữ liệu gần nhất là ngày nào", today=TODAY)
    assert result.kind == "latest_record"
    assert result.to_sql_clause() is None


def test_public_api_llm_provider_env_missing_key_falls_back_to_regex(monkeypatch) -> None:
    """LLM provider configured but API key missing → regex fallback."""
    monkeypatch.setenv("AIAL_TIME_PARSER_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = parse_time_expression("Doanh thu hôm qua", today=TODAY)
    # Falls back to regex
    assert result.kind == "yesterday"


# ─── SQL clause correctness ───────────────────────────────────────────────────

def test_sql_clause_today_correct() -> None:
    result = _regex_parse("hôm nay", today=TODAY)
    sql = result.to_sql_clause()
    assert sql == "PERIOD_DATE >= DATE '2026-05-06' AND PERIOD_DATE < DATE '2026-05-07'"


def test_sql_clause_7_days_correct() -> None:
    result = _regex_parse("7 ngày gần đây", today=TODAY)
    sql = result.to_sql_clause()
    # start = today - 6 days = 2026-04-30
    assert "2026-04-30" in sql
    assert "2026-05-07" in sql  # exclusive end = tomorrow


def test_sql_clause_current_month_correct() -> None:
    result = _regex_parse("tháng này", today=TODAY)
    sql = result.to_sql_clause()
    assert "2026-05-01" in sql
    assert "2026-06-01" in sql


def test_sql_clause_q1_2026_correct() -> None:
    result = _regex_parse("quý 1 2026", today=TODAY)
    sql = result.to_sql_clause()
    assert "2026-01-01" in sql
    assert "2026-04-01" in sql
