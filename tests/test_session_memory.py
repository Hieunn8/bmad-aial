"""Tests for Story 2A.6 — Short-term Session Memory + Per-Turn Security."""

from __future__ import annotations

from uuid import uuid4

import fakeredis
import pytest

from orchestration.memory.session import SessionMemory, SessionMemoryStore


class TestSessionMemoryIsolation:
    def test_session_key_is_scoped_to_user_and_department(self) -> None:
        store = SessionMemoryStore(redis=fakeredis.FakeRedis(decode_responses=True))
        session_id = str(uuid4())

        store.append_turn(
            user_id="user-A",
            department_id="sales",
            session_id=session_id,
            user_message="Doanh thu tháng 3?",
            assistant_message="Doanh thu tháng 3 là 100 tỷ",
        )

        result_a = store.get_history(user_id="user-A", department_id="sales", session_id=session_id)
        result_b = store.get_history(user_id="user-B", department_id="finance", session_id=session_id)

        assert len(result_a) == 1
        assert result_b == []

    def test_cross_user_session_access_impossible(self) -> None:
        store = SessionMemoryStore(redis=fakeredis.FakeRedis(decode_responses=True))
        session_id = str(uuid4())

        store.append_turn(
            user_id="user-secret",
            department_id="finance",
            session_id=session_id,
            user_message="confidential query",
            assistant_message="confidential answer",
        )

        leakage = store.get_history(
            user_id="user-attacker",
            department_id="finance",
            session_id=session_id,
        )
        assert leakage == []

    def test_session_ttl_is_24_hours(self) -> None:
        redis = fakeredis.FakeRedis(decode_responses=True)
        store = SessionMemoryStore(redis=redis)
        session_id = str(uuid4())

        store.append_turn(
            user_id="user-1",
            department_id="sales",
            session_id=session_id,
            user_message="test",
            assistant_message="answer",
        )

        key = store._make_key("user-1", "sales", session_id)
        ttl = redis.ttl(key)
        assert ttl > 0
        assert ttl <= 86400

    def test_expired_session_returns_empty_history(self) -> None:
        redis = fakeredis.FakeRedis(decode_responses=True)
        store = SessionMemoryStore(redis=redis)
        session_id = str(uuid4())

        store.append_turn("user-1", "sales", session_id, "q", "a")
        key = store._make_key("user-1", "sales", session_id)
        redis.delete(key)

        history = store.get_history("user-1", "sales", session_id)
        assert history == []


class TestSessionMemoryTurns:
    def test_append_and_retrieve_multiple_turns(self) -> None:
        store = SessionMemoryStore(redis=fakeredis.FakeRedis(decode_responses=True))
        session_id = str(uuid4())

        store.append_turn("user-1", "sales", session_id, "Doanh thu tháng 3?", "100 tỷ")
        store.append_turn("user-1", "sales", session_id, "Vì sao giảm?", "Do mùa vụ")

        history = store.get_history("user-1", "sales", session_id)
        assert len(history) == 2
        assert history[0]["user"] == "Doanh thu tháng 3?"
        assert history[1]["assistant"] == "Do mùa vụ"

    def test_session_memory_dataclass(self) -> None:
        mem = SessionMemory(
            user_id="user-1",
            department_id="sales",
            session_id=str(uuid4()),
            turns=[{"user": "q", "assistant": "a"}],
        )
        assert len(mem.turns) == 1
        assert mem.user_id == "user-1"
