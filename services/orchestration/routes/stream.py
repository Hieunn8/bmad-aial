"""SSE stream endpoint — Story 2A.5.

GET /v1/chat/stream/{request_id} — returns text/event-stream.
Emits: thinking → step(s) → done events for the given request.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from opentelemetry import trace

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.streaming.events import (
    make_done_event,
    make_step_event,
    make_thinking_event,
)
from orchestration.streaming.queue import get_stream_queue

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)

_WALKING_SKELETON_STEPS = [
    "Phân loại yêu cầu",
    "Truy vấn Oracle",
    "Tổng hợp kết quả",
    "Hoàn thành",
]


async def _event_generator(request_id: str) -> AsyncGenerator[str, None]:
    queue = get_stream_queue()
    trace_id = request_id

    # Emit thinking pulse
    yield make_thinking_event(phase=1, message="Đang phân tích...").to_sse()

    # Drain any queued events pushed by LangGraph
    for event in queue.drain(request_id):
        yield event.to_sse()

    # Emit walking-skeleton step narration
    for i, description in enumerate(_WALKING_SKELETON_STEPS, start=1):
        yield make_step_event(step=i, total=len(_WALKING_SKELETON_STEPS), description=description).to_sse()

    # Emit done
    yield make_done_event(trace_id=trace_id, answer="stub").to_sse()

    queue.close(request_id)
    queue.cleanup(request_id)


@router.get("/v1/chat/stream/{request_id}")
async def stream_query_result(
    request_id: UUID,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> StreamingResponse:
    from fastapi import HTTPException

    span = trace.get_current_span()
    span.set_attribute("aial.request_id", str(request_id))
    span.set_attribute("aial.user_id", principal.sub)

    queue = get_stream_queue()
    req_id_str = str(request_id)

    # If the request was pre-registered, verify ownership.
    # Unknown request_ids are allowed (walking skeleton creates queue lazily).
    if req_id_str in queue._owners and not queue.verify_owner(req_id_str, principal.sub):
        raise HTTPException(status_code=403, detail="Stream does not belong to this user")

    return StreamingResponse(
        _event_generator(req_id_str),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
