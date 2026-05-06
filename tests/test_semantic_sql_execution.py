"""Tests for semantic SQL planning against the Oracle Free sample catalog."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orchestration.semantic.sql_execution import build_semantic_sql_plan, execute_semantic_sql

from aial_shared.auth.keycloak import JWTClaims


def _claims(*, roles: tuple[str, ...] = ("sales_analyst",), department: str = "sales") -> JWTClaims:
    return JWTClaims(
        sub="user-1",
        email="user@aial.local",
        department=department,
        roles=roles,
        clearance=1,
        raw={},
    )


def _semantic_context() -> list[dict[str, object]]:
    return [
        {
            "term": "doanh thu thuần",
            "formula": "SUM(NET_REVENUE)",
            "freshness_rule": "daily",
            "source": {
                "data_source": "oracle-free-system",
                "schema": "SYSTEM",
                "table": "AIAL_SALES_DAILY_V",
            },
        }
    ]


def test_builds_current_month_filter_for_unaccented_vietnamese_query() -> None:
    plan = build_semantic_sql_plan(
        query="Doanh thu thang nay",
        semantic_context=_semantic_context(),
        principal=_claims(),
    )

    now = datetime.now(UTC)
    next_month_year = now.year + 1 if now.month == 12 else now.year
    next_month = 1 if now.month == 12 else now.month + 1

    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{now.year}-{now.month:02d}-01'" in plan.sql
    assert f"PERIOD_DATE < DATE '{next_month_year}-{next_month:02d}-01'" in plan.sql


def test_builds_recent_days_filter_for_vietnamese_query() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu 7 ngày gần đây",
        semantic_context=_semantic_context(),
        principal=_claims(),
    )
    now = datetime.now(UTC)
    start = (now - timedelta(days=6)).date()
    end = (now + timedelta(days=1)).date()

    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{end.isoformat()}'" in plan.sql


def test_builds_sql_from_structured_semantic_plan() -> None:
    context = _semantic_context()
    context[0]["_semantic_plan"] = {
        "time_filter": {"kind": "recent_days", "days": 7},
        "dimensions": ["REGION_CODE"],
    }
    plan = build_semantic_sql_plan(
        query="bức tranh kinh doanh mấy ngày nay theo vùng",
        semantic_context=context,
        principal=_claims(),
    )
    now = datetime.now(UTC)
    start = (now - timedelta(days=6)).date()

    assert plan is not None
    assert "REGION_CODE" in plan.sql
    assert "GROUP BY REGION_CODE" in plan.sql
    assert f"PERIOD_DATE >= DATE '{start.isoformat()}'" in plan.sql


def test_builds_grouped_oracle_sql_from_semantic_source() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu thuan quy 1 2026 theo khu vuc",
        semantic_context=_semantic_context(),
        principal=_claims(),
    )

    assert plan is not None
    assert "SUM(NET_REVENUE) AS METRIC_VALUE" in plan.sql
    assert "FROM SYSTEM.AIAL_SALES_DAILY_V" in plan.sql
    assert "REGION_CODE" in plan.sql
    assert "PERIOD_DATE >= DATE '2026-01-01'" in plan.sql
    assert "PERIOD_DATE < DATE '2026-04-01'" in plan.sql
    assert "DEPARTMENT_SCOPE = :department_scope" in plan.sql
    assert plan.parameters == {"department_scope": "sales"}


def test_admin_semantic_sql_does_not_force_department_scope() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu thuần 2026",
        semantic_context=_semantic_context(),
        principal=_claims(roles=("admin",), department="engineering"),
    )

    assert plan is not None
    assert "DEPARTMENT_SCOPE = :department_scope" not in plan.sql
    assert plan.parameters == {}


def test_execute_returns_warning_when_oracle_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("AIAL_ORACLE_USERNAME", raising=False)
    monkeypatch.delenv("AIAL_ORACLE_PASSWORD", raising=False)
    monkeypatch.delenv("AIAL_ORACLE_DSN", raising=False)

    plan = build_semantic_sql_plan(
        query="doanh thu thuần 2026",
        semantic_context=_semantic_context(),
        principal=_claims(),
    )
    result = execute_semantic_sql(plan)

    assert result.rows == []
    assert result.warning
    assert "Oracle" in result.warning
