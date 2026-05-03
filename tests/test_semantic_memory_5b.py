"""Tests for Epic 5B semantic governance and memory stack."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.memory.long_term import (
    HistoryEntry,
    get_conversation_memory_service,
    reset_conversation_memory_service,
)
from orchestration.semantic.management import (
    get_semantic_layer_service,
    reset_semantic_layer_service,
)


@pytest.fixture(autouse=True)
def reset_services() -> None:
    reset_semantic_layer_service()
    reset_conversation_memory_service()


@pytest.fixture()
def data_owner_claims() -> JWTClaims:
    return JWTClaims(
        sub="owner-1",
        email="owner@aial.local",
        department="finance",
        roles=("data_owner",),
        clearance=3,
        raw={},
    )


@pytest.fixture()
def user_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-1",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={},
    )


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app

    return TestClient(app)


def _auth(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    claims: JWTClaims,
) -> None:
    mock_decode.return_value = {
        "sub": claims.sub,
        "email": claims.email,
        "department": claims.department,
        "roles": list(claims.roles),
        "clearance": claims.clearance,
    }
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


class TestSemanticLayerManagement:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_publish_diff_and_rollback_metric_without_breaking_glossary_api(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        data_owner_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, data_owner_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        before = client.get("/v1/glossary/doanh%20thu%20thu%E1%BA%A7n", headers=headers)
        assert before.status_code == 200
        previous_formula = before.json()["formula"]

        publish_resp = client.post(
            "/v1/admin/semantic-layer/metrics/publish",
            json={
                "term": "doanh thu thuần",
                "definition": "Doanh thu sau điều chỉnh hoàn trả và giảm trừ",
                "formula": "SUM(NET_REVENUE) - SUM(RETURNS)",
                "owner": "Finance",
                "freshness_rule": "daily",
            },
            headers=headers,
        )
        assert publish_resp.status_code == 201
        new_version = publish_resp.json()["version"]
        assert new_version["previous_formula"] == previous_formula

        glossary_resp = client.get("/v1/glossary/doanh%20thu%20thu%E1%BA%A7n", headers=headers)
        assert glossary_resp.status_code == 200
        assert glossary_resp.json()["formula"] == "SUM(NET_REVENUE) - SUM(RETURNS)"

        versions_resp = client.get("/v1/admin/semantic-layer/metrics/doanh thu thuần/versions", headers=headers)
        assert versions_resp.status_code == 200
        versions = versions_resp.json()["versions"]
        assert len(versions) >= 2

        diff_resp = client.get(
            f"/v1/admin/semantic-layer/metrics/doanh thu thuần/diff?from_version_id={versions[0]['version_id']}&to_version_id={new_version['version_id']}",
            headers=headers,
        )
        assert diff_resp.status_code == 200
        assert any(row["kind"] == "added" for row in diff_resp.json()["diff"])

        rollback_resp = client.post(
            "/v1/admin/semantic-layer/metrics/doanh thu thuần/rollback",
            json={"version_id": versions[0]["version_id"], "reason": "restore audited baseline"},
            headers=headers,
        )
        assert rollback_resp.status_code == 201
        assert rollback_resp.json()["version"]["action"] == "rollback"

        glossary_after = client.get("/v1/glossary/doanh%20thu%20thu%E1%BA%A7n", headers=headers)
        assert glossary_after.status_code == 200
        assert glossary_after.json()["formula"] == previous_formula


class TestConversationMemoryRoutes:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_summary_context_history_and_reuse_are_user_scoped(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        user_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, user_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        session_id = str(uuid4())

        summary_resp = client.post(
            "/v1/chat/memory/summaries",
            json={
                "session_id": session_id,
                "sensitivity_level": 1,
                "intent_type": "chat_query",
                "topic": "monthly revenue trend",
                "filter_context": "march filter",
                "summary_text": "User asked about revenue trend and time filter",
            },
            headers=headers,
        )
        assert summary_resp.status_code == 201

        service = get_conversation_memory_service()
        history = service.record_interaction(
            user_id=user_claims.sub,
            department_id=user_claims.department,
            session_id=session_id,
            intent_type="chat_query",
            topic="monthly revenue trend",
            filter_context="march filter",
            key_result_summary="Result summary for revenue trend",
            sensitivity_level=1,
            matched_metrics=["doanh thu thuần"],
        )

        context_resp = client.get("/v1/chat/memory/context?query=monthly%20revenue%20trend", headers=headers)
        assert context_resp.status_code == 200
        assert context_resp.json()["summaries"]
        assert context_resp.json()["token_budget_increase_percent"] <= 20

        search_resp = client.get("/v1/chat/history/search?keyword=revenue", headers=headers)
        assert search_resp.status_code == 200
        assert search_resp.json()["total"] == 1

        reuse_resp = client.post(f"/v1/chat/history/{history.entry_id}/reuse", headers=headers)
        assert reuse_resp.status_code == 200
        assert reuse_resp.json()["preload"]["topic"] == "monthly revenue trend"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_templates_suggestions_and_opt_out_stay_private_to_user(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        user_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, user_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        service = get_conversation_memory_service()
        service.record_interaction(
            user_id=user_claims.sub,
            department_id=user_claims.department,
            session_id=str(uuid4()),
            intent_type="chat_query",
            topic="revenue topic",
            filter_context="month filter",
            key_result_summary="Result summary for topic",
            sensitivity_level=1,
            matched_metrics=["doanh thu thuần"],
        )

        save_resp = client.post(
            "/v1/chat/templates",
            json={
                "name": "Revenue Monthly",
                "query_intent": "revenue trend",
                "filters": "month filter",
                "time_range": "last_30_days",
                "output_format": "table",
            },
            headers=headers,
        )
        assert save_resp.status_code == 201

        suggestions_resp = client.get("/v1/chat/suggestions", headers=headers)
        assert suggestions_resp.status_code == 200
        assert suggestions_resp.json()["total"] >= 1

        templates_resp = client.get("/v1/chat/templates", headers=headers)
        assert templates_resp.status_code == 200
        assert templates_resp.json()["total"] == 1

        toggle_resp = client.put(
            "/v1/chat/preferences/learning",
            json={"enabled": False},
            headers=headers,
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled"] is False

    def test_memory_service_blocks_raw_values_and_cross_user_search(self) -> None:
        service = get_conversation_memory_service()
        with pytest.raises(ValueError):
            service.store_session_summary(
                user_id="user-a",
                department_id="sales",
                session_id=str(uuid4()),
                sensitivity_level=1,
                intent_type="chat_query",
                topic="revenue 100",
                filter_context="march",
                summary_text="contains 100",
            )

        safe_summary = service.store_session_summary(
            user_id="user-a",
            department_id="sales",
            session_id=str(uuid4()),
            sensitivity_level=1,
            intent_type="chat_query",
            topic="revenue topic",
            filter_context="march filter",
            summary_text="business summary only",
        )
        assert safe_summary.user_id == "user-a"

        service.record_interaction(
            user_id="user-a",
            department_id="sales",
            session_id=str(uuid4()),
            intent_type="chat_query",
            topic="revenue topic",
            filter_context="march filter",
            key_result_summary="business summary only",
            sensitivity_level=1,
            matched_metrics=[],
        )
        user_a_results = service.search_history(user_id="user-a", keyword="revenue")
        user_b_results = service.search_history(user_id="user-b", keyword="revenue")
        assert len(user_a_results) == 1
        assert user_b_results == []
        assert service.memory_audit() == []

    def test_similarity_threshold_filters_irrelevant_summaries(self) -> None:
        service = get_conversation_memory_service()
        service.store_session_summary(
            user_id="user-a",
            department_id="sales",
            session_id=str(uuid4()),
            sensitivity_level=1,
            intent_type="chat_query",
            topic="revenue trend",
            filter_context="march period",
            summary_text="business summary only",
        )
        service.store_session_summary(
            user_id="user-a",
            department_id="sales",
            session_id=str(uuid4()),
            sensitivity_level=1,
            intent_type="chat_query",
            topic="inventory ageing",
            filter_context="warehouse filter",
            summary_text="business inventory only",
        )
        context = service.build_context_bundle(
            user_id="user-a",
            department_id="sales",
            clearance=1,
            query="revenue trend for march",
        )
        assert len(context["summaries"]) == 1

    def test_department_change_prevents_old_department_summary_recall(self) -> None:
        service = get_conversation_memory_service()
        service.store_session_summary(
            user_id="user-a",
            department_id="sales",
            session_id=str(uuid4()),
            sensitivity_level=1,
            intent_type="chat_query",
            topic="revenue trend",
            filter_context="march period",
            summary_text="business summary only",
        )
        context = service.build_context_bundle(
            user_id="user-a",
            department_id="finance",
            clearance=1,
            query="revenue trend for march",
        )
        assert context["summaries"] == []

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_memory_audit_route_only_returns_callers_own_violations(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        user_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, user_claims)
        service = get_conversation_memory_service()
        service._history["other-user"].append(  # noqa: SLF001 - targeted regression fixture
            HistoryEntry(
                entry_id=str(uuid4()),
                user_id="other-user",
                department_id="finance",
                session_id=str(uuid4()),
                created_at=datetime.now(UTC),
                intent_type="chat_query",
                topic="salary 100",
                filter_context="private",
                key_result_summary="pii 100",
            )
        )
        service.record_interaction(
            user_id=user_claims.sub,
            department_id=user_claims.department,
            session_id=str(uuid4()),
            intent_type="chat_query",
            topic="safe topic",
            filter_context="safe filter",
            key_result_summary="safe summary",
            sensitivity_level=1,
            matched_metrics=[],
        )

        resp = client.get("/v1/chat/history/audit", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        assert resp.json()["violations"] == []
