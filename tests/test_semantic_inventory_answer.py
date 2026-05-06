from __future__ import annotations

from unittest.mock import patch

from orchestration.routes.query import _build_data_inventory_answer, _build_semantic_clarification_answer
from orchestration.semantic.resolver import SemanticPlannerOutput, SemanticResolveCandidate, SemanticResolveDecision

from aial_shared.auth.keycloak import JWTClaims


def test_data_inventory_answer_hides_technical_source_and_aliases() -> None:
    principal = JWTClaims(
        sub="u",
        email="u@aial.local",
        department="sales",
        roles=("sales_analyst",),
        clearance=1,
        raw={},
    )
    metric = {
        "term": "doanh thu thuần",
        "unit": "VND",
        "aliases": ["doanh thu", "net revenue"],
        "source": {"data_source": "oracle-free-system"},
        "examples": ["doanh thu tháng này thế nào"],
    }

    with (
        patch("orchestration.routes.query.get_user_role_management_service") as roles,
        patch("orchestration.routes.query.get_semantic_layer_service") as semantic,
    ):
        roles.return_value.allowed_metrics_for_principal.return_value = set()
        semantic.return_value.list_metrics.return_value = [metric]

        answer = _build_data_inventory_answer(principal)

    assert "doanh thu thuần" in answer
    assert "oracle-free-system" not in answer
    assert "net revenue" not in answer
    assert "doanh thu tháng này thế nào" in answer


def test_semantic_clarification_guides_user_to_standard_semantics() -> None:
    candidate = SemanticResolveCandidate(
        metric={
            "term": "doanh thu thuần",
            "examples": ["doanh thu tháng này thế nào"],
        },
        lexical_score=0.2,
        vector_score=0.4,
        merged_score=0.3,
        rerank_score=0.5,
    )
    decision = SemanticResolveDecision(
        status="low_confidence",
        semantic_context=[],
        selected=candidate,
        candidates=[candidate],
        normalized_query="thu nhap tuan nay",
        confidence=0.5,
        reasons=["confidence_below_gate"],
        planner_output=SemanticPlannerOutput(
            status="selected",
            selected_term="doanh thu thuần",
            intent="metric_value",
            time_filter={"kind": "current_week"},
            dimensions=[],
            confidence=0.5,
            needs_clarification=False,
            clarification_question=None,
            rationale="test",
        ),
    )

    answer = _build_semantic_clarification_answer(decision)

    assert answer is not None
    assert "doanh thu thuần" in answer
    assert "doanh thu tháng này thế nào" in answer
