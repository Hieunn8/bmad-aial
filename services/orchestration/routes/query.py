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
import re
import unicodedata
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, field_validator
from rag.composition.nodes import (
    RagChunk,
    SqlResult,
    compose_answer,
    format_citations,
    merge_results,
)
from rag.retrieval.weaviate_store import get_weaviate_document_store

from aial_shared.auth.cerbos import CerbosClient
from aial_shared.auth.fastapi_deps import CERBOS_CLIENT_DEP, get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.admin_control.user_role_management import get_user_role_management_service
from orchestration.approval.workflow import (
    ApprovalRequest,
    ApprovalState,
    QueryIntent,
    create_approval_request,
    get_approval_store,
)
from orchestration.audit.read_model import AuditRecord, get_audit_read_model
from orchestration.cache.query_result_cache import (
    CachedQueryResult,
    CacheLookupResult,
    QueryCacheContext,
    get_query_result_cache,
    normalize_query_intent,
)
from orchestration.cross_domain.service import execute_cross_domain_query, is_cross_domain_query
from orchestration.explanation.generator import SqlExplanation, SqlExplanationGenerator
from orchestration.exporting.service import get_export_service
from orchestration.graph.graph import get_query_graph, invoke_query_graph
from orchestration.llm.answering import generate_chat_answer
from orchestration.memory.long_term import get_conversation_memory_service
from orchestration.security.column_masker import ColumnSensitivity, apply_column_security
from orchestration.security.pii_masker import PiiMasker
from orchestration.semantic.management import get_semantic_layer_service
from orchestration.semantic.resolver import SemanticResolveDecision
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
    force_refresh: bool = False

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
    cache_hit: bool = False
    cache_timestamp: str | None = None
    freshness_indicator: str | None = None
    cache_similarity: float | None = None


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
    filter_context = (
        "time_filter"
        if any(token in normalized for token in ("tháng", "quý", "month", "quarter"))
        else "general_filter"
    )
    return topic, filter_context


def _build_role_scope(principal: JWTClaims) -> str:
    normalized_roles = sorted({role.strip() for role in principal.roles if role.strip()})
    return "|".join(normalized_roles) if normalized_roles else "anonymous"


def _derive_semantic_layer_version(semantic_context: list[dict[str, Any]]) -> str:
    version_ids = [
        str(entry["active_version_id"])
        for entry in semantic_context
        if isinstance(entry, dict) and entry.get("active_version_id")
    ]
    if version_ids:
        return "|".join(sorted(version_ids))
    return get_semantic_layer_service().cache_invalidated_at.isoformat()


def _derive_data_freshness_class(
    *,
    semantic_context: list[dict[str, Any]],
    execution_settings: dict[str, Any] | None,
) -> str:
    freshness_rules = sorted(
        {
            str(entry["freshness_rule"])
            for entry in semantic_context
            if isinstance(entry, dict) and entry.get("freshness_rule")
        }
    )
    if freshness_rules:
        return "|".join(freshness_rules)
    if execution_settings and execution_settings.get("data_source"):
        return f"sql:{execution_settings['data_source']}"
    return "sql:adhoc"


def _build_cache_context(
    *,
    query: str,
    principal: JWTClaims,
    semantic_context: list[dict[str, Any]],
    execution_settings: dict[str, Any] | None,
) -> QueryCacheContext:
    return QueryCacheContext(
        query=query,
        normalized_intent=normalize_query_intent(query),
        owner_user_id=principal.sub,
        department_id=principal.department,
        role_scope=_build_role_scope(principal),
        semantic_layer_version=_derive_semantic_layer_version(semantic_context),
        data_freshness_class=_derive_data_freshness_class(
            semantic_context=semantic_context,
            execution_settings=execution_settings,
        ),
    )


def _format_cache_freshness_indicator(timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp)
        rendered = parsed.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    except ValueError:
        rendered = timestamp
    return f"Káº¿t quáº£ tá»« cache â€” cáº­p nháº­t lÃºc {rendered}"


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
    terminal_states = {
        ApprovalState.APPROVED,
        ApprovalState.REJECTED,
        ApprovalState.EXPIRED,
    }
    if store.is_expired(request) and request.state not in terminal_states:
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


