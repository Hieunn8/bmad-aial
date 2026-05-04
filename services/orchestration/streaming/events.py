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


def make_done_event(
    *,
    trace_id: str,
    answer: str = "",
    cache_hit: bool = False,
    cache_timestamp: str | None = None,
    freshness_indicator: str | None = None,
    cache_similarity: float | None = None,
    force_refresh_available: bool = False,
    confidence_state: str | None = None,
    conflict_detail: str | None = None,
    provenance: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> SseEvent:
    data: dict[str, Any] = {"trace_id": trace_id, "answer": answer}
    if cache_hit:
        data["cache_hit"] = True
    if cache_timestamp is not None:
        data["cache_timestamp"] = cache_timestamp
    if freshness_indicator is not None:
        data["freshness_indicator"] = freshness_indicator
    if cache_similarity is not None:
        data["cache_similarity"] = cache_similarity
    if force_refresh_available:
        data["force_refresh_available"] = True
    if confidence_state is not None:
        data["confidence_state"] = confidence_state
    if conflict_detail is not None:
        data["conflict_detail"] = conflict_detail
    if provenance is not None:
        data["provenance"] = provenance
    if sources is not None:
        data["sources"] = sources
    return SseEvent(type=SseEventType.DONE, data=data)


def make_error_event(*, error_code: str, message: str, trace_id: str | None = None) -> SseEvent:
    data: dict[str, Any] = {"error_code": error_code, "message": message}
    if trace_id is not None:
        data["trace_id"] = trace_id
    return SseEvent(type=SseEventType.ERROR, data=data)
