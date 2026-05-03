"""Conversation memory, preferences, templates, and history APIs for Epic 5B."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.memory.long_term import get_conversation_memory_service

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


class SessionSummaryRequest(BaseModel):
    session_id: str
    sensitivity_level: int
    intent_type: str
    topic: str
    filter_context: str
    summary_text: str


class SavedTemplateRequest(BaseModel):
    name: str
    query_intent: str
    filters: str
    time_range: str
    output_format: str


class PreferenceLearningRequest(BaseModel):
    enabled: bool


@router.post("/v1/chat/memory/summaries", status_code=201)
async def create_session_summary(
    body: SessionSummaryRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    summary = get_conversation_memory_service().store_session_summary(
        user_id=principal.sub,
        department_id=principal.department,
        session_id=body.session_id,
        sensitivity_level=body.sensitivity_level,
        intent_type=body.intent_type,
        topic=body.topic,
        filter_context=body.filter_context,
        summary_text=body.summary_text,
    )
    return {"summary": summary.to_dict()}


@router.get("/v1/chat/memory/context")
async def get_memory_context(
    query: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    return get_conversation_memory_service().build_context_bundle(
        user_id=principal.sub,
        department_id=principal.department,
        clearance=principal.clearance,
        query=query,
    )


@router.put("/v1/chat/preferences/learning")
async def set_preference_learning(
    body: PreferenceLearningRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    enabled = get_conversation_memory_service().set_learning_enabled(
        user_id=principal.sub,
        enabled=body.enabled,
    )
    return {"enabled": enabled}


@router.get("/v1/chat/suggestions")
async def get_suggestions(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    suggestions = get_conversation_memory_service().get_suggestions(user_id=principal.sub)
    return {"suggestions": suggestions, "total": len(suggestions)}


@router.post("/v1/chat/templates", status_code=201)
async def save_template(
    body: SavedTemplateRequest,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    template = get_conversation_memory_service().save_template(
        user_id=principal.sub,
        name=body.name,
        query_intent=body.query_intent,
        filters=body.filters,
        time_range=body.time_range,
        output_format=body.output_format,
    )
    return {"template": template.to_dict()}


@router.get("/v1/chat/templates")
async def list_templates(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    templates = get_conversation_memory_service().list_templates(user_id=principal.sub)
    return {"templates": [template.to_dict() for template in templates], "total": len(templates)}


@router.get("/v1/chat/history/search")
async def search_history(
    keyword: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    results = get_conversation_memory_service().search_history(
        user_id=principal.sub,
        keyword=keyword,
        topic=topic,
        date_from=date_from,
        date_to=date_to,
    )
    return {"results": [result.to_dict() for result in results], "total": len(results)}


@router.post("/v1/chat/history/{entry_id}/reuse")
async def reuse_history_entry(
    entry_id: str,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> dict[str, Any]:
    try:
        payload = get_conversation_memory_service().reuse_history_entry(
            user_id=principal.sub,
            entry_id=entry_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="History entry not found") from exc
    return {"preload": payload}


@router.get("/v1/chat/history/audit")
async def memory_audit(principal: JWTClaims = CURRENT_USER_DEP) -> dict[str, Any]:
    violations = get_conversation_memory_service().memory_audit(user_id=principal.sub)
    return {"violations": violations, "total": len(violations)}