_DIM_LABELS: dict[str, str] = {
    "REGION_CODE": "khu vực",
    "CHANNEL_CODE": "kênh",
    "PRODUCT_CODE": "sản phẩm",
    "CATEGORY_NAME": "danh mục",
}


def _build_semantic_no_data_answer(
    *,
    semantic_context: list[dict[str, Any]] | None,
    generated_sql: str,
    data_source: str | None,
    max_available_date: str | None = None,
) -> str | None:
    if not semantic_context:
        return None
    metric_term = str(semantic_context[0].get("term") or "semantic")
    source = semantic_context[0].get("source", {})
    source_value = source.get("data_source") if isinstance(source, dict) else None
    source_name = data_source or (str(source_value) if source_value else "")
    if not source_name:
        return None

    # Read filter context directly from semantic_plan (reliable — no SQL parsing needed)
    semantic_plan = semantic_context[0].get("_semantic_plan") or {}
    time_filter = semantic_plan.get("time_filter") or {}
    entity_filters = semantic_plan.get("entity_filters") or {}

    filter_parts: list[str] = []
    # Time range
    tf_start = time_filter.get("start")
    tf_end = time_filter.get("end")
    tf_kind = time_filter.get("kind", "")
    if tf_start and tf_end:
        filter_parts.append(f"thời gian {tf_start} → {tf_end}")
    elif tf_kind and tf_kind not in ("none", "latest_record", ""):
        filter_parts.append(f"bộ lọc thời gian: {tf_kind}")
    else:
        # fallback: parse SQL for DATE literals
        date_bounds = re.findall(r"DATE '(\d{4}-\d{2}-\d{2})'", generated_sql)
        if len(date_bounds) >= 2:
            filter_parts.append(f"thời gian {date_bounds[0]} → {date_bounds[1]}")
    # Entity filters (specific values like HCM, ONLINE)
    for col, val in entity_filters.items():
        label = _DIM_LABELS.get(col, col.lower())
        filter_parts.append(f"{label}: {val}")

    filter_str = ("bộ lọc: " + ", ".join(filter_parts) + " | ") if filter_parts else ""

    # Availability hint from auto-query
    if max_available_date:
        availability = f"Dữ liệu có sẵn trong khoảng **{max_available_date}**."
        suggestion = (
            f"{availability}\n"
            "Thử hỏi lại với khoảng thời gian trên, hoặc bỏ bộ lọc thời gian để xem toàn bộ dữ liệu."
        )
    elif tf_start:
        # Time filter was applied but no auto-query result — generic suggestion with context
        suggestion = (
            "Khoảng thời gian trên chưa có dữ liệu. "
            "Thử hỏi: *tháng trước*, *quý 1 2026*, hoặc bỏ bộ lọc thời gian."
        )
    else:
        suggestion = "Thử hỏi về khoảng thời gian cụ thể hoặc bỏ bộ lọc để xem toàn bộ."

    return (
        f"Không tìm thấy dữ liệu `{metric_term}` ({filter_str}nguồn: {source_name}).\n"
        f"{suggestion}"
    )


