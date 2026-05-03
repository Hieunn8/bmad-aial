from __future__ import annotations

import fakeredis

from orchestration.cache.query_result_cache import (
    CachedQueryResult,
    QueryCacheContext,
    QueryResultCache,
    normalize_query_intent,
)


def _context(*, query: str, user_id: str = "user-1") -> QueryCacheContext:
    return QueryCacheContext(
        query=query,
        normalized_intent=normalize_query_intent(query),
        owner_user_id=user_id,
        department_id="sales",
        role_scope="user",
        semantic_layer_version="v1",
        data_freshness_class="daily",
    )


class TestQueryResultCache:
    def test_semantic_lookup_matches_paraphrased_query_in_same_scope(self) -> None:
        cache = QueryResultCache(fakeredis.FakeRedis(decode_responses=True))
        source = _context(query="Doanh thu Q1 2026 theo chi nhánh?")
        cache.store(
            CachedQueryResult.build(
                context=source,
                answer="cached revenue answer",
                rows=[{"branch": "HCM", "revenue": 100}],
                generated_sql="SELECT revenue FROM sales",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        result = cache.find_best_match(_context(query="Cho tôi xem doanh thu Q1 2026 chia theo chi nhánh?"))

        assert result is not None
        assert result.similarity >= 0.85
        assert result.entry.answer == "cached revenue answer"

    def test_cache_ttl_uses_five_minute_policy(self) -> None:
        redis = fakeredis.FakeRedis(decode_responses=True)
        cache = QueryResultCache(redis)
        context = _context(query="Doanh thu tháng 3")
        entry_key = cache.store(
            CachedQueryResult.build(
                context=context,
                answer="cached",
                rows=[],
                generated_sql="SELECT 1",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        ttl = redis.ttl(entry_key)

        assert ttl > 0
        assert ttl <= 300

    def test_invalidate_user_entries_removes_all_owned_cache_keys(self) -> None:
        redis = fakeredis.FakeRedis(decode_responses=True)
        cache = QueryResultCache(redis)
        cache.store(
            CachedQueryResult.build(
                context=_context(query="Doanh thu tháng 3", user_id="user-a"),
                answer="a",
                rows=[],
                generated_sql="SELECT 1",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )
        cache.store(
            CachedQueryResult.build(
                context=_context(query="Doanh thu tháng 4", user_id="user-a"),
                answer="b",
                rows=[],
                generated_sql="SELECT 2",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        deleted = cache.invalidate_user_entries("user-a")

        assert deleted == 2
        assert cache.find_best_match(_context(query="Doanh thu tháng 3", user_id="user-a")) is None

    def test_render_prometheus_metrics_exposes_hit_miss_and_invalidation_counters(self) -> None:
        cache = QueryResultCache(fakeredis.FakeRedis(decode_responses=True))
        context = _context(query="Doanh thu Q1 2026 theo chi nhánh?")
        cache.store(
            CachedQueryResult.build(
                context=context,
                answer="cached revenue answer",
                rows=[{"branch": "HCM", "revenue": 100}],
                generated_sql="SELECT revenue FROM sales",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )
        cache.find_best_match(_context(query="Cho tôi xem doanh thu Q1 2026 chia theo chi nhánh?"))
        cache.record_force_refresh()
        cache.invalidate_query(context, reason="force_refresh")

        metrics = cache.render_prometheus_metrics()

        assert "aial_semantic_query_cache_hits_total 1.0" in metrics
        assert "aial_semantic_query_cache_misses_total 0.0" in metrics
        assert "aial_semantic_query_cache_force_refresh_total 1.0" in metrics
        assert 'aial_semantic_query_cache_invalidations_total_by_reason{reason="force_refresh"} 1' in metrics
