"""Chat query route for the LangGraph walking skeleton."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.graph.graph import get_query_graph, invoke_query_graph

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class ChatQueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2000)
    session_id: UUID

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("query must not be empty")
        return value


class ChatQueryResponse(BaseModel):
    answer: str
    trace_id: str


def _current_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if span_context.trace_id:
        return f"{span_context.trace_id:032x}"
    return str(uuid4())


@router.post("/v1/chat/query", response_model=ChatQueryResponse)
async def chat_query(
    payload: ChatQueryRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ChatQueryResponse:
    trace_id = _current_trace_id()
    current_span = trace.get_current_span()
    current_span.set_attribute("aial.trace_id", trace_id)
    current_span.set_attribute("aial.session_id", str(payload.session_id))
    current_span.set_attribute("aial.user_id", principal.sub)
    current_span.set_attribute("aial.department_id", principal.department)
    current_span.set_attribute("aial.route_name", "chat_query")
    result = await invoke_query_graph(
        graph=get_query_graph(),
        query=payload.query,
        session_id=str(payload.session_id),
        principal=principal,
        trace_id=trace_id,
    )
    return ChatQueryResponse(
        answer=result.get("final_response") or "stub",
        trace_id=result["trace_id"],
    )
