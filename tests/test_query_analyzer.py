"""Tests for query_analyzer — LLM-based full semantic understanding.

Tests use monkeypatch to inject mock LLM responses, so no real API key needed.
Covers: JSON parsing, term validation, time filter extraction, clarification,
        provider fallback, and integration with SemanticPlanner.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from orchestration.semantic.query_analyzer import (
    _build_metrics_block,
    _parse_response,
    _parse_time_filter,
    analyze_query,
)
from orchestration.semantic.resolver import SemanticPlannerOutput, SemanticResolveCandidate

TODAY = date(2026, 5, 6)


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_candidate(term: str, aliases: list[str] | None = None, examples: list[str] | None = None) -> SemanticResolveCandidate:
    return SemanticResolveCandidate(
        metric={
            "term": term,
            "aliases": aliases or [],
            "definition": f"Định nghĩa của {term}",
            "formula": "SUM(VALUE)",
            "dimensions": ["PERIOD_DATE", "REGION_CODE", "CHANNEL_CODE"],
            "examples": examples or [f"xem {term} tháng này"],
        },
        lexical_score=0.8,
        vector_score=0.7,
        merged_score=0.75,
        rerank_score=0.75,
    )


_REVENUE = _make_candidate(
    "doanh thu thuần",
    aliases=["doanh thu", "net revenue", "thu nhập", "bán hàng"],
    examples=["doanh thu tháng này", "thu nhập 7 ngày gần đây", "bức tranh kinh doanh"],
)
_PROFIT = _make_candidate(
    "lợi nhuận gộp",
    aliases=["gross margin", "lãi gộp"],
    examples=["lợi nhuận gộp quý này", "biên lợi nhuận theo khu vực"],
)
_BUDGET = _make_candidate(
    "doanh thu ngân sách",
    aliases=["budget revenue", "kế hoạch doanh thu"],
    examples=["ngân sách doanh thu năm nay"],
)


# ─── _build_metrics_block ─────────────────────────────────────────────────────

def test_metrics_block_contains_term() -> None:
    block = _build_metrics_block([_REVENUE])
    assert "doanh thu thuần" in block


def test_metrics_block_contains_aliases() -> None:
    block = _build_metrics_block([_REVENUE])
    assert "thu nhập" in block
    assert "bán hàng" in block


def test_metrics_block_contains_examples() -> None:
    block = _build_metrics_block([_REVENUE])
    assert "doanh thu tháng này" in block


def test_metrics_block_multiple_candidates() -> None:
    block = _build_metrics_block([_REVENUE, _PROFIT, _BUDGET])
    assert "doanh thu thuần" in block
    assert "lợi nhuận gộp" in block
    assert "doanh thu ngân sách" in block


# ─── _parse_time_filter ───────────────────────────────────────────────────────

def test_parse_time_filter_valid() -> None:
    result = _parse_time_filter({"kind": "today", "start": "2026-05-06", "end": "2026-05-07"})
    assert result is not None
    assert result["kind"] == "today"
    assert result["start"] == "2026-05-06"


def test_parse_time_filter_none_input() -> None:
    assert _parse_time_filter(None) is None


def test_parse_time_filter_kind_none() -> None:
    assert _parse_time_filter({"kind": "none"}) is None


def test_parse_time_filter_latest_record_no_start_allowed() -> None:
    result = _parse_time_filter({"kind": "latest_record", "start": None, "end": None})
    assert result is not None
    assert result["kind"] == "latest_record"


def test_parse_time_filter_missing_start_returns_none_for_regular() -> None:
    result = _parse_time_filter({"kind": "current_month", "start": None, "end": "2026-06-01"})
    assert result is None  # incomplete — let regex handle it


# ─── _parse_response ──────────────────────────────────────────────────────────

def test_parse_response_valid_resolved() -> None:
    llm_json = """{
        "selected_term": "doanh thu thuần",
        "intent": "metric_value",
        "time_filter": {"kind": "today", "start": "2026-05-06", "end": "2026-05-07"},
        "dimensions": [],
        "confidence": 0.92,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "clear revenue query for today"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE, _PROFIT])
    assert result is not None
    assert result.selected_term == "doanh thu thuần"
    assert result.intent == "metric_value"
    assert result.time_filter is not None
    assert result.time_filter["kind"] == "today"
    assert not result.needs_clarification


