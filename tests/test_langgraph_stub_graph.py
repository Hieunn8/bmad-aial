"""Tests for the LangGraph stub graph and shared state contract."""

from __future__ import annotations

from uuid import uuid4

import fakeredis
import pytest
from langchain_core.messages import HumanMessage
from orchestration.graph.checkpointing import FakeRedisSaver, create_redis_checkpointer
from orchestration.graph.graph import create_query_graph, invoke_query_graph
from orchestration.graph.state import AIALGraphState, build_initial_state

from aial_shared.auth.keycloak import JWTClaims


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "user-123",
            "email": "user@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )


class TestGraphStateContract:
    def test_build_initial_state_populates_architecture_fields(self, sample_claims: JWTClaims) -> None:
        state = build_initial_state(
            query="Doanh thu HCM thang 3?",
            session_id="5e2d938d-4b76-4df0-bd77-27c8d0df9a53",
            principal=sample_claims,
            trace_id="trace-123",
        )

        expected_keys = {
            "trace_id",
            "session_id",
            "user_id",
            "department_id",
            "messages",
            "intent_type",
            "sql_result",
            "rag_result",
            "final_response",
            "error",
            "should_abort",
        }
        assert expected_keys <= set(state.keys())
        assert state["trace_id"] == "trace-123"
        assert state["session_id"] == "5e2d938d-4b76-4df0-bd77-27c8d0df9a53"
        assert state["user_id"] == "user-123"
        assert state["department_id"] == "sales"
        assert isinstance(state["messages"][0], HumanMessage)
        assert state["messages"][0].content == "Doanh thu HCM thang 3?"

    def test_typed_dict_alias_is_importable(self) -> None:
        state: AIALGraphState = {"trace_id": "abc"}
        assert state["trace_id"] == "abc"


class TestFakeRedisSaver:
    def test_put_persists_checkpoint_metadata_in_fake_redis(self) -> None:
        saver = FakeRedisSaver(fakeredis.FakeRedis(decode_responses=False))
        config = {"configurable": {"thread_id": "thread-1"}}

        updated_config = saver.put(
            config,
            {
                "v": 1,
                "id": "checkpoint-1",
                "ts": "2026-04-29T00:00:00Z",
                "channel_values": {"final_response": "stub"},
                "channel_versions": {"final_response": 1},
                "versions_seen": {},
            },
            {"source": "unit-test"},
            {"final_response": 1},
        )

        assert updated_config["configurable"]["checkpoint_id"] == "checkpoint-1"
        assert saver.redis_client.exists("aial:test:checkpoint:thread-1:checkpoint-1") == 1


class TestQueryGraph:
    @pytest.mark.anyio
    async def test_invoke_returns_stub_answer_and_trace_id(self, sample_claims: JWTClaims) -> None:
        saver = FakeRedisSaver(fakeredis.FakeRedis(decode_responses=False))
        graph = create_query_graph(checkpointer=saver)

        result = await invoke_query_graph(
            graph=graph,
            query="test query",
            session_id=str(uuid4()),
            principal=sample_claims,
            trace_id="trace-xyz",
        )

        assert result["final_response"] == "stub using governed metric"
        assert result["trace_id"] == "trace-xyz"
        assert result["intent_type"] == "stub"
        assert result["should_abort"] is False

    @pytest.mark.requires_redis
    @pytest.mark.anyio
    async def test_real_redis_checkpointer_round_trip_when_redis_available(self, sample_claims: JWTClaims) -> None:
        try:
            saver = create_redis_checkpointer("redis://localhost:6379")
        except Exception as exc:  # pragma: no cover - environment dependent
            pytest.skip(f"Redis unavailable for integration test: {exc}")

        graph = create_query_graph(checkpointer=saver)
        session_id = str(uuid4())

        result = await invoke_query_graph(
            graph=graph,
            query="redis test",
            session_id=session_id,
            principal=sample_claims,
            trace_id="trace-redis",
        )

        assert result["final_response"] == "stub using governed metric"
        checkpoint = saver.get_tuple({"configurable": {"thread_id": session_id}})
        assert checkpoint is not None
