"""Redis-backed semantic query result cache for Story 6.3."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from difflib import SequenceMatcher
from functools import lru_cache
from hashlib import sha256
from typing import Any

from redis import Redis

logger = logging.getLogger(__name__)

DEFAULT_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
_QUERY_CACHE_TTL_SECONDS = 300
_QUERY_CACHE_SIMILARITY_THRESHOLD = 0.85
_CACHE_OVERRIDE: QueryResultCache | None = None
_STOPWORDS = {
    "cho",
    "toi",
    "tôi",
    "xem",
    "show",
    "me",
    "please",
    "hay",
    "hãy",
    "xin",
    "giup",
    "giúp",
    "can",
    "need",
}


class InMemoryRedis:
    """Small Redis-like store with TTL support for local fallback/tests."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._sets: dict[str, set[str]] = {}
        self._expires_at: dict[str, float] = {}

    def _purge_if_expired(self, key: str) -> None:
        expires_at = self._expires_at.get(key)
        if expires_at is None or expires_at > time.time():
            return
        self.delete(key)

    def ping(self) -> bool:
        return True

    def set(self, key: str, value: str) -> None:
        self._purge_if_expired(key)
        self._values[key] = value

    def get(self, key: str) -> str | None:
        self._purge_if_expired(key)
        return self._values.get(key)

    def sadd(self, key: str, *values: str) -> None:
        self._purge_if_expired(key)
        self._sets.setdefault(key, set()).update(values)

    def smembers(self, key: str) -> set[str]:
        self._purge_if_expired(key)
        return set(self._sets.get(key, set()))

    def srem(self, key: str, *values: str) -> None:
        self._purge_if_expired(key)
        if key not in self._sets:
            return
        for value in values:
            self._sets[key].discard(value)
        if not self._sets[key]:
            self._sets.pop(key, None)
            self._expires_at.pop(key, None)

    def expire(self, key: str, ttl_seconds: int) -> bool:
        if key not in self._values and key not in self._sets:
            return False
        self._expires_at[key] = time.time() + ttl_seconds
        return True

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            existed = key in self._values or key in self._sets
            self._values.pop(key, None)
            self._sets.pop(key, None)
            self._expires_at.pop(key, None)
            deleted += int(existed)
        return deleted

    def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        remaining = int(expires_at - time.time())
        return max(remaining, -2)


@dataclass(frozen=True)
class QueryCacheContext:
    query: str
    normalized_intent: str
    owner_user_id: str
    department_id: str
    role_scope: str
    semantic_layer_version: str
    data_freshness_class: str


@dataclass(frozen=True)
class CachedQueryResult:
    owner_user_id: str
    original_query: str
    normalized_intent: str
    department_id: str
    role_scope: str
    semantic_layer_version: str
    data_freshness_class: str
    created_at: str
    answer: str
    rows: list[dict[str, Any]]
    generated_sql: str
    data_source: str | None = None
    pii_scan_mode: str | None = None

    @classmethod
    def build(
        cls,
        *,
        context: QueryCacheContext,
        answer: str,
        rows: list[dict[str, Any]],
        generated_sql: str,
        data_source: str | None,
        pii_scan_mode: str | None,
    ) -> "CachedQueryResult":
        return cls(
            owner_user_id=context.owner_user_id,
            original_query=context.query,
            normalized_intent=context.normalized_intent,
            department_id=context.department_id,
            role_scope=context.role_scope,
            semantic_layer_version=context.semantic_layer_version,
            data_freshness_class=context.data_freshness_class,
            created_at=datetime.now(UTC).isoformat(),
            answer=answer,
            rows=rows,
            generated_sql=generated_sql,
            data_source=data_source,
            pii_scan_mode=pii_scan_mode,
        )


@dataclass(frozen=True)
class CacheLookupResult:
    entry: CachedQueryResult
    similarity: float
    cache_key: str


def normalize_query_intent(query: str) -> str:
    normalized = query.casefold()
    replacements = {
        "chia theo": "theo",
        "cho tôi xem": " ",
        "cho toi xem": " ",
        "vui lòng": " ",
        "hãy": " ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    tokens = [
        token
        for token in re.findall(r"\w+", normalized, flags=re.UNICODE)
        if token and token not in _STOPWORDS
    ]
    deduped_tokens = list(dict.fromkeys(tokens))
    return " ".join(sorted(deduped_tokens))