def test_parse_response_needs_clarification() -> None:
    llm_json = """{
        "selected_term": null,
        "intent": "metric_value",
        "time_filter": null,
        "dimensions": [],
        "confidence": 0.45,
        "needs_clarification": true,
        "clarification_question": "Bạn muốn xem `doanh thu thuần` hay `lợi nhuận gộp`?",
        "rationale": "ambiguous between revenue and profit"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE, _PROFIT])
    assert result is not None
    assert result.needs_clarification
    assert result.clarification_question is not None
    assert "Bạn" in result.clarification_question


def test_parse_response_invalid_term_discarded() -> None:
    """LLM hallucinated a term not in candidates → selected_term should be ignored."""
    llm_json = """{
        "selected_term": "doanh_thu_ao",
        "intent": "metric_value",
        "time_filter": null,
        "dimensions": [],
        "confidence": 0.9,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "hallucinated term"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE])
    assert result is not None
    # Falls back to first candidate since not needs_clarification
    assert result.selected_term == "doanh thu thuần"


def test_parse_response_low_confidence_auto_needs_clarification() -> None:
    """confidence < 0.55 → needs_clarification forced to True."""
    llm_json = """{
        "selected_term": "doanh thu thuần",
        "intent": "metric_value",
        "time_filter": null,
        "dimensions": [],
        "confidence": 0.40,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "low confidence"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE])
    assert result is not None
    assert result.needs_clarification


def test_parse_response_metric_breakdown_with_region() -> None:
    llm_json = """{
        "selected_term": "doanh thu thuần",
        "intent": "metric_breakdown",
        "time_filter": {"kind": "current_month", "start": "2026-05-01", "end": "2026-06-01"},
        "dimensions": ["REGION_CODE"],
        "confidence": 0.88,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "breakdown by region for current month"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE])
    assert result is not None
    assert result.intent == "metric_breakdown"
    assert "REGION_CODE" in result.dimensions


def test_parse_response_invalid_dimension_filtered() -> None:
    """Dimensions not in the allowed set are filtered out."""
    llm_json = """{
        "selected_term": "doanh thu thuần",
        "intent": "metric_breakdown",
        "time_filter": null,
        "dimensions": ["REGION_CODE", "INVALID_DIM", "CHANNEL_CODE"],
        "confidence": 0.85,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "test"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE])
    assert result is not None
    assert "INVALID_DIM" not in result.dimensions
    assert "REGION_CODE" in result.dimensions
    assert "CHANNEL_CODE" in result.dimensions


def test_parse_response_latest_date_intent() -> None:
    llm_json = """{
        "selected_term": "doanh thu thuần",
        "intent": "latest_date",
        "time_filter": {"kind": "latest_record"},
        "dimensions": [],
        "confidence": 0.95,
        "needs_clarification": false,
        "clarification_question": null,
        "rationale": "user asks for most recent date with data"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE])
    assert result is not None
    assert result.intent == "latest_date"
    assert result.time_filter is not None
    assert result.time_filter["kind"] == "latest_record"


def test_parse_response_malformed_json_returns_none() -> None:
    result = _parse_response("not json at all", candidates=[_REVENUE])
    assert result is None


def test_parse_response_auto_clarification_question_generated() -> None:
    """When needs_clarification but no clarification_question, one is auto-generated."""
    llm_json = """{
        "selected_term": null,
        "intent": "metric_value",
        "time_filter": null,
        "dimensions": [],
        "confidence": 0.3,
        "needs_clarification": true,
        "clarification_question": null,
        "rationale": "ambiguous"
    }"""
    result = _parse_response(llm_json, candidates=[_REVENUE, _PROFIT])
    assert result is not None
    assert result.clarification_question is not None
    assert len(result.clarification_question) > 10


# ─── analyze_query (provider routing) ────────────────────────────────────────

def test_analyze_query_returns_none_when_no_provider(monkeypatch) -> None:
    monkeypatch.delenv("AIAL_QUERY_ANALYZER_PROVIDER", raising=False)
    result = analyze_query(query="doanh thu hôm nay", candidates=[_REVENUE], today=TODAY)
    assert result is None  # triggers deterministic fallback


