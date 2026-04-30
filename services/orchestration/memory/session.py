"""Short-term session memory — Story 2A.6.

Security invariants:
  - Session key = user_id + department_id + session_id (cross-user injection impossible).
  - TTL = 24 h; expired sessions return empty history.
  - Cerbos re-checked every turn (enforced in query route, not here).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_TTL_SECONDS = 86_400  # 24 hours


@dataclass
class SessionMemory:
    user_id: str
    department_id: str
    session_id: str
    turns: list[dict[str, str]] = field(default_factory=list)


class SessionMemoryStore:
    def __init__(self, redis: Any) -> None:
        self._redis = redis

    def _make_key(self, user_id: str, department_id: str, session_id: str) -> str:
        return f"aial:session:{user_id}:{department_id}:{session_id}"

    def append_turn(
        self,
        user_id: str,
        department_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        key = self._make_key(user_id, department_id, session_id)
        turn = json.dumps({"user": user_message, "assistant": assistant_message})
        self._redis.rpush(key, turn)
        self._redis.expire(key, _TTL_SECONDS)

    def get_history(
        self,
        user_id: str,
        department_id: str,
        session_id: str,
    ) -> list[dict[str, str]]:
        key = self._make_key(user_id, department_id, session_id)
        raw = self._redis.lrange(key, 0, -1)
        if not raw:
            return []
        return [json.loads(item) for item in raw]