def _compute_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    union = left_tokens | right_tokens
    token_score = len(left_tokens & right_tokens) / len(union) if union else 0.0
    sequence_score = SequenceMatcher(a=left, b=right).ratio()
    return round((token_score * 0.7) + (sequence_score * 0.3), 4)


class QueryResultCache:
    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client
        self._stats = {
            "hits": 0,
            "misses": 0,
            "force_refreshes": 0,
            "invalidations_total": 0,
            "invalidations_by_reason": {},
        }

    def _scope_fingerprint(self, context: QueryCacheContext) -> str:
        payload = (
            f"{context.department_id}|{context.role_scope}|"
            f"{context.semantic_layer_version}|{context.data_freshness_class}"
        )
        return sha256(payload.encode("utf-8")).hexdigest()

    def _entry_key(self, context: QueryCacheContext) -> str:
        scope = self._scope_fingerprint(context)
        digest = sha256(f"{context.owner_user_id}|{context.normalized_intent}".encode("utf-8")).hexdigest()
        return f"aial:cache:query:{scope}:{digest}:result"

    def _scope_index_key(self, context: QueryCacheContext) -> str:
        return f"aial:cache:query:index:{self._scope_fingerprint(context)}"

    def _user_index_key(self, user_id: str) -> str:
        return f"aial:cache:query:user:{user_id}"

    def _load_entry(self, key: str) -> CachedQueryResult | None:
        raw = self._redis.get(key)
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Skipping malformed semantic cache entry: %s", key)
            self._redis.delete(key)
            return None
        return CachedQueryResult(**payload)

    def store(self, entry: CachedQueryResult) -> str:
        context = QueryCacheContext(
            query=entry.original_query,
            normalized_intent=entry.normalized_intent,
            owner_user_id=entry.owner_user_id,
            department_id=entry.department_id,
            role_scope=entry.role_scope,
            semantic_layer_version=entry.semantic_layer_version,
            data_freshness_class=entry.data_freshness_class,
        )
        entry_key = self._entry_key(context)
        scope_index_key = self._scope_index_key(context)
        user_index_key = self._user_index_key(entry.owner_user_id)
        serialized = json.dumps(asdict(entry), ensure_ascii=False)
        self._redis.set(entry_key, serialized)
        self._redis.expire(entry_key, _QUERY_CACHE_TTL_SECONDS)
        self._redis.sadd(scope_index_key, entry_key)
        self._redis.expire(scope_index_key, _QUERY_CACHE_TTL_SECONDS)
        self._redis.sadd(user_index_key, entry_key)
        self._redis.expire(user_index_key, _QUERY_CACHE_TTL_SECONDS)
        return entry_key

    def find_best_match(self, context: QueryCacheContext) -> CacheLookupResult | None:
        best_match: CacheLookupResult | None = None
        for entry_key in self._redis.smembers(self._scope_index_key(context)):
            entry = self._load_entry(entry_key)
            if entry is None:
                self._redis.srem(self._scope_index_key(context), entry_key)
                continue
            similarity = _compute_similarity(context.normalized_intent, entry.normalized_intent)
            if similarity < _QUERY_CACHE_SIMILARITY_THRESHOLD:
                continue
            if best_match is None or similarity > best_match.similarity:
                best_match = CacheLookupResult(entry=entry, similarity=similarity, cache_key=entry_key)
        if best_match is None:
            self._stats["misses"] += 1
            return None
        self._stats["hits"] += 1
        return best_match

    def invalidate_user_entries(self, user_id: str, *, reason: str = "permission_change") -> int:
        user_index_key = self._user_index_key(user_id)
        entry_keys = list(self._redis.smembers(user_index_key))
        deleted = 0
        for entry_key in entry_keys:
            entry = self._load_entry(entry_key)
            if entry is not None:
                context = QueryCacheContext(
                    query=entry.original_query,
                    normalized_intent=entry.normalized_intent,
                    owner_user_id=entry.owner_user_id,
                    department_id=entry.department_id,
                    role_scope=entry.role_scope,
                    semantic_layer_version=entry.semantic_layer_version,
                    data_freshness_class=entry.data_freshness_class,
                )
                self._redis.srem(self._scope_index_key(context), entry_key)
            deleted += self._redis.delete(entry_key)
        self._redis.delete(user_index_key)
        self._record_invalidation(reason=reason, entry_count=deleted)
        return deleted

    def invalidate_query(self, context: QueryCacheContext, *, reason: str = "manual_refresh") -> int:
        deleted = 0
        scope_index_key = self._scope_index_key(context)
        for entry_key in self._redis.smembers(scope_index_key):
            entry = self._load_entry(entry_key)
            if entry is None:
                self._redis.srem(scope_index_key, entry_key)
                continue
            if entry.normalized_intent != context.normalized_intent:
                continue
            self._redis.srem(scope_index_key, entry_key)
            self._redis.srem(self._user_index_key(entry.owner_user_id), entry_key)
            deleted += self._redis.delete(entry_key)
        self._record_invalidation(reason=reason, entry_count=deleted)
        return deleted

    def record_force_refresh(self) -> None:
        self._stats["force_refreshes"] += 1

    def _record_invalidation(self, *, reason: str, entry_count: int) -> None:
        reason_counts = self._stats["invalidations_by_reason"]
        reason_counts[reason] = int(reason_counts.get(reason, 0)) + entry_count
        self._stats["invalidations_total"] += entry_count

    def get_stats(self) -> dict[str, float | dict[str, int]]:
        hits = self._stats["hits"]
        misses = self._stats["misses"]
        total = hits + misses
        return {
            "hits": float(hits),
            "misses": float(misses),
            "force_refreshes": float(self._stats["force_refreshes"]),
            "invalidations_total": float(self._stats["invalidations_total"]),
            "invalidations_by_reason": dict(self._stats["invalidations_by_reason"]),
            "hit_rate": round(hits / total, 4) if total else 0.0,
        }

    def render_prometheus_metrics(self) -> str:
        stats = self.get_stats()
        invalidations_by_reason = stats["invalidations_by_reason"]
        lines = [
            "# HELP aial_semantic_query_cache_hits_total Total semantic query cache hits.",
            "# TYPE aial_semantic_query_cache_hits_total counter",
            f"aial_semantic_query_cache_hits_total {stats['hits']}",
            "# HELP aial_semantic_query_cache_misses_total Total semantic query cache misses.",
            "# TYPE aial_semantic_query_cache_misses_total counter",
            f"aial_semantic_query_cache_misses_total {stats['misses']}",
            "# HELP aial_semantic_query_cache_force_refresh_total Total force refresh requests.",
            "# TYPE aial_semantic_query_cache_force_refresh_total counter",
            f"aial_semantic_query_cache_force_refresh_total {stats['force_refreshes']}",
            "# HELP aial_semantic_query_cache_invalidations_total Total invalidated semantic cache entries by reason.",
            "# TYPE aial_semantic_query_cache_invalidations_total counter",
            f"aial_semantic_query_cache_invalidations_total {stats['invalidations_total']}",
            "# HELP aial_semantic_query_cache_invalidations_total_by_reason Total invalidated semantic cache entries partitioned by reason.",
            "# TYPE aial_semantic_query_cache_invalidations_total_by_reason counter",
            "# HELP aial_semantic_query_cache_hit_rate Semantic query cache hit rate.",
            "# TYPE aial_semantic_query_cache_hit_rate gauge",
            f"aial_semantic_query_cache_hit_rate {stats['hit_rate']}",
        ]
        if isinstance(invalidations_by_reason, dict):
            for reason, value in sorted(invalidations_by_reason.items()):
                lines.append(
                    f'aial_semantic_query_cache_invalidations_total_by_reason{{reason="{reason}"}} {value}'
                )
        return "\n".join(lines) + "\n"


def _build_redis_client(redis_url: str = DEFAULT_REDIS_URL) -> Redis:
    client = Redis.from_url(redis_url, decode_responses=True)
    client.ping()
    return client


@lru_cache(maxsize=1)
def get_query_result_cache() -> QueryResultCache:
    if _CACHE_OVERRIDE is not None:
        return _CACHE_OVERRIDE
    try:
        return QueryResultCache(_build_redis_client())
    except Exception as exc:  # pragma: no cover - depends on runtime Redis
        logger.warning("Semantic query cache falling back to in-memory store: %s", exc)
        return QueryResultCache(InMemoryRedis())


def reset_query_result_cache(redis_client: Any | None = None) -> QueryResultCache:
    global _CACHE_OVERRIDE
    get_query_result_cache.cache_clear()
    _CACHE_OVERRIDE = QueryResultCache(redis_client) if redis_client is not None else None
    return get_query_result_cache()