def test_analyze_query_returns_none_when_anthropic_key_missing(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = analyze_query(query="doanh thu hôm nay", candidates=[_REVENUE], today=TODAY)
    assert result is None


def test_analyze_query_returns_none_on_empty_candidates(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    result = analyze_query(query="doanh thu hôm nay", candidates=[], today=TODAY)
    assert result is None


def test_analyze_query_anthropic_success(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": """{
            "selected_term": "doanh thu thuần",
            "intent": "metric_value",
            "time_filter": {"kind": "today", "start": "2026-05-06", "end": "2026-05-07"},
            "dimensions": [],
            "confidence": 0.92,
            "needs_clarification": false,
            "clarification_question": null,
            "rationale": "clear today query"
        }"""}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp):
        result = analyze_query(query="Doanh thu hôm nay", candidates=[_REVENUE], today=TODAY)

    assert result is not None
    assert result.selected_term == "doanh thu thuần"
    assert result.time_filter is not None
    assert result.time_filter["start"] == "2026-05-06"
    assert not result.needs_clarification


def test_analyze_query_anthropic_clarification(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": """{
            "selected_term": null,
            "intent": "metric_value",
            "time_filter": null,
            "dimensions": [],
            "confidence": 0.45,
            "needs_clarification": true,
            "clarification_question": "Bạn muốn xem `doanh thu thuần` hay `lợi nhuận gộp`? Cả hai đều có sẵn.",
            "rationale": "ambiguous between revenue and profit metrics"
        }"""}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp):
        result = analyze_query(query="số liệu tháng này", candidates=[_REVENUE, _PROFIT], today=TODAY)

    assert result is not None
    assert result.needs_clarification
    assert "doanh thu thuần" in (result.clarification_question or "")


def test_analyze_query_openai_success(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": """{
            "selected_term": "lợi nhuận gộp",
            "intent": "metric_breakdown",
            "time_filter": {"kind": "current_month", "start": "2026-05-01", "end": "2026-06-01"},
            "dimensions": ["REGION_CODE"],
            "confidence": 0.89,
            "needs_clarification": false,
            "clarification_question": null,
            "rationale": "gross margin breakdown by region"
        }"""}}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.post", return_value=mock_resp):
        result = analyze_query(
            query="lãi gộp tháng này theo từng vùng miền",
            candidates=[_REVENUE, _PROFIT],
            today=TODAY,
        )

    assert result is not None
    assert result.selected_term == "lợi nhuận gộp"
    assert "REGION_CODE" in result.dimensions
    assert result.intent == "metric_breakdown"


def test_analyze_query_falls_back_when_api_raises(monkeypatch) -> None:
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    with patch("httpx.post", side_effect=Exception("network error")):
        result = analyze_query(query="doanh thu hôm nay", candidates=[_REVENUE], today=TODAY)

    assert result is None  # network error → None → deterministic fallback


# ─── Integration: SemanticPlanner uses QueryAnalyzer first ────────────────────

def test_semantic_planner_uses_query_analyzer_when_provider_set(monkeypatch) -> None:
    """End-to-end: SemanticPlanner priority chain includes QueryAnalyzer."""
    monkeypatch.setenv("AIAL_QUERY_ANALYZER_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "content": [{"text": """{
            "selected_term": "doanh thu thuần",
            "intent": "metric_value",
            "time_filter": {"kind": "yesterday", "start": "2026-05-05", "end": "2026-05-06"},
            "dimensions": [],
            "confidence": 0.93,
            "needs_clarification": false,
            "clarification_question": null,
            "rationale": "yesterday revenue query"
        }"""}]
    }
    mock_resp.raise_for_status = MagicMock()

    from orchestration.semantic.resolver import SemanticPlanner

    with patch("httpx.post", return_value=mock_resp):
        planner = SemanticPlanner()
        result = planner.plan(
            query="thu nhập hôm qua là bao nhiêu nhỉ",
            normalized_query="thu nhap hom qua la bao nhieu nhi",
            candidates=[_REVENUE],
        )

    assert result.selected_term == "doanh thu thuần"
    assert result.time_filter is not None
    assert result.time_filter["start"] == "2026-05-05"


def test_semantic_planner_falls_back_to_deterministic_when_no_provider(monkeypatch) -> None:
    monkeypatch.delenv("AIAL_QUERY_ANALYZER_PROVIDER", raising=False)
    monkeypatch.delenv("AIAL_SEMANTIC_PLANNER_PROVIDER", raising=False)

    from orchestration.semantic.resolver import SemanticPlanner

    planner = SemanticPlanner()
    result = planner.plan(
        query="doanh thu tháng này",
        normalized_query="doanh thu thang nay",
        candidates=[_REVENUE],
    )

    assert result.selected_term == "doanh thu thuần"
    assert result.time_filter is not None
    tf = result.time_filter
    assert tf["kind"] == "current_month"
