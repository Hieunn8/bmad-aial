"""Gemini chat integration for optional answer synthesis fallback."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import httpx
from rag.composition.nodes import RagChunk

from orchestration.llm.prompting import build_answer_prompt


class GeminiChatService:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._api_key = (api_key or os.getenv("GEMINI_API_KEY", "")).strip()
        self._model = (model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")).strip()
        self._base_url = (
            base_url or os.getenv("GEMINI_API_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")
        ).rstrip("/")
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
            "system_instruction": {
                "parts": [
                    {
                        "text": (
                            "You are the AIAL analytics assistant. "
                            "Answer in Vietnamese. "
                            "When document excerpts or SQL rows are provided, ground the answer in them. "
                            "Do not fabricate facts that are not present in the provided context. "
                            "If evidence is partial, say that clearly."
                        )
                    }
                ]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": build_answer_prompt(
                                query=query,
                                semantic_context=semantic_context,
                                memory_context=memory_context,
                                preference_context=preference_context,
                                rag_chunks=rag_chunks,
                                sql_rows=sql_rows,
                                data_source=data_source,
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024,
            },
        }

        url = f"{self._base_url}/models/{self._model}:generateContent"
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            response = await client.post(
                url,
                params={"key": self._api_key},
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        return self._extract_text(body)

    @staticmethod
    def _extract_text(body: dict[str, Any]) -> str | None:
        candidates = body.get("candidates")
        if not isinstance(candidates, list):
            return None
        parts: list[str] = []
        for candidate in candidates:
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        if not parts:
            return None
        return "\n".join(parts)


@lru_cache(maxsize=1)
def get_gemini_chat_service() -> GeminiChatService:
    return GeminiChatService()
