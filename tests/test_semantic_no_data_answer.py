from __future__ import annotations

from orchestration.routes.query import _build_semantic_no_data_answer, _has_meaningful_sql_values

_CTX_PLAIN = [{"term": "doanh thu thuần", "source": {"data_source": "oracle-free-system"}}]

_CTX_WITH_PLAN = [
    {
        "term": "doanh thu thuần",
        "source": {"data_source": "oracle-free-system"},
        "_semantic_plan": {
            "time_filter": {"kind": "recent_days", "start": "2026-04-30", "end": "2026-05-07"},
            "entity_filters": {"REGION_CODE": "HCM"},
        },
    }
]


def test_reads_time_range_from_semantic_plan() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=_CTX_WITH_PLAN,
        generated_sql="SELECT SUM(NET_REVENUE) AS METRIC_VALUE FROM SYSTEM.AIAL_SALES_DAILY_V WHERE 1=1",
        data_source="oracle-free-system",
    )
    assert answer is not None
    assert "2026-04-30" in answer
    assert "2026-05-07" in answer


def test_shows_entity_filter_in_message() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=_CTX_WITH_PLAN,
        generated_sql="",
        data_source="oracle-free-system",
    )
    assert answer is not None
    assert "HCM" in answer


def test_shows_max_available_date_hint() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=_CTX_WITH_PLAN,
        generated_sql="",
        data_source="oracle-free-system",
        max_available_date="2026-01-01 đến 2026-03-31",
    )
    assert answer is not None
    assert "2026-01-01 đến 2026-03-31" in answer
    assert "dữ liệu hiện có trong kho" in answer
    assert "không tự đổi sang kỳ khác" in answer


def test_suggestion_does_not_repeat_failed_time_range() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=_CTX_WITH_PLAN,
        generated_sql="",
        data_source="oracle-free-system",
    )
    assert answer is not None
    assert "7 ngày gần đây" not in answer


def test_fallback_to_sql_parsing_when_no_plan() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=_CTX_PLAIN,
        generated_sql=(
            "SELECT SUM(NET_REVENUE) AS METRIC_VALUE FROM SYSTEM.AIAL_SALES_DAILY_V "
            "WHERE PERIOD_DATE >= DATE '2026-05-01' AND PERIOD_DATE < DATE '2026-06-01'"
        ),
        data_source="oracle-free-system",
    )
    assert answer is not None
    assert "2026-05-01" in answer
    assert "oracle-free-system" in answer
    assert "Truy vấn semantic đã chạy" in answer
    assert "SUM(NET_REVENUE)" in answer


def test_null_aggregate_row_is_treated_as_no_data() -> None:
    assert not _has_meaningful_sql_values([{"METRIC_VALUE": None}])
    assert _has_meaningful_sql_values([{"METRIC_VALUE": 275150250}])
