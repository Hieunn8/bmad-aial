"""SSE stream endpoint — Story 2A.5.

GET /v1/chat/stream/{request_id} — returns text/event-stream.

Security invariants:
  - Only serves streams for request_ids pre-registered via POST /v1/chat/query.
  - Ownership verified before any event is emitted.
  - Unknown request_ids → 404, not a synthetic stream.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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

    yield make_thinking_event(phase=1, message="Đang phân tích...").to_sse()

    for event in queue.drain(request_id):
        yield event.to_sse()

    if queue.is_closed(request_id):
        queue.cleanup(request_id)
        return

    for i, description in enumerate(_WALKING_SKELETON_STEPS, start=1):
        yield make_step_event(step=i, total=len(_WALKING_SKELETON_STEPS), description=description).to_sse()

    yield make_done_event(trace_id=request_id, answer="stub").to_sse()

    queue.close(request_id)
    queue.cleanup(request_id)


@router.get("/v1/chat/stream/{request_id}")
async def stream_query_result(
    request_id: UUID,
    principal: JWTClaims = CURRENT_USER_DEP,
) -> StreamingResponse:
    span = trace.get_current_span()
    span.set_attribute("aial.request_id", str(request_id))
    span.set_attribute("aial.user_id", principal.sub)

    queue = get_stream_queue()
    req_id_str = str(request_id)

    # Strict: only serve pre-registered request_ids (created by POST /v1/chat/query)
    if req_id_str not in queue._owners:
        raise HTTPException(
            status_code=404,
            detail="Stream not found — submit a query first via POST /v1/chat/query",
        )

    if not queue.verify_owner(req_id_str, principal.sub):
        raise HTTPException(status_code=403, detail="Stream does not belong to this user")

    return StreamingResponse(
        _event_generator(req_id_str),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
