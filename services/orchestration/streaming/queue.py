"""In-memory SSE event queue — per request_id (Story 2A.5).

Each POST /v1/chat/query creates a queue keyed by request_id.
The GET /v1/chat/stream/{request_id} endpoint drains the queue.
LangGraph nodes push events into the queue during processing.

Ownership: request_id is bound to user_id at creation time.
The stream endpoint verifies ownership before delivering events.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator

from orchestration.streaming.events import SseEvent


class StreamEventQueue:
    def __init__(self) -> None:
        self._queues: dict[str, deque[SseEvent]] = {}
        self._closed: set[str] = set()
        self._owners: dict[str, str] = {}  # request_id → user_id

    def create(self, request_id: str, *, owner_user_id: str) -> None:
        self._queues[request_id] = deque()
        self._owners[request_id] = owner_user_id

    def verify_owner(self, request_id: str, user_id: str) -> bool:
        """Return True only if this user owns the stream. Unknown request_ids return False."""
        return self._owners.get(request_id) == user_id

    def push(self, request_id: str, event: SseEvent) -> None:
        if request_id in self._queues:
            self._queues[request_id].append(event)

    def drain(self, request_id: str) -> Iterator[SseEvent]:
        queue = self._queues.get(request_id)
        if queue is None:
            return
        while queue:
            yield queue.popleft()

    def close(self, request_id: str) -> None:
        self._closed.add(request_id)

    def is_closed(self, request_id: str) -> bool:
        return request_id in self._closed

    def cleanup(self, request_id: str) -> None:
        self._queues.pop(request_id, None)
        self._closed.discard(request_id)
        self._owners.pop(request_id, None)


# Module-level singleton — shared across requests in the same process
_global_queue = StreamEventQueue()


def get_stream_queue() -> StreamEventQueue:
    return _global_queue
