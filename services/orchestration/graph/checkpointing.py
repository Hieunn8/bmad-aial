"""Checkpoint helpers for LangGraph graph execution."""

from __future__ import annotations

import json
import os
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis import RedisSaver
from redis import Redis

DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


def create_redis_checkpointer(redis_url: str = DEFAULT_REDIS_URL) -> RedisSaver:
    saver = RedisSaver.from_conn_string(redis_url)
    saver.setup()
    return saver


class FakeRedisSaver(InMemorySaver):
    """In-memory LangGraph saver that mirrors writes into fakeredis for tests."""

    def __init__(self, redis_client: Redis) -> None:
        super().__init__()
        self.redis_client = redis_client

    def put(
        self,
        config: dict[str, Any],
        checkpoint: Any,
        metadata: Any,
        new_versions: Any,
    ) -> dict[str, Any]:
        normalized_config = {
            **config,
            "configurable": {
                "checkpoint_ns": "",
                **config["configurable"],
            },
        }
        updated_config = super().put(normalized_config, checkpoint, metadata, new_versions)
        thread_id = normalized_config["configurable"]["thread_id"]
        checkpoint_id = updated_config["configurable"]["checkpoint_id"]
        key = f"aial:test:checkpoint:{thread_id}:{checkpoint_id}"
        payload = json.dumps(
            {
                "checkpoint": checkpoint,
                "metadata": metadata,
                "new_versions": new_versions,
            },
            default=str,
        )
        self.redis_client.set(key, payload.encode("utf-8"))
        return updated_config
