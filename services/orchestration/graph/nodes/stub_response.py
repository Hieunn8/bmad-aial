"""Stub node for the walking skeleton query graph."""

from __future__ import annotations

from opentelemetry import trace

from orchestration.graph.state import AIALGraphState


async def stub_response_node(state: AIALGraphState) -> dict[str, object]:
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("langgraph.stub_response") as span:
        span.set_attribute("aial.trace_id", state["trace_id"])
        span.set_attribute("aial.session_id", state["session_id"])
        span.set_attribute("aial.user_id", state["user_id"])
        span.set_attribute("aial.department_id", state["department_id"])
        span.set_attribute("aial.node_name", "stub_response")
        return {
            "intent_type": "stub",
            "final_response": "stub",
            "error": None,
            "should_abort": False,
            "current_node": "stub_response",
        }
