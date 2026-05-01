"""SSE event types for query streaming (Story 2A.5).

Event format follows FMT-2 from architecture.md:
  data: {"type": "<type>", ...}\n\n
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class SseEventType:
    THINKING = "thinking"
    STEP = "step"
    ROW = "row"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True)
class SseEvent:
    type: str
    data: dict[str, Any]

    def to_sse(self) -> str:
        payload = json.dumps({"type": self.type, **self.data})
        return f"data: {payload}\n\n"


def make_thinking_event(*, phase: int, message: str) -> SseEvent:
    return SseEvent(type=SseEventType.THINKING, data={"phase": phase, "message": message})


def make_step_event(*, step: int, total: int, description: str) -> SseEvent:
    return SseEvent(type=SseEventType.STEP, data={"step": step, "total": total, "description": description})


def make_row_event(*, rows: list[dict[str, Any]], chunk_index: int) -> SseEvent:
    return SseEvent(type=SseEventType.ROW, data={"rows": rows, "chunk_index": chunk_index})


def make_done_event(*, trace_id: str, answer: str = "") -> SseEvent:
    return SseEvent(type=SseEventType.DONE, data={"trace_id": trace_id, "answer": answer})


def make_error_event(*, code: str, message: str) -> SseEvent:
    return SseEvent(type=SseEventType.ERROR, data={"code": code, "message": message})
