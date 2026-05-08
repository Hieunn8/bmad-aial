"""Stub node for the walking skeleton query graph."""

from __future__ import annotations

from opentelemetry import trace

from aial_shared.auth.keycloak import JWTClaims
from orchestration.graph.state import AIALGraphState
from orchestration.semantic.cube_runtime import execute_cube_semantic_query, is_cube_runtime_enabled
from orchestration.semantic.sql_execution import build_and_execute_semantic_sql


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
        if is_cube_runtime_enabled() and semantic_context:
            cube_execution = execute_cube_semantic_query(
                query=state["query"],
                semantic_context=semantic_context,
                principal=principal,
            )
            generated_sql = cube_execution.generated_sql or f"CUBE_REST_QUERY {metric_term}"
            sql_rows = cube_execution.rows
            data_source = cube_execution.data_source
            max_available_date = cube_execution.max_available_date
            warning = cube_execution.warning
            runtime_label = "runtime:cube"
        else:
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
            data_source = semantic_execution.plan.data_source if semantic_execution.plan is not None else None
            max_available_date = semantic_execution.max_available_date
            warning = semantic_execution.warning
            runtime_label = "sql:semantic" if semantic_execution.plan is not None else None
        recalled = memory_context.get("summaries", [])
        preference_hint = preference_context[0]["label"] if preference_context else None
        answer_parts = [f"stub using {metric_term}"]
        if runtime_label:
            answer_parts.append(runtime_label)
        if warning:
            answer_parts.append(warning)
        if recalled:
            answer_parts.append(f"memory:{len(recalled)}")
        if preference_hint:
            answer_parts.append(f"preference:{preference_hint}")
        return {
            "intent_type": "semantic_memory_stub" if semantic_context or recalled or preference_context else "stub",
            "final_response": " | ".join(answer_parts),
            "generated_sql": generated_sql,
            "sql_result": sql_rows,
            "data_source": data_source,
            "max_available_date": max_available_date,
            "error": None,
            "should_abort": False,
            "current_node": "stub_response",
        }
