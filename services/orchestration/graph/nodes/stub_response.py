"""Stub node for the walking skeleton query graph."""

from __future__ import annotations

from opentelemetry import trace

from orchestration.graph.state import AIALGraphState
from orchestration.semantic.sql_execution import build_and_execute_semantic_sql

from aial_shared.auth.keycloak import JWTClaims


async def stub_response_node(state: AIALGraphState) -> dict[str, object]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("langgraph.stub_response") as span:
        span.set_attribute("aial.trace_id", state["trace_id"])
        span.set_attribute("aial.session_id", state["session_id"])
        span.set_attribute("aial.user_id", state["user_id"])
        span.set_attribute("aial.department_id", state["department_id"])
        span.set_attribute("aial.node_name", "stub_response")
        semantic_context = state.get("semantic_context", [])
        memory_context = state.get("memory_context", {})
        preference_context = state.get("preference_context", [])
        metric_term = semantic_context[0]["term"] if semantic_context else "governed metric"
        metric_formula = semantic_context[0]["formula"] if semantic_context else "COUNT(*)"
        principal = JWTClaims(
            sub=state["user_id"],
            email="",
            department=state["department_id"],
            roles=tuple(state.get("roles", [])),
            clearance=int(state.get("clearance", 1)),
            raw={},
        )
        semantic_execution = build_and_execute_semantic_sql(
            query=state["query"],
            semantic_context=semantic_context,
            principal=principal,
        )
        generated_sql = (
            semantic_execution.plan.sql
            if semantic_execution.plan is not None
            else f"SELECT {metric_formula} AS metric_value FROM semantic_layer_stub"
        )
        sql_rows = semantic_execution.rows
        recalled = memory_context.get("summaries", [])
        preference_hint = preference_context[0]["label"] if preference_context else None
        answer_parts = [f"stub using {metric_term}"]
        if semantic_execution.plan is not None:
            answer_parts.append("sql:semantic")
        if semantic_execution.warning:
            answer_parts.append(semantic_execution.warning)
        if recalled:
            answer_parts.append(f"memory:{len(recalled)}")
        if preference_hint:
            answer_parts.append(f"preference:{preference_hint}")
        return {
            "intent_type": "semantic_memory_stub" if semantic_context or recalled or preference_context else "stub",
            "final_response": " | ".join(answer_parts),
            "generated_sql": generated_sql,
            "sql_result": sql_rows,
            "data_source": semantic_execution.plan.data_source if semantic_execution.plan is not None else None,
            "error": None,
            "should_abort": False,
            "current_node": "stub_response",
        }
