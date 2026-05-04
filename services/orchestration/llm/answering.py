"""Provider selection for chatbot answer synthesis."""

from __future__ import annotations

import logging
from typing import Any

from rag.composition.nodes import RagChunk

from orchestration.llm.gemini import get_gemini_chat_service
from orchestration.llm.openai import get_openai_chat_service

logger = logging.getLogger(__name__)


async def generate_chat_answer(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None = None,
    memory_context: dict[str, Any] | None = None,
    preference_context: list[dict[str, Any]] | None = None,
    rag_chunks: list[RagChunk] | None = None,
    sql_rows: list[dict[str, Any]] | None = None,
    data_source: str | None = None,
) -> str | None:
    services = [
        get_openai_chat_service(),
        get_gemini_chat_service(),
    ]
    for service in services:
        if not service.enabled:
            continue
        try:
            answer = await service.generate_answer(
                query=query,
                semantic_context=semantic_context,
                memory_context=memory_context,
                preference_context=preference_context,
                rag_chunks=rag_chunks,
                sql_rows=sql_rows,
                data_source=data_source,
            )
        except Exception as exc:
            logger.warning("LLM provider %s failed: %s", service.__class__.__name__, exc)
            continue
        if answer:
            return answer
    return None
