from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from orchestration.semantic.cube_model import generate_cube_model_files
from orchestration.semantic.cube_runtime import CubeSemanticRuntimeClient, build_cube_query

from aial_shared.auth.keycloak import JWTClaims


def _metric() -> dict[str, object]:
    return {
        "term": "doanh thu thuần",
        "definition": "Tổng doanh thu sau hoàn trả",
        "formula": "SUM(NET_REVENUE)",
        "unit": "VND",
        "dimensions": ["PERIOD_DATE", "REGION_CODE", "CHANNEL_CODE"],
        "source": {
            "data_source": "oracle-free-system",
            "schema": "SYSTEM",
            "table": "AIAL_SALES_DAILY_V",
        },
        "_semantic_plan": {
            "intent": "metric_breakdown",
            "time_filter": {"kind": "month", "start": "2026-05-01", "end": "2026-06-01"},
            "dimensions": ["REGION_CODE"],
            "entity_filters": {"CHANNEL_CODE": "ONLINE"},
        },
    }


def _claims() -> JWTClaims:
    return JWTClaims(
        sub="user-1",
        email="user@aial.local",
        department="sales",
        roles=("sales_analyst",),
        clearance=1,
        raw={},
    )


def test_generates_cube_yaml_from_legacy_semantic_catalog(tmp_path: Path) -> None:
    result = generate_cube_model_files([_metric()], model_dir=tmp_path)

    assert result.ok
    assert result.metric_count == 1
    generated = (tmp_path / "sales_daily.yml").read_text(encoding="utf-8")
    assert "name: sales_daily" in generated
    assert "sql_table: SYSTEM.AIAL_SALES_DAILY_V" in generated
    assert "name: net_revenue" in generated
    assert "sql: NET_REVENUE" in generated
    assert "name: period_date" in generated
    assert "primary_key: true" in generated


def test_builds_cube_query_from_semantic_plan() -> None:
    query = build_cube_query(metric=_metric(), row_limit=25)

    assert query["measures"] == ["sales_daily.net_revenue"]
    assert query["dimensions"] == ["sales_daily.region_code"]
    assert query["filters"] == [
        {"member": "sales_daily.channel_code", "operator": "equals", "values": ["ONLINE"]}
    ]
    assert query["timeDimensions"] == [
        {
            "dimension": "sales_daily.period_date",
            "dateRange": ["2026-05-01", "2026-06-01"],
            "granularity": "day",
        }
    ]
    assert query["limit"] == 25


def test_cube_client_returns_warning_when_not_configured() -> None:
    execution = CubeSemanticRuntimeClient(api_url="", api_secret="").execute(
        query="doanh thu",
        semantic_context=[_metric()],
        principal=_claims(),
    )

    assert execution.rows == []
    assert execution.runtime_query is not None
    assert execution.warning
    assert execution.provenance[0]["runtime"] == "cube"


def test_cube_client_extracts_rows_from_rest_response(monkeypatch) -> None:
    response = MagicMock()
    response.json.return_value = {"data": [{"sales_daily.net_revenue": 1000}]}
    response.raise_for_status.return_value = None
    post = MagicMock(return_value=response)
    monkeypatch.setattr("orchestration.semantic.cube_runtime.httpx.post", post)

    execution = CubeSemanticRuntimeClient(
        api_url="http://cube.local/cubejs-api/v1",
        api_secret="secret",
    ).execute(
        query="doanh thu",
        semantic_context=[_metric()],
        principal=_claims(),
        row_limit=10,
    )

    assert execution.rows == [{"sales_daily.net_revenue": 1000}]
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["query"]["limit"] == 10