def _normalize_vietnamese_intent(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(without_marks.replace("đ", "d").replace("Ä‘", "d").split())


def _is_data_inventory_query(query: str) -> bool:
    normalized = _normalize_vietnamese_intent(query)
    patterns = (
        "ban co du lieu gi",
        "co du lieu gi",
        "co nhung du lieu gi",
        "dang co du lieu gi",
        "danh sach du lieu",
        "du lieu nao",
        "co nhung semantic nao",
        "semantic nao",
    )
    return any(pattern in normalized for pattern in patterns)


def _build_data_inventory_answer(principal: JWTClaims) -> str:
    allowed_terms = get_user_role_management_service().allowed_metrics_for_principal(principal)
    metrics = get_semantic_layer_service().list_metrics()
    visible_metrics = [
        metric
        for metric in metrics
        if not allowed_terms or str(metric.get("term", "")).casefold() in allowed_terms
    ]
    if not visible_metrics:
        return "Hiện chưa có semantic hoặc nguồn dữ liệu nào được publish cho vai trò của bạn."

    lines = ["Bạn có thể hỏi các nhóm dữ liệu sau:"]
    for metric in visible_metrics[:10]:
        unit = metric.get("unit")
        examples = [str(example) for example in metric.get("examples", [])[:2] if str(example).strip()]
        detail_parts = [str(metric.get("term", ""))]
        if unit:
            detail_parts.append(f"đơn vị {unit}")
        if examples:
            detail_parts.append(f"ví dụ: {examples[0]}")
        lines.append(f"- {'; '.join(detail_parts)}")
    lines.append("Tôi sẽ tự chọn semantic phù hợp và chỉ hỏi lại khi câu hỏi bị mơ hồ.")
    return "\n".join(lines)


def _build_semantic_clarification_answer(decision: SemanticResolveDecision) -> str | None:
    if decision.status not in {"ambiguous", "low_confidence"}:
        return None
    candidate_terms: list[str] = []
    for candidate in decision.candidates:
        if candidate.filtered_reason or candidate.validation_errors:
            continue
        term = str(candidate.metric.get("term", "")).strip()
        if term and term not in candidate_terms:
            candidate_terms.append(term)
    if not candidate_terms:
        return None
    if decision.planner_output and decision.planner_output.clarification_question:
        question = decision.planner_output.clarification_question
    elif len(candidate_terms) == 1:
        question = f"Có phải bạn muốn hỏi theo semantic chuẩn `{candidate_terms[0]}` không?"
    else:
        question = f"Bạn muốn dùng semantic chuẩn nào: {', '.join(candidate_terms[:4])}?"
    examples = []
    for candidate in decision.candidates[:3]:
        for example in candidate.metric.get("examples", [])[:1]:
            if isinstance(example, str) and example.strip():
                examples.append(example.strip())
    suffix = ""
    if examples:
        suffix = "\nVí dụ câu hỏi phù hợp: " + "; ".join(examples[:3])
    return (
        "Tôi chưa đủ chắc để tự chọn semantic và chạy dữ liệu. "
        f"{question}{suffix}"
    )


def _has_meaningful_sql_values(rows: list[dict[str, Any]]) -> bool:
    if not rows:
        return False
    for row in rows:
        for value in row.values():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return True
    return False


def _record_query_interaction(
    *,
    query: str,
    principal: JWTClaims,
    session_id: str,
    semantic_context: list[dict[str, Any]] | None,
) -> None:
    topic, filter_context = _derive_safe_query_metadata(query)
    get_conversation_memory_service().record_interaction(
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


def _record_semantic_resolve_audit(
    *,
    request_id: str,
    principal: JWTClaims,
    session_id: str,
    decision: SemanticResolveDecision,
) -> None:
    get_audit_read_model().append(
        AuditRecord(
            request_id=request_id,
            user_id=principal.sub,
            department_id=principal.department,
            session_id=session_id,
            timestamp=datetime.now(UTC),
            intent_type="semantic_resolve",
            sensitivity_tier="SEMANTIC",
            sql_hash=None,
            data_sources=["semantic_registry"],
            rows_returned=len(decision.semantic_context),
            latency_ms=0,
            policy_decision="allow" if decision.status == "selected" else "review",
            status=decision.status,
            metadata=decision.to_audit_dict(),
        )
    )


async def _safe_rag_search(
    *,
    query: str,
    principal: JWTClaims,
    cerbos_client: CerbosClient,
) -> list[RagChunk]:
    try:
        return await get_weaviate_document_store().search(
            query=query,
            principal=principal,
            cerbos_client=cerbos_client,
            limit=5,
        )
    except Exception as exc:
        logger.warning("RAG retrieval failed for user %s: %s", principal.sub, exc)
        return []


async def _safe_generate_chat_answer(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    memory_context: dict[str, Any] | None,
    preference_context: list[dict[str, Any]] | None,
    rag_chunks: list[RagChunk] | None,
    sql_rows: list[dict[str, Any]] | None,
    data_source: str | None,
) -> str | None:
    try:
        return await generate_chat_answer(
            query=query,
            semantic_context=semantic_context,
            memory_context=memory_context,
            preference_context=preference_context,
            rag_chunks=rag_chunks,
            sql_rows=sql_rows,
            data_source=data_source,
        )
    except Exception as exc:
        logger.warning("LLM answer generation failed: %s", exc)
        return None


def _publish_query_result(
    *,
    request_id: str,
    trace_id: str,
    principal: JWTClaims,
    sensitivity_tier: int,
    rows: list[dict[str, Any]],
    answer: str,
    data_source: str | None,
    generated_sql: str,
    cache_hit: bool = False,
    cache_timestamp: str | None = None,
    cache_similarity: float | None = None,
    confidence_state: str | None = None,
    conflict_detail: str | None = None,
    provenance: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    queue = get_stream_queue()
    _explanation_store[request_id] = (
        principal.sub,
        _explanation_generator.explain_kw(sql=generated_sql, metric_context=None),
    )
    get_export_service().register_query_result(
        request_id=request_id,
        owner_user_id=principal.sub,
        department_scope=principal.department,
        sensitivity_tier=sensitivity_tier,
        rows=rows,
        trace_id=trace_id,
        data_source=data_source,
    )
    if rows:
        queue.push(request_id, make_row_event(rows=rows, chunk_index=0))
    queue.push(
        request_id,
        make_done_event(
            trace_id=trace_id,
            answer=answer,
            cache_hit=cache_hit,
            cache_timestamp=cache_timestamp,
            freshness_indicator=_format_cache_freshness_indicator(cache_timestamp) if cache_timestamp else None,
            cache_similarity=cache_similarity,
            force_refresh_available=cache_hit,
            confidence_state=confidence_state,
            conflict_detail=conflict_detail,
            provenance=provenance,
            sources=sources,
        ),
    )
    queue.close(request_id)


def _serve_cached_query_result(
    *,
    request_id: str,
    trace_id: str,
    principal: JWTClaims,
    session_id: str,
    query: str,
    sensitivity_tier: int,
    semantic_context: list[dict[str, Any]],
    cache_hit: CacheLookupResult,
) -> None:
    _record_query_interaction(
        query=query,
        principal=principal,
        session_id=session_id,
        semantic_context=semantic_context,
    )
    _publish_query_result(
        request_id=request_id,
        trace_id=trace_id,
        principal=principal,
        sensitivity_tier=sensitivity_tier,
        rows=cache_hit.entry.rows,
        answer=cache_hit.entry.answer,
        data_source=cache_hit.entry.data_source,
        generated_sql=cache_hit.entry.generated_sql,
        cache_hit=True,
        cache_timestamp=cache_hit.entry.created_at,
        cache_similarity=cache_hit.similarity,
    )


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
    cerbos_client: CerbosClient,
    trace_id: str,
    sensitivity_tier: int = 1,
    execution_settings: dict[str, Any] | None = None,
    semantic_context: list[dict[str, Any]] | None = None,
    memory_context: dict[str, Any] | None = None,
    preference_context: list[dict[str, Any]] | None = None,
    cache_context: QueryCacheContext | None = None,
) -> None:
    """Background task: run LangGraph, store explanation keyed by request_id + user_id."""
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
        rag_retrieval = _safe_rag_search(
            query=query,
            principal=principal,
            cerbos_client=cerbos_client,
        )
        if timeout_seconds is not None:
            result, rag_chunks = await asyncio.wait_for(
                asyncio.gather(invoke, rag_retrieval),
                timeout=timeout_seconds,
            )
        else:
            result, rag_chunks = await asyncio.gather(invoke, rag_retrieval)
        _apply_query_execution_settings(result, execution_settings=execution_settings)
        secured_rows = _apply_runtime_security(result, principal=principal)
        fallback_sql = f"SELECT * FROM oracle WHERE query='{query[:40]}'"
        if semantic_context:
            fallback_sql = f"SELECT {semantic_context[0]['formula']} FROM semantic_layer"
        generated_sql = result.get("generated_sql", fallback_sql)
        _record_query_interaction(
            query=query,
            principal=principal,
            session_id=session_id,
            semantic_context=semantic_context,
        )
        answer = result.get("final_response", "stub") or "stub"
        sources: list[dict[str, Any]] | None = None
        if rag_chunks:
            sql_result = None
            if secured_rows:
                sql_result = SqlResult(
                    data=secured_rows,
                    trace_id=trace_id,
                    table_name=str(result.get("data_source") or "query_result"),
                    timestamp=datetime.now(UTC).isoformat(),
                )
            hybrid = merge_results(sql_result=sql_result, rag_chunks=rag_chunks)
            answer = compose_answer(hybrid)
            citations = format_citations(hybrid)
            sources = [
                {
                    "doc_id": chunk.document_id,
                    "title": chunk.source_name,
                    "page": chunk.page_number,
                }
                for chunk in rag_chunks
            ]
            result["rag_result"] = {
                "citations": citations,
                "source_count": len(rag_chunks),
            }
        llm_answer = await _safe_generate_chat_answer(
            query=query,
            semantic_context=semantic_context,
            memory_context=memory_context,
            preference_context=preference_context,
            rag_chunks=rag_chunks,
            sql_rows=secured_rows,
            data_source=str(result.get("data_source") or ""),
        )
        if llm_answer:
            answer = llm_answer
        if result.get("data_source_warning"):
            answer = f"{answer}\n\n[warning] {result['data_source_warning']}"
        if _is_data_inventory_query(query):
            answer = _build_data_inventory_answer(principal)
        semantic_no_data_answer = _build_semantic_no_data_answer(
            semantic_context=semantic_context,
            generated_sql=generated_sql,
            data_source=str(result.get("data_source") or ""),
            max_available_date=result.get("max_available_date"),
        )
        if semantic_no_data_answer and not _has_meaningful_sql_values(secured_rows):
            answer = semantic_no_data_answer
            if result.get("data_source_warning"):
                answer = f"{answer}\n\n[warning] {result['data_source_warning']}"
        if cache_context is not None:
            get_query_result_cache().store(
                CachedQueryResult.build(
                    context=cache_context,
                    answer=answer,
                    rows=secured_rows,
                    generated_sql=generated_sql,
                    data_source=result.get("data_source"),
                    pii_scan_mode=result.get("pii_scan_mode"),
                )
            )
        _publish_query_result(
            request_id=request_id,
            trace_id=trace_id,
            principal=principal,
            sensitivity_tier=sensitivity_tier,
            rows=secured_rows,
            answer=answer,
            data_source=result.get("data_source"),
            generated_sql=generated_sql,
            sources=sources,
        )
    except TimeoutError:
        logger.warning("Graph execution timed out for request %s", request_id)
        get_stream_queue().push(
            request_id,
            make_error_event(
                error_code="timeout",
                message="Query execution timed out",
                trace_id=trace_id,
            ),
        )
        get_stream_queue().close(request_id)
    except Exception as exc:
        logger.warning("Graph execution failed for request %s: %s", request_id, exc)
        get_stream_queue().push(
            request_id,
            make_error_event(
                error_code="stream-error",
                message="Query execution failed",
                trace_id=trace_id,
            ),
        )
        get_stream_queue().close(request_id)


async def _run_cross_domain_query_and_cache_explanation(
    *,
    request_id: str,
    query: str,
    session_id: str,
    principal: JWTClaims,
    trace_id: str,
    sensitivity_tier: int = 1,
    semantic_context: list[dict[str, Any]] | None = None,
) -> None:
    try:
        result = execute_cross_domain_query(
            query=query,
            principal_user_id=principal.sub,
            principal_department=principal.department,
            session_id=session_id,
            request_id=request_id,
        )
        _record_query_interaction(
            query=query,
            principal=principal,
            session_id=session_id,
            semantic_context=semantic_context,
        )
        _publish_query_result(
            request_id=request_id,
            trace_id=trace_id,
            principal=principal,
            sensitivity_tier=sensitivity_tier,
            rows=result.rows,
            answer=result.answer,
            data_source=result.data_source,
            generated_sql=result.generated_sql,
            confidence_state="cross-source-conflict" if result.discrepancy_detected else None,
            conflict_detail=result.discrepancy_detail,
            provenance=result.provenance,
        )
    except Exception as exc:
        logger.warning("Cross-domain execution failed for request %s: %s", request_id, exc)
        get_stream_queue().push(
            request_id,
            make_error_event(
                error_code="stream-error",
                message="Cross-domain query execution failed",
                trace_id=trace_id,
            ),
        )
        get_stream_queue().close(request_id)


@router.post("/v1/chat/query", response_model=ChatQueryStreamHandle)
async def chat_query(
    payload: ChatQueryRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
    cerbos: CerbosClient = CERBOS_CLIENT_DEP,
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
    allowed_metrics = get_user_role_management_service().allowed_metrics_for_principal(principal)
    semantic_decision = get_semantic_layer_service().resolve_query(
        query=payload.query,
        principal=principal,
        allowed_terms=allowed_metrics,
    )
    semantic_context = semantic_decision.semantic_context
    _record_semantic_resolve_audit(
        request_id=request_id,
        principal=principal,
        session_id=str(payload.session_id),
        decision=semantic_decision,
    )
    memory_service = get_conversation_memory_service()
    memory_context = memory_service.build_context_bundle(
        user_id=principal.sub,
        department_id=principal.department,
        clearance=principal.clearance,
        query=payload.query,
    )
    preference_context = memory_service.get_suggestions(user_id=principal.sub)
    cache_context = _build_cache_context(
        query=payload.query,
        principal=principal,
        semantic_context=semantic_context,
        execution_settings=execution_settings,
    )
    current_span.set_attribute("aial.semantic_match_count", len(semantic_context))
    current_span.set_attribute("aial.semantic_resolve_status", semantic_decision.status)
    current_span.set_attribute("aial.semantic_resolve_confidence", semantic_decision.confidence)
    current_span.set_attribute("aial.memory_summary_count", len(memory_context.get("summaries", [])))
    current_span.set_attribute("aial.query_cache.role_scope", cache_context.role_scope)
    current_span.set_attribute("aial.query_cache.semantic_layer_version", cache_context.semantic_layer_version)
    current_span.set_attribute("aial.query_cache.freshness_class", cache_context.data_freshness_class)
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
    semantic_clarification = _build_semantic_clarification_answer(semantic_decision)
    if semantic_clarification:
        _publish_query_result(
            request_id=request_id,
            trace_id=trace_id,
            principal=principal,
            sensitivity_tier=intent.sensitivity_tier,
            rows=[],
            answer=semantic_clarification,
            data_source=None,
            generated_sql="",
            confidence_state=semantic_decision.status,
            provenance=[semantic_decision.to_audit_dict()],
        )
        return ChatQueryStreamHandle(
            request_id=request_id,
            status="streaming",
            trace_id=trace_id,
            message="Cần xác nhận semantic trước khi truy vấn dữ liệu.",
        )
    if is_cross_domain_query(payload.query):
        current_span.set_attribute("aial.query_mode", "cross_domain")
        asyncio.create_task(
            _run_cross_domain_query_and_cache_explanation(
                request_id=request_id,
                query=payload.query,
                session_id=str(payload.session_id),
                principal=principal,
                trace_id=trace_id,
                sensitivity_tier=intent.sensitivity_tier,
                semantic_context=semantic_context,
            )
        )
        return ChatQueryStreamHandle(
            request_id=request_id,
            status="streaming",
            trace_id=trace_id,
            message="Dang phan ra hai truy van FINANCE va BUDGET de hop nhat ket qua...",
        )
    cache_service = get_query_result_cache()
    current_span.set_attribute("aial.query_cache.force_refresh", payload.force_refresh)
    if payload.force_refresh:
        cache_service.record_force_refresh()
        cache_service.invalidate_query(cache_context, reason="force_refresh")
    else:
        cache_hit = cache_service.find_best_match(cache_context)
        if cache_hit is not None:
            current_span.set_attribute("aial.query_cache.hit", True)
            current_span.set_attribute("aial.query_cache.similarity", cache_hit.similarity)
            _serve_cached_query_result(
                request_id=request_id,
                trace_id=trace_id,
                principal=principal,
                session_id=str(payload.session_id),
                query=payload.query,
                sensitivity_tier=intent.sensitivity_tier,
                semantic_context=semantic_context,
                cache_hit=cache_hit,
            )
            return ChatQueryStreamHandle(
                request_id=request_id,
                status="streaming",
                trace_id=trace_id,
                message=execution_settings.get("warning") if execution_settings else None,
                cache_hit=True,
                cache_timestamp=cache_hit.entry.created_at,
                freshness_indicator=_format_cache_freshness_indicator(cache_hit.entry.created_at),
                cache_similarity=cache_hit.similarity,
            )
    current_span.set_attribute("aial.query_cache.hit", False)

    # Fire-and-forget: do NOT await — return stream handle immediately
    asyncio.create_task(
        _run_graph_and_cache_explanation(
            request_id=request_id,
            query=payload.query,
            session_id=str(payload.session_id),
            principal=principal,
            trace_id=trace_id,
            sensitivity_tier=intent.sensitivity_tier,
            cerbos_client=cerbos,
            execution_settings=execution_settings,
            semantic_context=semantic_context,
            memory_context=memory_context,
            preference_context=preference_context,
            cache_context=cache_context,
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
