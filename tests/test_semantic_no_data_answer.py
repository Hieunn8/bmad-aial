from __future__ import annotations

from orchestration.routes.query import _build_semantic_no_data_answer, _has_meaningful_sql_values


def test_semantic_no_data_answer_explains_empty_period_not_mapping_failure() -> None:
    answer = _build_semantic_no_data_answer(
        semantic_context=[{"term": "doanh thu thuần", "source": {"data_source": "oracle-free-system"}}],
        generated_sql=(
            "SELECT SUM(NET_REVENUE) AS METRIC_VALUE FROM SYSTEM.AIAL_SALES_DAILY_V "
            "WHERE PERIOD_DATE >= DATE '2026-05-01' AND PERIOD_DATE < DATE '2026-06-01'"
        ),
        data_source="oracle-free-system",
    )

    assert answer is not None
    assert "doanh thu thuần" in answer
    assert "2026-05-01" in answer
    assert "không phải lỗi map semantic" in answer


def test_null_aggregate_row_is_treated_as_no_data() -> None:
    assert not _has_meaningful_sql_values([{"METRIC_VALUE": None}])
    assert _has_meaningful_sql_values([{"METRIC_VALUE": 275150250}])
