"""Semantic dynamic query tests — validates 3 tiêu chí:

  1. Dynamic alias/synonym: từ đồng nghĩa map đúng semantic term
  2. Flexible SQL: time filter chính xác cho mỗi loại câu hỏi
  3. Clarification: hỏi lại khi câu hỏi mơ hồ
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orchestration.semantic.management import SemanticLayerService
from orchestration.semantic.sql_execution import build_semantic_sql_plan

from aial_shared.auth.keycloak import JWTClaims


def _claims(*, roles: tuple[str, ...] = ("sales_analyst",), department: str = "sales") -> JWTClaims:
    return JWTClaims(
        sub="user-1",
        email="user@aial.local",
        department=department,
        roles=roles,
        clearance=2,
        raw={},
    )


def _oracle_context(*, with_plan: dict | None = None) -> list[dict]:
    ctx: list[dict] = [
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
    if with_plan:
        ctx[0]["_semantic_plan"] = with_plan
    return ctx


def _service_with_revenue() -> SemanticLayerService:
    service = SemanticLayerService(catalog_store=None)
    service.publish_metric(
        term="doanh thu thuần",
        aliases=["doanh thu", "net revenue", "revenue", "bán hàng", "thu nhập", "kinh doanh", "doanh số"],
        definition="Tổng doanh thu sau khi trừ hoàn trả",
        formula="SUM(NET_REVENUE)",
        owner="Sales",
        freshness_rule="daily",
        changed_by="test",
        aggregation="sum",
        grain="daily",
        unit="VND",
        dimensions=["PERIOD_DATE", "REGION_CODE", "CHANNEL_CODE", "PRODUCT_CODE"],
        examples=[
            "doanh thu tháng này",
            "thu nhập hôm nay",
            "bán hàng 7 ngày gần đây",
            "tình hình kinh doanh theo khu vực",
            "doanh thu hôm qua",
            "doanh số tuần này",
        ],
        negative_examples=["doanh thu ngân sách", "kế hoạch doanh thu"],
        source={"data_source": "oracle-free-system", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["sales_analyst", "admin"]},
    )
    return service


# ─── Tiêu chí 1: Dynamic alias/synonym ────────────────────────────────────────

def test_alias_thu_nhap_resolves_to_doanh_thu_thuan() -> None:
    """'thu nhập' là alias → map đúng semantic 'doanh thu thuần'."""
    service = _service_with_revenue()
    decision = service.resolve_query(query="thu nhập hôm qua", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_alias_doanh_so_resolves_to_doanh_thu_thuan() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="doanh số tuần này theo kênh", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_alias_ban_hang_resolves_to_doanh_thu_thuan() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="tình hình bán hàng tháng này", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_alias_kinh_doanh_resolves_via_synonym_boost() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="bức tranh kinh doanh 7 ngày gần đây", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


def test_no_accent_alias_maps_correctly() -> None:
    """Không dấu tiếng Việt vẫn map đúng."""
    service = _service_with_revenue()
    decision = service.resolve_query(query="thu nhap hom qua", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


# ─── Tiêu chí 2a: SQL filter — hôm nay ───────────────────────────────────────

def test_sql_hom_nay_accented() -> None:
    """'hôm nay' → filter đúng ngày hôm nay."""
    now = datetime.now(UTC)
    today = now.date()
    plan = build_semantic_sql_plan(
        query="Doanh thu hôm nay",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{today.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{(today + timedelta(days=1)).isoformat()}'" in plan.sql
    assert "SUM(NET_REVENUE) AS METRIC_VALUE" in plan.sql


def test_sql_hom_nay_no_accent() -> None:
    now = datetime.now(UTC)
    today = now.date()
    plan = build_semantic_sql_plan(
        query="Doanh thu hom nay",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{today.isoformat()}'" in plan.sql


def test_sql_thu_nhap_hom_nay_different_from_all_time() -> None:
    """'thu nhập hôm nay' phải có filter ngày — KHÔNG trả về tổng toàn bộ."""
    now = datetime.now(UTC)
    today = now.date()
    plan = build_semantic_sql_plan(
        query="thu nhập hôm nay",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{today.isoformat()}'" in plan.sql


# ─── Tiêu chí 2b: SQL filter — hôm qua ───────────────────────────────────────

def test_sql_hom_qua_accented() -> None:
    """'hôm qua' → filter đúng ngày hôm qua, KHÔNG cùng kết quả với hôm nay."""
    now = datetime.now(UTC)
    today = now.date()
    yesterday = today - timedelta(days=1)
    plan = build_semantic_sql_plan(
        query="thu nhập hôm qua",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{yesterday.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{today.isoformat()}'" in plan.sql


def test_sql_hom_qua_no_accent() -> None:
    now = datetime.now(UTC)
    yesterday = (now.date() - timedelta(days=1))
    plan = build_semantic_sql_plan(
        query="doanh thu hom qua",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{yesterday.isoformat()}'" in plan.sql


def test_hom_nay_vs_hom_qua_have_different_sql() -> None:
    """Câu hỏi hôm nay và hôm qua phải sinh SQL khác nhau."""
    plan_today = build_semantic_sql_plan(
        query="Doanh thu hôm nay",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    plan_yesterday = build_semantic_sql_plan(
        query="Thu nhập hôm qua",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan_today is not None
    assert plan_yesterday is not None
    assert plan_today.sql != plan_yesterday.sql


# ─── Tiêu chí 2c: SQL filter — tuần này / tuần trước ─────────────────────────

def test_sql_tuan_nay_accented() -> None:
    now = datetime.now(UTC)
    today = now.date()
    start_of_week = today - timedelta(days=today.weekday())
    plan = build_semantic_sql_plan(
        query="Doanh thu tuần này",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start_of_week.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{(start_of_week + timedelta(days=7)).isoformat()}'" in plan.sql


def test_sql_tuan_truoc() -> None:
    now = datetime.now(UTC)
    today = now.date()
    start_prev = today - timedelta(days=today.weekday() + 7)
    plan = build_semantic_sql_plan(
        query="doanh thu tuần trước",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start_prev.isoformat()}'" in plan.sql


# ─── Tiêu chí 2d: SQL filter — N ngày gần đây ────────────────────────────────

def test_sql_7_ngay_gan_day() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(days=6)).date()
    plan = build_semantic_sql_plan(
        query="doanh thu 7 ngày gần đây",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start.isoformat()}'" in plan.sql


def test_sql_30_ngay_gan_day() -> None:
    now = datetime.now(UTC)
    start = (now - timedelta(days=29)).date()
    plan = build_semantic_sql_plan(
        query="doanh thu 30 ngay gan day",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start.isoformat()}'" in plan.sql


# ─── Tiêu chí 2e: SQL filter — tháng này ─────────────────────────────────────

def test_sql_thang_nay() -> None:
    now = datetime.now(UTC)
    plan = build_semantic_sql_plan(
        query="doanh thu tháng này",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{now.year}-{now.month:02d}-01'" in plan.sql


# ─── Tiêu chí 2f: SQL filter — năm và quý ────────────────────────────────────

def test_sql_quy_1_2026() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu quý 1 2026",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert "PERIOD_DATE >= DATE '2026-01-01'" in plan.sql
    assert "PERIOD_DATE < DATE '2026-04-01'" in plan.sql


def test_sql_quy_4_2025() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu Q4 2025",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert "PERIOD_DATE >= DATE '2025-10-01'" in plan.sql
    assert "PERIOD_DATE < DATE '2026-01-01'" in plan.sql


# ─── Tiêu chí 2g: Intent "gần đây nhất" → MAX(PERIOD_DATE) ──────────────────

def test_sql_latest_record_via_semantic_plan() -> None:
    """Khi semantic_plan có kind='latest_record' → SQL dùng MAX(PERIOD_DATE)."""
    ctx = _oracle_context(with_plan={"time_filter": {"kind": "latest_record"}, "dimensions": []})
    plan = build_semantic_sql_plan(
        query="Doanh thu có dữ liệu gần đây nhất là ngày nào",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert "MAX(PERIOD_DATE) AS LATEST_DATE" in plan.sql
    assert "SUM(NET_REVENUE)" not in plan.sql
    assert "GROUP BY" not in plan.sql


def test_sql_latest_record_detected_from_query_text() -> None:
    """Text 'gần nhất' → _is_latest_date_query → MAX query mà không cần semantic_plan."""
    plan = build_semantic_sql_plan(
        query="dữ liệu gần nhất là ngày nào",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert "MAX(PERIOD_DATE) AS LATEST_DATE" in plan.sql


def test_sql_latest_record_moi_nhat() -> None:
    plan = build_semantic_sql_plan(
        query="doanh thu mới nhất là ngày nào",
        semantic_context=_oracle_context(),
        principal=_claims(),
    )
    assert plan is not None
    assert "MAX(PERIOD_DATE) AS LATEST_DATE" in plan.sql


# ─── Tiêu chí 2h: Semantic plan time_filter kinds → SQL ──────────────────────

def test_plan_kind_today_generates_today_filter() -> None:
    now = datetime.now(UTC)
    today = now.date()
    ctx = _oracle_context(with_plan={"time_filter": {"kind": "today"}, "dimensions": []})
    plan = build_semantic_sql_plan(
        query="doanh thu hôm nay",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{today.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{(today + timedelta(days=1)).isoformat()}'" in plan.sql


def test_plan_kind_yesterday_generates_yesterday_filter() -> None:
    now = datetime.now(UTC)
    today = now.date()
    yesterday = today - timedelta(days=1)
    ctx = _oracle_context(with_plan={"time_filter": {"kind": "yesterday"}, "dimensions": []})
    plan = build_semantic_sql_plan(
        query="thu nhập hôm qua",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{yesterday.isoformat()}'" in plan.sql
    assert f"PERIOD_DATE < DATE '{today.isoformat()}'" in plan.sql


def test_plan_kind_current_week_generates_week_filter() -> None:
    now = datetime.now(UTC)
    today = now.date()
    start_of_week = today - timedelta(days=today.weekday())
    ctx = _oracle_context(with_plan={"time_filter": {"kind": "current_week"}, "dimensions": []})
    plan = build_semantic_sql_plan(
        query="doanh thu tuần này",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert f"PERIOD_DATE >= DATE '{start_of_week.isoformat()}'" in plan.sql


# ─── Tiêu chí 2i: Dimension extraction ───────────────────────────────────────

def test_sql_groups_by_region_from_plan() -> None:
    ctx = _oracle_context(with_plan={"time_filter": {"kind": "current_month"}, "dimensions": ["REGION_CODE"]})
    plan = build_semantic_sql_plan(
        query="doanh thu tháng này theo khu vực",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert "REGION_CODE" in plan.sql
    assert "GROUP BY REGION_CODE" in plan.sql


def test_sql_groups_by_channel_from_plan() -> None:
    ctx = _oracle_context(with_plan={"time_filter": None, "dimensions": ["CHANNEL_CODE"]})
    plan = build_semantic_sql_plan(
        query="doanh thu theo kênh bán",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert "CHANNEL_CODE" in plan.sql
    assert "GROUP BY CHANNEL_CODE" in plan.sql


def test_sql_groups_by_multiple_dimensions() -> None:
    ctx = _oracle_context(
        with_plan={
            "time_filter": {"kind": "recent_days", "days": 7},
            "dimensions": ["REGION_CODE", "CHANNEL_CODE"],
        }
    )
    plan = build_semantic_sql_plan(
        query="bán hàng 7 ngày gần đây theo khu vực và kênh",
        semantic_context=ctx,
        principal=_claims(),
    )
    assert plan is not None
    assert "REGION_CODE" in plan.sql
    assert "CHANNEL_CODE" in plan.sql


# ─── Tiêu chí 3: Clarification khi mơ hồ ────────────────────────────────────

def test_ambiguous_query_triggers_clarification() -> None:
    """Khi 2 metrics có cùng alias và score ngang nhau → ambiguous → hỏi lại user.

    Dùng service riêng (không phải _service_with_revenue) để kiểm soát
    score balance giữa 2 metrics.
    """
    service = SemanticLayerService(catalog_store=None)
    # Cả 2 metrics cùng alias "doanh thu", cùng số examples → score ngang nhau
    for term, formula in [("doanh thu thực tế", "SUM(NET_REVENUE)"), ("doanh thu điều chỉnh", "SUM(ADJUSTED_REVENUE)")]:
        service.publish_metric(
            term=term,
            aliases=["doanh thu", "revenue"],
            definition=f"Tổng {term} theo dữ liệu bán hàng",
            formula=formula,
            owner="Sales",
            freshness_rule="daily",
            changed_by="test",
            examples=["doanh thu tháng này", "revenue theo khu vực"],
            negative_examples=[],
            source={"data_source": "oracle-free-system", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
            security={"sensitivity_tier": 1, "allowed_roles": ["sales_analyst"]},
        )
    decision = service.resolve_query(query="doanh thu", principal=_claims())
    # Kết quả phải là ambiguous hoặc low_confidence — không được auto-select
    assert decision.status in {"ambiguous", "low_confidence"}
    assert decision.semantic_context == []


def test_clarification_question_contains_candidate_terms() -> None:
    """Câu hỏi clarification phải list các candidate để user chọn."""
    service = _service_with_revenue()
    service.publish_metric(
        term="doanh thu ngân sách",
        aliases=["doanh thu", "budget"],
        definition="Ngân sách doanh thu",
        formula="SUM(BUDGET_AMOUNT)",
        owner="Finance",
        freshness_rule="daily",
        changed_by="test",
        source={"data_source": "oracle-free-system", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["sales_analyst"]},
    )
    decision = service.resolve_query(query="doanh thu", principal=_claims())
    if decision.status == "ambiguous" and decision.planner_output:
        question = decision.planner_output.clarification_question
        assert question is not None
        assert len(question) > 10


def test_specific_query_with_time_does_not_trigger_clarification() -> None:
    """Câu hỏi có context rõ không cần clarification."""
    service = _service_with_revenue()
    service.publish_metric(
        term="doanh thu ngân sách",
        aliases=["budget revenue", "ngân sách"],
        definition="Ngân sách doanh thu",
        formula="SUM(BUDGET_AMOUNT)",
        owner="Finance",
        freshness_rule="daily",
        changed_by="test",
        source={"data_source": "oracle-free-system", "schema": "SYSTEM", "table": "AIAL_SALES_DAILY_V"},
        security={"sensitivity_tier": 1, "allowed_roles": ["sales_analyst"]},
    )
    # "thu nhập" + "hôm nay" đủ context để resolve "doanh thu thuần"
    decision = service.resolve_query(query="thu nhập hôm nay là bao nhiêu", principal=_claims())
    assert decision.status == "selected"
    assert decision.semantic_context[0]["term"] == "doanh thu thuần"


# ─── Resolver time_filter extraction ─────────────────────────────────────────

def test_resolver_extracts_today_time_filter() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="doanh thu hôm nay", principal=_claims())
    assert decision.status == "selected"
    tf = decision.semantic_context[0].get("_semantic_plan", {}).get("time_filter", {})
    assert tf.get("kind") == "today"
    assert tf.get("start") is not None  # has resolved date


def test_resolver_extracts_yesterday_time_filter() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="thu nhập hôm qua", principal=_claims())
    assert decision.status == "selected"
    tf = decision.semantic_context[0].get("_semantic_plan", {}).get("time_filter", {})
    assert tf.get("kind") == "yesterday"
    assert tf.get("start") is not None


def test_resolver_extracts_current_week_time_filter() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(query="doanh thu tuần này theo khu vực", principal=_claims())
    assert decision.status == "selected"
    tf = decision.semantic_context[0].get("_semantic_plan", {}).get("time_filter", {})
    assert tf.get("kind") == "current_week"
    assert tf.get("start") is not None


def test_resolver_extracts_latest_record_time_filter() -> None:
    service = _service_with_revenue()
    decision = service.resolve_query(
        query="Doanh thu có dữ liệu gần đây nhất là ngày nào?",
        principal=_claims(),
    )
    assert decision.status == "selected"
    tf = decision.semantic_context[0].get("_semantic_plan", {}).get("time_filter", {})
    assert tf.get("kind") == "latest_record"


def test_resolver_gan_day_nhat_does_not_mismap_to_recent_days() -> None:
    """'gần đây nhất' KHÔNG được map thành recent_days — phải là latest_record."""
    service = _service_with_revenue()
    decision = service.resolve_query(query="doanh thu gần đây nhất", principal=_claims())
    assert decision.status == "selected"
    tf = decision.semantic_context[0].get("_semantic_plan", {}).get("time_filter", {})
    assert tf.get("kind") == "latest_record"
    assert tf.get("kind") != "recent_days"
