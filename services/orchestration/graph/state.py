"""Shared LangGraph state contract for orchestration workflows."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage
from typing_extensions import TypedDict

from aial_shared.auth.keycloak import JWTClaims


class AIALGraphState(TypedDict, total=False):
    trace_id: str
    session_id: str
    user_id: str
    department_id: str
    messages: list[BaseMessage]
    intent_type: str
    current_node: str
    sql_result: Any | None
    rag_result: Any | None
    final_response: str | None
    error: str | None
    should_abort: bool
    semantic_context: list[dict[str, Any]]
    memory_context: dict[str, Any]
    preference_context: list[dict[str, Any]]


class QueryDecompositionState(TypedDict, total=False):
    trace_id: str
    request_id: str
    source_domains: list[str]
    strategy: str
    subqueries: list[dict[str, Any]]
    intermediate_results: list[dict[str, Any]]
    merge_keys: list[str]
    merge_metadata: dict[str, Any]
    merged_result: dict[str, Any] | None
    error: dict[str, Any] | None


def build_initial_state(
    *,
    query: str,
    session_id: str,
    principal: JWTClaims,
    trace_id: str,
    semantic_context: list[dict[str, Any]] | None = None,
    memory_context: dict[str, Any] | None = None,
    preference_context: list[dict[str, Any]] | None = None,
) -> AIALGraphState:
    return AIALGraphState(
        trace_id=trace_id,
        session_id=session_id,
        user_id=principal.sub,
        department_id=principal.department,
        messages=[HumanMessage(content=query)],
        intent_type="pending",
        sql_result=None,
        rag_result=None,
        final_response=None,
        error=None,
        should_abort=False,
        semantic_context=semantic_context or [],
        memory_context=memory_context or {},
        preference_context=preference_context or [],
    )
