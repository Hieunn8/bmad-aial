"""OpenAI chat integration for primary answer synthesis."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx
from rag.composition.nodes import RagChunk

from orchestration.llm.prompting import build_answer_prompt


class OpenAIChatService:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self._model = (model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")).strip()
        self._base_url = (base_url or os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self._timeout_seconds = timeout_seconds

    @property
    def enabled(self) -> bool:
        return bool(self._api_key and self._model)

    async def generate_answer(
        self,
        *,
        query: str,
        semantic_context: list[dict[str, Any]] | None = None,
        memory_context: dict[str, Any] | None = None,
        preference_context: list[dict[str, Any]] | None = None,
        rag_chunks: list[RagChunk] | None = None,
        sql_rows: list[dict[str, Any]] | None = None,
        data_source: str | None = None,
    ) -> str | None:
        if not self.enabled:
            return None

        payload = {
            "model": self._model,
            "instructions": (
                "You are the AIAL analytics assistant. "
                "Answer in Vietnamese. "
                "When document excerpts or SQL rows are provided, ground the answer in them. "
                "Do not fabricate facts that are not present in the provided context. "
                "If evidence is partial, say that clearly."
            ),
            "input": build_answer_prompt(
                query=query,
                semantic_context=semantic_context,
                memory_context=memory_context,
                preference_context=preference_context,
                rag_chunks=rag_chunks,
                sql_rows=sql_rows,
                data_source=data_source,
            ),
            "temperature": 0.2,
            "max_output_tokens": 1024,
        }

        url = f"{self._base_url}/responses"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            body = response.json()
        return self._extract_text(body)

    @staticmethod
    def _extract_text(body: dict[str, Any]) -> str | None:
        output_text = body.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        outputs = body.get("output")
        if not isinstance(outputs, list):
            return None

        parts: list[str] = []
        for item in outputs:
            content_items = item.get("content", [])
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if not parts:
            return None
        return "\n".join(parts)


@lru_cache(maxsize=1)
def get_openai_chat_service() -> OpenAIChatService:
    return OpenAIChatService()
