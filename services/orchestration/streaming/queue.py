"""In-memory SSE event queue per request_id."""

from __future__ import annotations

import asyncio
from asyncio import QueueEmpty
from collections.abc import Iterator

from orchestration.streaming.events import SseEvent


class StreamEventQueue:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[SseEvent]] = {}
        self._closed: set[str] = set()
        self._owners: dict[str, str] = {}

    def create(self, request_id: str, *, owner_user_id: str) -> None:
        self._queues[request_id] = asyncio.Queue()
        self._closed.discard(request_id)
        self._owners[request_id] = owner_user_id

    def verify_owner(self, request_id: str, user_id: str) -> bool:
        return self._owners.get(request_id) == user_id

    def push(self, request_id: str, event: SseEvent) -> None:
        queue = self._queues.get(request_id)
        if queue is not None:
            queue.put_nowait(event)

    def drain(self, request_id: str) -> Iterator[SseEvent]:
        queue = self._queues.get(request_id)
        if queue is None:
            return
        while True:
            try:
                yield queue.get_nowait()
            except QueueEmpty:
                return

    async def next_event(self, request_id: str, *, poll_interval: float = 0.25) -> SseEvent | None:
        while True:
            queue = self._queues.get(request_id)
            if queue is None:
                return None
            if self.is_closed(request_id) and queue.empty():
                return None
            try:
                return await asyncio.wait_for(queue.get(), timeout=poll_interval)
            except TimeoutError:
                if self.is_closed(request_id) and queue.empty():
                    return None

    def close(self, request_id: str) -> None:
        self._closed.add(request_id)

    def is_closed(self, request_id: str) -> bool:
        return request_id in self._closed

    def cleanup(self, request_id: str) -> None:
        self._queues.pop(request_id, None)
        self._closed.discard(request_id)
        self._owners.pop(request_id, None)


_global_queue = StreamEventQueue()


def get_stream_queue() -> StreamEventQueue:
    return _global_queue
