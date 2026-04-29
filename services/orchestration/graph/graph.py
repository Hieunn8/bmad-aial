"""LangGraph assembly and invocation helpers for chat query orchestration."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from aial_shared.auth.keycloak import JWTClaims
from orchestration.graph.checkpointing import create_redis_checkpointer
from orchestration.graph.nodes.stub_response import stub_response_node
from orchestration.graph.state import AIALGraphState, build_initial_state

logger = logging.getLogger(__name__)


def create_query_graph(*, checkpointer: BaseCheckpointSaver | None = None) -> Any:
    builder = StateGraph(AIALGraphState)
    builder.add_node("stub_response", stub_response_node)
    builder.add_edge(START, "stub_response")
    builder.add_edge("stub_response", END)
    if checkpointer is None:
        return builder.compile()
    return builder.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_query_graph() -> Any:
    try:
        checkpointer = create_redis_checkpointer()
    except Exception as exc:  # pragma: no cover - depends on local Redis/RedisStack
        logger.warning("Redis checkpointer unavailable, using in-memory graph: %s", exc)
        return create_query_graph()
    return create_query_graph(checkpointer=checkpointer)


async def invoke_query_graph(
    *,
    graph: Any,
    query: str,
    session_id: str,
    principal: JWTClaims,
    trace_id: str,
) -> AIALGraphState:
    initial_state = build_initial_state(
        query=query,
        session_id=session_id,
        principal=principal,
        trace_id=trace_id,
    )
    config = {"configurable": {"thread_id": session_id}}
    result = await graph.ainvoke(initial_state, config=config)
    return AIALGraphState(result)
