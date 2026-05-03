"""Chat query route — Story 2A.1 / 2B.1: stream handle + SQL explanation (FR-O5).

Security invariants:
  - POST /v1/chat/query returns immediately (fire-and-forget LangGraph).
  - GET .../sql-explanation only works for owned, registered request_ids.
  - Fabricated explanations for arbitrary UUIDs are not served.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, field_validator

from aial_shared.auth.cerbos import CerbosClient
from aial_shared.auth.fastapi_deps import get_cerbos_client, get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.approval.workflow import (
    ApprovalRequest,
    ApprovalState,
    QueryIntent,
    create_approval_request,
    get_approval_store,
)
from orchestration.admin_control.user_role_management import get_user_role_management_service
from orchestration.explanation.generator import SqlExplanation, SqlExplanationGenerator
from orchestration.graph.graph import get_query_graph, invoke_query_graph
from orchestration.memory.long_term import get_conversation_memory_service
from orchestration.security.column_masker import ColumnSensitivity, apply_column_security
from orchestration.security.pii_masker import PiiMasker
from orchestration.semantic.management import get_semantic_layer_service
from orchestration.streaming.events import make_done_event, make_error_event, make_row_event
from orchestration.streaming.queue import get_stream_queue

logger = logging.getLogger(__name__)

_explanation_generator = SqlExplanationGenerator()
_pii_masker = PiiMasker()
_PII_SCAN_PENDING = "<PII_SCAN_PENDING>"
# Stores request_id → (user_id, SqlExplanation) after graph completes
_explanation_store: dict[str, tuple[str, SqlExplanation]] = {}
_SENSITIVE_KEYWORDS = {
    3: ("ssn", "social security", "cmnd", "cccd", "customer pii", "employee pii"),
    2: ("salary", "margin", "personal", "phone", "email", "address", "employee"),
}

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)

_INVALID_QUERY_TYPE = "https://aial.internal/errors/invalid-query"


class ChatQueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=2000)
    session_id: UUID
    approval_request_id: UUID | None = None

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
    approval_request_id: str | None = None
    approval_state: str | None = None
    message: str | None = None


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


def _classify_query_sensitivity(query: str) -> int:
    normalized = query.casefold()
    for tier, keywords in sorted(_SENSITIVE_KEYWORDS.items(), reverse=True):
        if any(keyword in normalized for keyword in keywords):
            return tier
    return 1


def _build_query_intent(query: str, principal: JWTClaims) -> QueryIntent:
    sensitivity_tier = _classify_query_sensitivity(query)
    normalized_query = " ".join(query.split())
    return QueryIntent(
        user_id=principal.sub,
        department=principal.department,
        sensitivity_tier=sensitivity_tier,
        intent_type="chat_query",
        filters={"query_preview": normalized_query[:80]},
        estimated_row_count=100,
        query_digest=hashlib.sha256(normalized_query.encode("utf-8")).hexdigest(),
    )


def _derive_safe_query_metadata(query: str) -> tuple[str, str]:
    normalized = query.casefold()
    topic = "general_analysis"
    if "doanh thu" in normalized:
        topic = "revenue_analysis"
    elif "lợi nhuận" in normalized:
        topic = "profit_analysis"
    elif "nhân viên" in normalized or "employee" in normalized:
        topic = "employee_analysis"
    filter_context = "time_filter" if any(token in normalized for token in ("tháng", "quý", "month", "quarter")) else "general_filter"
    return topic, filter_context


def _resolve_approval_request(
    *,
    approval_request_id: UUID | None,
    intent: QueryIntent,
    principal: JWTClaims,
) -> ApprovalRequest:
    store = get_approval_store()
    if approval_request_id is None:
        return create_approval_request(intent, store=store)

    request = store.get(str(approval_request_id))
    if request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if request.intent.user_id != principal.sub:
        raise HTTPException(status_code=403, detail="Approval request does not belong to this user")
    if request.query_fingerprint != intent.fingerprint():
        raise HTTPException(status_code=409, detail="Approval request does not match this query intent")
    if store.is_expired(request) and request.state not in {ApprovalState.APPROVED, ApprovalState.REJECTED, ApprovalState.EXPIRED}:
        store.expire(request.request_id)
        request = store.get(request.request_id)
    return request


def _extract_result_rows(sql_result: Any) -> list[dict[str, Any]]:
    if isinstance(sql_result, list) and all(isinstance(row, dict) for row in sql_result):
        return sql_result
    if isinstance(sql_result, dict):
        rows = sql_result.get("rows")
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            return rows
    return []


def _infer_free_text_columns(rows: list[dict[str, Any]]) -> list[str]:
    free_text_columns: set[str] = set()
    for row in rows:
        for column, value in row.items():
            if isinstance(value, str):
                free_text_columns.add(column)
    return sorted(free_text_columns)


def _apply_runtime_security(
    result: dict[str, Any],
    *,
    principal: JWTClaims,
) -> list[dict[str, Any]]:
    rows = _extract_result_rows(result.get("sql_result"))
    if not rows:
        return []

    raw_schema = result.get("column_sensitivity", {})
    schema = {
        column: value if isinstance(value, ColumnSensitivity) else ColumnSensitivity(int(value))
        for column, value in raw_schema.items()
    }
    secured_rows = apply_column_security(rows, schema=schema, user_clearance=principal.clearance)
    free_text_columns = result.get("free_text_columns") or _infer_free_text_columns(secured_rows)
    pii_scan = _pii_masker.scan_rows(
        secured_rows,
        free_text_columns=list(free_text_columns),
        user_clearance=principal.clearance,
    )

    if pii_scan.mode == "inline":
        final_rows = pii_scan.rows
    else:
        final_rows = []
        for row in secured_rows:
            new_row = dict(row)
            for column in free_text_columns:
                if column in new_row and isinstance(new_row[column], str):
                    new_row[column] = _PII_SCAN_PENDING
            final_rows.append(new_row)

    result["sql_result"] = final_rows
    result["pii_scan_mode"] = pii_scan.mode
    if pii_scan.scan_id:
        result["pii_scan_id"] = pii_scan.scan_id
    return final_rows


def _apply_query_execution_settings(
    result: dict[str, Any],
    *,
    execution_settings: dict[str, Any] | None,
) -> None:
    if execution_settings is None:
        return
    rows = _extract_result_rows(result.get("sql_result"))
    row_limit = execution_settings.get("row_limit")
    if isinstance(row_limit, int) and row_limit >= 0 and rows:
        result["sql_result"] = rows[:row_limit]
    result["data_source"] = execution_settings.get("data_source")
    if execution_settings.get("warning"):
        result["data_source_warning"] = execution_settings["warning"]


async def _is_sensitive_query_authorized(
    *,
    principal: JWTClaims,
    cerbos: CerbosClient,
    sensitivity_tier: int,
) -> bool:
    loop = asyncio.get_running_loop()
    decision = await loop.run_in_executor(
        None,
        lambda: cerbos.check(
            principal,
            "api:chat",
            "default",
            "query_sensitive",
            resource_attr={"sensitivity_tier": str(sensitivity_tier)},
        ),
    )
    return decision.allowed


async def _run_graph_and_cache_explanation(
    *,
    request_id: str,
    query: str,
    session_id: str,
    principal: JWTClaims,
    trace_id: str,
    execution_settings: dict[str, Any] | None = None,
    semantic_context: list[dict[str, Any]] | None = None,
    memory_context: dict[str, Any] | None = None,
    preference_context: list[dict[str, Any]] | None = None,
) -> None:
    """Background task: run LangGraph, store explanation keyed by request_id + user_id."""
    queue = get_stream_queue()
    try:
        timeout_seconds = None
        if execution_settings is not None:
            configured_timeout = execution_settings.get("query_timeout_seconds")
            if isinstance(configured_timeout, int) and configured_timeout > 0:
                timeout_seconds = configured_timeout
        invoke = invoke_query_graph(
            graph=get_query_graph(),
            query=query,
            session_id=session_id,
            principal=principal,
            trace_id=trace_id,
            semantic_context=semantic_context,
            memory_context=memory_context,
            preference_context=preference_context,
        )
        if timeout_seconds is not None:
            result = await asyncio.wait_for(
                invoke,
                timeout=timeout_seconds,
            )
        else:
            result = await invoke
        _apply_query_execution_settings(result, execution_settings=execution_settings)
        secured_rows = _apply_runtime_security(result, principal=principal)
        fallback_sql = f"SELECT * FROM oracle WHERE query='{query[:40]}'"
        if semantic_context:
            fallback_sql = f"SELECT {semantic_context[0]['formula']} FROM semantic_layer"
        generated_sql = result.get("generated_sql", fallback_sql)
        exp = _explanation_generator.explain_kw(sql=generated_sql, metric_context=None)
        _explanation_store[request_id] = (principal.sub, exp)
        topic, filter_context = _derive_safe_query_metadata(query)
        memory_service = get_conversation_memory_service()
        memory_service.record_interaction(
            user_id=principal.sub,
            department_id=principal.department,
            session_id=session_id,
            intent_type="chat_query",
            topic=topic,
            filter_context=filter_context,
            key_result_summary=f"Answer summary for {topic}",
            sensitivity_level=_classify_query_sensitivity(query),
            matched_metrics=[str(item["term"]) for item in semantic_context or []],
        )
        if secured_rows:
            queue.push(request_id, make_row_event(rows=secured_rows, chunk_index=0))
        answer = result.get("final_response", "stub") or "stub"
        if result.get("data_source_warning"):
            answer = f"{answer}\n\n[warning] {result['data_source_warning']}"
        queue.push(request_id, make_done_event(trace_id=trace_id, answer=answer))
        queue.close(request_id)
    except TimeoutError:
        logger.warning("Graph execution timed out for request %s", request_id)
        queue.push(request_id, make_error_event(code="QUERY_TIMEOUT", message="Query execution timed out"))
        queue.close(request_id)
    except Exception as exc:
        logger.warning("Graph execution failed for request %s: %s", request_id, exc)
        queue.push(request_id, make_error_event(code="GRAPH_EXECUTION_FAILED", message="Query execution failed"))
        queue.close(request_id)


@router.post("/v1/chat/query", response_model=ChatQueryStreamHandle)
async def chat_query(
    payload: ChatQueryRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
    cerbos: CerbosClient = Depends(get_cerbos_client),
) -> ChatQueryStreamHandle:
    """Return stream handle immediately; LangGraph runs in background (fire-and-forget)."""
    request_id = str(uuid4())
    trace_id = _current_trace_id()
    current_span = trace.get_current_span()
    current_span.set_attribute("aial.request_id", request_id)
    current_span.set_attribute("aial.trace_id", trace_id)
    current_span.set_attribute("aial.session_id", str(payload.session_id))
    current_span.set_attribute("aial.user_id", principal.sub)
    current_span.set_attribute("aial.department_id", principal.department)
    current_span.set_attribute("aial.route_name", "chat_query")

    intent = _build_query_intent(payload.query, principal)
    execution_settings = get_user_role_management_service().resolve_query_data_source(principal)
    if get_user_role_management_service().list_data_sources() and execution_settings is None:
        raise HTTPException(status_code=403, detail="No authorized data source is configured for this principal")
    semantic_context = get_semantic_layer_service().match_query(payload.query)
    memory_service = get_conversation_memory_service()
    memory_context = memory_service.build_context_bundle(
        user_id=principal.sub,
        department_id=principal.department,
        clearance=principal.clearance,
        query=payload.query,
    )
    preference_context = memory_service.get_suggestions(user_id=principal.sub)
    current_span.set_attribute("aial.semantic_match_count", len(semantic_context))
    current_span.set_attribute("aial.memory_summary_count", len(memory_context.get("summaries", [])))
    can_bypass_approval = False
    if intent.sensitivity_tier >= 2:
        can_bypass_approval = await _is_sensitive_query_authorized(
            principal=principal,
            cerbos=cerbos,
            sensitivity_tier=intent.sensitivity_tier,
        )
        current_span.set_attribute("aial.sensitive_bypass_allowed", can_bypass_approval)

    if intent.sensitivity_tier >= 2 and not can_bypass_approval:
        approval_request = _resolve_approval_request(
            approval_request_id=payload.approval_request_id,
            intent=intent,
            principal=principal,
        )
        if approval_request.state != ApprovalState.APPROVED:
            status = "approval_required"
            if approval_request.state == ApprovalState.REJECTED:
                status = "rejected"
            elif approval_request.state == ApprovalState.EXPIRED:
                status = "expired"
            return ChatQueryStreamHandle(
                request_id=request_id,
                status=status,
                trace_id=trace_id,
                approval_request_id=approval_request.request_id,
                approval_state=approval_request.state.value,
                message="Câu hỏi này đang chờ phê duyệt",
            )

    get_stream_queue().create(request_id, owner_user_id=principal.sub)

    # Fire-and-forget: do NOT await — return stream handle immediately
    asyncio.create_task(
        _run_graph_and_cache_explanation(
            request_id=request_id,
            query=payload.query,
            session_id=str(payload.session_id),
            principal=principal,
            trace_id=trace_id,
            execution_settings=execution_settings,
            semantic_context=semantic_context,
            memory_context=memory_context,
            preference_context=preference_context,
        )
    )

    return ChatQueryStreamHandle(
        request_id=request_id,
        status="streaming",
        trace_id=trace_id,
        message=execution_settings.get("warning") if execution_settings else None,
    )


@router.get("/v1/chat/query/{request_id}/sql-explanation")
async def sql_explanation(
    request_id: UUID,
    show_sql: bool = False,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    """FR-O5 SQL explanation — Story 2B.1.

    Only serves explanations for request_ids that:
    1. Exist in the explanation store (query was actually executed).
    2. Belong to the calling user (ownership verification).
    """
    req_id = str(request_id)
    entry = _explanation_store.get(req_id)

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="No explanation found — query may still be processing or request_id is unknown",
        )

    owner_user_id, exp = entry
    if owner_user_id != principal.sub:
        raise HTTPException(status_code=403, detail="This explanation does not belong to you")

    return exp.to_response_dict(include_raw_sql=show_sql)
