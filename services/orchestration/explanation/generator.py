"""SQL Explanation Generator — Story 2B.1 (FR-O5).

Generates plain-Vietnamese explanations for Oracle query results.
Raw SQL is never shown by default (progressive disclosure via "Xem SQL gốc").
Explanations cached alongside query results.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ExplanationConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


_UNCERTAINTY_MESSAGES = {
    ExplanationConfidence.MEDIUM: "Đây là giải thích ước tính — độ tin cậy: Trung bình",
    ExplanationConfidence.LOW: "Đây là giải thích ước tính — độ tin cậy: Thấp",
}

# Simple patterns for extracting readable info from SQL
_TABLE_RE = re.compile(r"\bFROM\s+(\w+)", re.IGNORECASE)
_JOIN_RE = re.compile(r"\bJOIN\s+(\w+)", re.IGNORECASE)
_WHERE_RE = re.compile(r"\bWHERE\s+(.+?)(?:\bGROUP|\bORDER|\bHAVING|\bFETCH|$)", re.IGNORECASE | re.DOTALL)
_AGG_RE = re.compile(r"\b(SUM|COUNT|AVG|MAX|MIN)\s*\(([^)]+)\)", re.IGNORECASE)

_TABLE_LABELS: dict[str, str] = {
    "sales_summary": "Bảng tổng hợp doanh thu",
    "orders": "Bảng đơn hàng",
    "customers": "Bảng khách hàng",
    "employees": "Bảng nhân viên",
    "departments": "Bảng phòng ban",
    "dual": "Bảng hệ thống Oracle",
}


@dataclass
class SqlExplanation:
    data_source: str
    formula_description: str | None
    filters_applied: list[str]
    confidence: ExplanationConfidence
    raw_sql: str | None = None

    @property
    def uncertainty_message(self) -> str | None:
        return _UNCERTAINTY_MESSAGES.get(self.confidence)

    def to_response_dict(self, *, include_raw_sql: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "data_source": self.data_source,
            "formula_description": self.formula_description,
            "filters_applied": self.filters_applied,
            "confidence": self.confidence.value,
            "uncertainty_message": self.uncertainty_message,
            "raw_sql": None,
        }
        if include_raw_sql and self.raw_sql:
            d["raw_sql"] = self.raw_sql
            d["raw_sql_disclaimer"] = "SQL được kiểm tra an toàn trước khi thực thi"
        return d


_EXPLANATION_CACHE: dict[tuple[str, tuple[tuple[str, str], ...]], SqlExplanation] = {}


def _cached_explain(sql: str, metric_context: tuple[tuple[str, str], ...]) -> SqlExplanation | None:
    return _EXPLANATION_CACHE.get((sql, metric_context))


def _store_explain(sql: str, metric_context: tuple[tuple[str, str], ...], result: SqlExplanation) -> None:
    if len(_EXPLANATION_CACHE) < 256:
        _EXPLANATION_CACHE[(sql, metric_context)] = result


class SqlExplanationGenerator:
    """Rule-based SQL explanation generator for walking skeleton.

    Epic 4+ replaces this with LLM-backed compose_response node.
    Results are cached by normalized SQL string.
    """

    def explain(self, sql: str, metric_context: tuple[tuple[str, str], ...] = ()) -> SqlExplanation:
        cached = _cached_explain(sql, metric_context)
        if cached is not None:
            return cached
        context = dict(metric_context)
        tables = _TABLE_RE.findall(sql) + _JOIN_RE.findall(sql)
        data_source = ", ".join(
            _TABLE_LABELS.get(t.lower(), t.upper()) for t in dict.fromkeys(tables)
        ) or "Nguồn dữ liệu Oracle"

        agg_matches = _AGG_RE.findall(sql)
        if context.get("formula"):
            formula = context.get("formula", "")
            formula_desc = f"{context.get('term', '')} = {formula}"
        elif agg_matches:
            fn, col = agg_matches[0]
            formula_desc = f"{fn.upper()}({col.strip()}) — tổng hợp dữ liệu"
        else:
            formula_desc = None

        filters: list[str] = []
        where_match = _WHERE_RE.search(sql)
        if where_match:
            raw_where = where_match.group(1).strip()
            for clause in re.split(r"\bAND\b", raw_where, flags=re.IGNORECASE):
                clause = clause.strip()
                if clause:
                    filters.append(clause[:80])

        confidence = ExplanationConfidence.HIGH if (tables and agg_matches) else ExplanationConfidence.MEDIUM

        result = SqlExplanation(
            data_source=data_source,
            formula_description=formula_desc,
            filters_applied=filters,
            confidence=confidence,
            raw_sql=sql,
        )
        _store_explain(sql, metric_context, result)
        return result

    def explain_kw(self, *, sql: str, metric_context: dict[str, str] | None = None) -> SqlExplanation:
        ctx_tuple = tuple(sorted((metric_context or {}).items()))
        return self.explain(sql, ctx_tuple)
