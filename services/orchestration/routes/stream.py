"""SSE stream endpoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from opentelemetry import trace

from aial_shared.auth.fastapi_deps import get_current_user
from aial_shared.auth.keycloak import JWTClaims
from orchestration.streaming.queue import get_stream_queue

router = APIRouter()
CURRENT_USER_DEP = Depends(get_current_user)


async def _event_generator(request_id: str) -> AsyncGenerator[str, None]:
    queue = get_stream_queue()
    try:
        while True:
            event = await queue.next_event(request_id)
            if event is None:
                return
            yield event.to_sse()
    finally:
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
