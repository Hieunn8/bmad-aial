"""Business Glossary — canonical term-to-formula registry.

S2 Interface Contract (Story 2A.2):
  GET /v1/glossary/{term} → GlossaryEntry | NotFoundResponse
  Epic 5B management CRUD extends this API without breaking changes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# ---------------------------------------------------------------------------
# Seed data — Phase 1 bootstrap (PostgreSQL-backed at runtime)
# ---------------------------------------------------------------------------

SEED_GLOSSARY: list[dict[str, str]] = [
    {
        "term": "doanh thu thuần",
        "definition": "Doanh thu bán hàng sau khi trừ chiết khấu thương mại và hàng bán bị trả lại",
        "formula": "SUM(NET_REVENUE)",
        "owner": "Finance",
        "freshness_rule": "daily",
    },
    {
        "term": "doanh thu",
        "definition": "Tổng doanh thu gộp từ bán hàng và cung cấp dịch vụ",
        "formula": "SUM(GROSS_REVENUE)",
        "owner": "Finance",
        "freshness_rule": "daily",
    },
    {
        "term": "lợi nhuận gộp",
        "definition": "Doanh thu thuần trừ giá vốn hàng bán",
        "formula": "SUM(NET_REVENUE) - SUM(COST_OF_GOODS_SOLD)",
        "owner": "Finance",
        "freshness_rule": "daily",
    },
    {
        "term": "số lượng khách hàng",
        "definition": "Tổng số khách hàng đang hoạt động trong kỳ",
        "formula": "COUNT(DISTINCT CUSTOMER_ID)",
        "owner": "Sales",
        "freshness_rule": "daily",
    },
]

_SEED_INDEX: dict[str, dict[str, str]] = {entry["term"].lower(): entry for entry in SEED_GLOSSARY}


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class GlossaryRepository:
    """PostgreSQL-backed glossary repository.

    `connection_factory` is injected so tests can pass `None` and mock `find()`.
    Production wires a psycopg2/asyncpg factory from the service config.
    """

    def __init__(self, connection_factory: Callable[[], Any] | None) -> None:
        self._factory = connection_factory

    def find(self, term: str) -> dict[str, str] | None:
        normalized = term.strip().lower()
        if self._factory is None:
            return _SEED_INDEX.get(normalized)
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
