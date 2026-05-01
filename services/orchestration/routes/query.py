"""Chat query route — Story 2A.1 / 2B.1: stream handle + SQL explanation (FR-O5)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.explanation.generator import SqlExplanationGenerator
from orchestration.graph.graph import get_query_graph, invoke_query_graph
from orchestration.streaming.queue import get_stream_queue

_explanation_generator = SqlExplanationGenerator()

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)

_INVALID_QUERY_TYPE = "https://aial.internal/errors/invalid-query"


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


class ChatQueryStreamHandle(BaseModel):
    """Initial response returned immediately; SSE stream begins in parallel (Story 2A.5)."""

    request_id: str
    status: str
    trace_id: str


class SqlExplanationResponse(BaseModel):
    """FR-O5 SQL explanation — Story 2B.1."""

    data_source: str
    formula_description: str | None
    filters_applied: list[str]
    confidence: str
    uncertainty_message: str | None
    raw_sql: str | None = None


def _current_trace_id() -> str:
    span_context = trace.get_current_span().get_span_context()
    if span_context.trace_id:
        return f"{span_context.trace_id:032x}"
    return str(uuid4())


@router.post("/v1/chat/query", response_model=ChatQueryStreamHandle)
async def chat_query(
    payload: ChatQueryRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> ChatQueryStreamHandle:
    request_id = str(uuid4())
    get_stream_queue().create(request_id, owner_user_id=principal.sub)
    trace_id = _current_trace_id()
    current_span = trace.get_current_span()
    current_span.set_attribute("aial.request_id", request_id)
    current_span.set_attribute("aial.trace_id", trace_id)
    current_span.set_attribute("aial.session_id", str(payload.session_id))
    current_span.set_attribute("aial.user_id", principal.sub)
    current_span.set_attribute("aial.department_id", principal.department)
    current_span.set_attribute("aial.route_name", "chat_query")
    await invoke_query_graph(
        graph=get_query_graph(),
        query=payload.query,
        session_id=str(payload.session_id),
        principal=principal,
        trace_id=trace_id,
    )
    return ChatQueryStreamHandle(request_id=request_id, status="streaming", trace_id=trace_id)


@router.get("/v1/chat/query/{request_id}/sql-explanation")
async def sql_explanation(
    request_id: UUID,
    show_sql: bool = False,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    """FR-O5 SQL explanation — Story 2B.1.

    Returns plain-Vietnamese description of data source, formula, and filters.
    Raw SQL not shown by default; pass ?show_sql=true for progressive disclosure.
    """
    exp = _explanation_generator.explain_kw(
        sql=f"SELECT * FROM query_result WHERE request_id='{request_id}'",
        metric_context=None,
    )
    return exp.to_response_dict(include_raw_sql=show_sql)
