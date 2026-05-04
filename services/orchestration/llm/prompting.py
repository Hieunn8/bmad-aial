"""Shared prompt construction helpers for LLM answer synthesis."""

from __future__ import annotations

import json
from typing import Any

from rag.composition.nodes import RagChunk


def truncate_text(value: str, limit: int = 600) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}..."


def render_rows(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not rows:
        return []
    return rows[:3]


def render_rag_chunks(rag_chunks: list[RagChunk] | None) -> list[dict[str, Any]]:
    if not rag_chunks:
        return []
    rendered: list[dict[str, Any]] = []
    for chunk in rag_chunks[:5]:
        rendered.append(
            {
                "document_id": chunk.document_id,
                "title": chunk.source_name,
                "page": chunk.page_number,
                "department": chunk.department,
                "score": round(chunk.score, 4),
                "excerpt": truncate_text(chunk.chunk_text, 700),
            }
        )
    return rendered


def build_answer_prompt(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    memory_context: dict[str, Any] | None,
    preference_context: list[dict[str, Any]] | None,
    rag_chunks: list[RagChunk] | None,
    sql_rows: list[dict[str, Any]] | None,
    data_source: str | None,
) -> str:
    prompt_payload = {
        "user_query": query,
        "semantic_context": semantic_context or [],
        "memory_summaries": (memory_context or {}).get("summaries", [])[:5],
        "user_preferences": preference_context or [],
        "sql_data_source": data_source,
        "sql_rows_sample": render_rows(sql_rows),
        "rag_sources": render_rag_chunks(rag_chunks),
        "instructions": [
            "Tra loi ngan gon, truc tiep, bang tieng Viet.",
            "Neu co nguon tai lieu, uu tien dua vao nguon do.",
            "Neu co du lieu bang, neu ro do la du lieu he thong.",
            "Neu thieu du lieu de ket luan chac chan, noi ro muc do chac chan.",
        ],
    }
    return json.dumps(prompt_payload, ensure_ascii=False)
