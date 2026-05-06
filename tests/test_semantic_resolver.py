"""Vietnamese regression tests for production-shaped semantic resolution."""

from __future__ import annotations

from orchestration.semantic.management import SemanticLayerService

from aial_shared.auth.keycloak import JWTClaims


def _claims(*, roles: tuple[str, ...] = ("finance_analyst",), clearance: int = 3) -> JWTClaims:
    return JWTClaims(
        sub="user-1",
        email="user@aial.local",
        department="sales",
        roles=roles,
        clearance=clearance,
        raw={},
    )


def _publish_revenue(service: SemanticLayerService) -> None:
    service.publish_metric(
        term="doanh thu thuần",
        aliases=["doanh thu", "net revenue", "revenue", "bán hàng", "kinh doanh", "thu nhập"],
        definition="Tổng doanh thu sau khi trừ hoàn trả và giảm trừ thương mại",
        formula="SUM(NET_REVENUE)",
        owner="Finance",
        freshness_rule="daily",
        changed_by="test",
        aggregation="sum",
        grain="daily",
        unit="VND",
        dimensions=["thời gian", "khu vực", "kênh bán"],
        examples=[
            "tình hình kinh doanh theo khu vực",
            "bán hàng mấy ngày nay theo vùng",
            "doanh số 7 ngày gần đây",
            "thu nhập tuần này",
        ],
        negative_examples=["doanh thu ngân sách", "kế hoạch doanh thu"],
        source={"data_source": "oracle-free", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["finance_analyst"]},
    )


def test_resolves_no_accent_vietnamese_query() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(query="Doanh thu thang nay", principal=_claims())

    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"
    assert decision.confidence >= 0.62


def test_resolves_synonym_without_exact_metric_keyword() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(query="tình hình bán hàng quý 1 theo khu vực", principal=_claims())

    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_resolves_income_as_revenue_synonym_in_sales_context() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(query="thu nhập tuần này", principal=_claims())

    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_resolves_long_business_sentence() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(
        query=(
            "Anh chị cho tôi xem bức tranh kinh doanh tháng này, nếu được thì "
            "tách theo khu vực để biết vùng nào đang đóng góp chính"
        ),
        principal=_claims(),
    )

    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"
    assert decision.semantic_context[0]["_semantic_plan"]["intent"] == "metric_breakdown"
    assert "REGION_CODE" in decision.semantic_context[0]["_semantic_plan"]["dimensions"]


def test_structured_planner_maps_long_synonym_query_to_time_and_dimension() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(
        query="Cho tôi xem bức tranh kinh doanh mấy ngày nay theo vùng miền",
        principal=_claims(),
    )

    assert decision.status == "selected"
    plan = decision.semantic_context[0]["_semantic_plan"]
    assert plan["selected_term"] == "doanh thu thuần"
    tf = plan["time_filter"]
    assert tf["kind"] == "recent_days"
    assert tf.get("start") is not None  # time_parser now resolves dates
    assert "REGION_CODE" in plan["dimensions"]


def test_ambiguous_query_is_not_auto_selected() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)
    service.publish_metric(
        term="doanh thu kế hoạch",
        aliases=["doanh thu", "kế hoạch doanh thu", "revenue target"],
        definition="Mục tiêu doanh thu đã phê duyệt cho kỳ kế hoạch",
        formula="SUM(REVENUE_TARGET)",
        owner="Finance",
        freshness_rule="daily",
        changed_by="test",
        source={"data_source": "oracle-free", "schema": "SYSTEM", "table": "AIAL_SALES_PLAN_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["finance_analyst"]},
    )

    decision = service.resolve_query(query="doanh thu", principal=_claims())

    assert decision.status == "ambiguous"
    assert decision.semantic_context == []
    assert len(decision.candidates) >= 2


def test_total_revenue_prefers_net_revenue_over_budget_revenue() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)
    service.publish_metric(
        term="doanh thu ngân sách",
        aliases=["budget revenue"],
        definition="Tổng ngân sách doanh thu đã lập kế hoạch",
        formula="SUM(BUDGET_AMOUNT)",
        owner="Finance",
        freshness_rule="daily",
        changed_by="test",
        source={"data_source": "oracle-free", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["finance_analyst"]},
    )

    decision = service.resolve_query(query="tất cả doanh thu", principal=_claims())

    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_role_security_filter_blocks_unauthorized_metric() -> None:
    service = SemanticLayerService(catalog_store=None)
    _publish_revenue(service)

    decision = service.resolve_query(query="doanh thu tháng này", principal=_claims(roles=("user",)))

    assert decision.status == "no_match"
    assert decision.semantic_context == []
    assert decision.candidates[0].filtered_reason == "role_not_allowed"
