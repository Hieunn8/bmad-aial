from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from orchestration.llm.answering import generate_chat_answer
from orchestration.llm.openai import OpenAIChatService


def test_openai_extracts_output_text() -> None:
    body = {"output_text": "Tra loi tu OpenAI"}
    assert OpenAIChatService._extract_text(body) == "Tra loi tu OpenAI"


@pytest.mark.asyncio()
async def test_answering_prefers_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    openai = type("OpenAIStub", (), {})()
    openai.enabled = True
    openai.generate_answer = AsyncMock(return_value="OpenAI answer")

    gemini = type("GeminiStub", (), {})()
    gemini.enabled = True
    gemini.generate_answer = AsyncMock(return_value="Gemini answer")

    monkeypatch.setattr("orchestration.llm.answering.get_openai_chat_service", lambda: openai)
    monkeypatch.setattr("orchestration.llm.answering.get_gemini_chat_service", lambda: gemini)

    answer = await generate_chat_answer(query="Xin chao")
    assert answer == "OpenAI answer"
    gemini.generate_answer.assert_not_awaited()


@pytest.mark.asyncio()
async def test_answering_falls_back_to_gemini_when_openai_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    openai = type("OpenAIStub", (), {})()
    openai.enabled = True
    openai.generate_answer = AsyncMock(side_effect=RuntimeError("OpenAI down"))

    gemini = type("GeminiStub", (), {})()
    gemini.enabled = True
    gemini.generate_answer = AsyncMock(return_value="Gemini fallback")

    monkeypatch.setattr("orchestration.llm.answering.get_openai_chat_service", lambda: openai)
    monkeypatch.setattr("orchestration.llm.answering.get_gemini_chat_service", lambda: gemini)

    answer = await generate_chat_answer(query="Xin chao")
    assert answer == "Gemini fallback"
