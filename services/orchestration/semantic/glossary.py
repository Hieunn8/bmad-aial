"""Business glossary and seed metric catalog."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

SEED_GLOSSARY: list[dict[str, object]] = [
    {
        "term": "doanh thu thuần",
        "definition": "Doanh thu bán hàng sau khi trừ chiết khấu và hàng trả lại",
        "formula": "SUM(NET_REVENUE)",
        "owner": "Finance",
        "freshness_rule": "daily",
        "aggregation": "sum",
        "grain": "daily_customer",
        "unit": "VND",
        "dimensions": ["date", "customer", "region", "channel"],
        "source": {"data_source": "oracle-finance", "schema": "FINANCE_ANALYTICS", "table": "F_SALES"},
    },
    {
        "term": "doanh thu",
        "definition": "Tổng doanh thu gộp từ bán hàng và cung cấp dịch vụ",
        "formula": "SUM(GROSS_REVENUE)",
        "owner": "Finance",
        "freshness_rule": "daily",
        "aggregation": "sum",
        "grain": "daily_customer",
        "unit": "VND",
        "dimensions": ["date", "customer", "region", "channel"],
        "source": {"data_source": "oracle-finance", "schema": "FINANCE_ANALYTICS", "table": "F_SALES"},
    },
    {
        "term": "lợi nhuận gộp",
        "definition": "Doanh thu thuần trừ giá vốn hàng bán",
        "formula": "SUM(NET_REVENUE) - SUM(COST_OF_GOODS_SOLD)",
        "owner": "Finance",
        "freshness_rule": "daily",
        "aggregation": "derived",
        "grain": "daily_customer",
        "unit": "VND",
        "dimensions": ["date", "customer", "region", "channel"],
        "source": {"data_source": "oracle-finance", "schema": "FINANCE_ANALYTICS", "table": "F_SALES"},
    },
    {
        "term": "số lượng khách hàng",
        "definition": "Tổng số khách hàng đang hoạt động trong kỳ",
        "formula": "COUNT(DISTINCT CUSTOMER_ID)",
        "owner": "Sales",
        "freshness_rule": "daily",
        "aggregation": "count_distinct",
        "grain": "daily_customer",
        "unit": "customers",
        "dimensions": ["date", "region", "channel"],
        "source": {"data_source": "oracle-sales", "schema": "SALES_ANALYTICS", "table": "F_CUSTOMER_ACTIVITY"},
    },
]

_SEED_INDEX: dict[str, dict[str, object]] = {str(entry["term"]).lower(): entry for entry in SEED_GLOSSARY}


class GlossaryRepository:
    """PostgreSQL-backed glossary repository."""

    def __init__(self, connection_factory: Callable[[], Any] | None) -> None:
        self._factory = connection_factory

    def find(self, term: str) -> dict[str, object] | None:
        normalized = term.strip().lower()
        if self._factory is None:
            if os.getenv("AIAL_SEED_SEMANTIC_GLOSSARY", "").strip().lower() in {"1", "true", "yes", "on"}:
                return _SEED_INDEX.get(normalized)
            return None
        with self._factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT term, definition, formula, owner, freshness_rule "
                    "FROM glossary_terms WHERE lower(term) = %s",
                    (normalized,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return {
            "term": row[0],
            "definition": row[1],
            "formula": row[2],
            "owner": row[3],
            "freshness_rule": row[4],
        }
