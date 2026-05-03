"""Tests for the orchestration chat query endpoint — Story 2A.1."""

from __future__ import annotations

import asyncio
import hashlib
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import fakeredis
import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.fastapi_deps import reset_cerbos_client_cache
from aial_shared.auth.keycloak import JWTClaims
from orchestration.admin_control.user_role_management import get_user_role_management_service, reset_user_role_management_service
from orchestration.approval.workflow import ApprovalDecision, QueryIntent, create_approval_request, get_approval_store
from orchestration.cache.query_result_cache import (
    CachedQueryResult,
    QueryCacheContext,
    normalize_query_intent,
    reset_query_result_cache,
)
from orchestration.semantic.management import get_semantic_layer_service
from orchestration.audit.read_model import AuditFilter, get_audit_read_model
from orchestration.security.column_masker import ColumnSensitivity
from orchestration.streaming.events import SseEventType
from orchestration.streaming.queue import get_stream_queue


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={
            "sub": "user-123",
            "email": "user@aial.local",
            "department": "sales",
            "roles": ["user"],
            "clearance": 1,
        },
    )


@pytest.fixture()
def client() -> TestClient:
    reset_cerbos_client_cache()
    reset_user_role_management_service()
    from orchestration.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_query_cache() -> None:
    reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))


def _auth_mocks(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = claims.raw
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()

    def _default_check(principal: JWTClaims, resource_kind: str, resource_id: str, action: str, **_: object) -> MagicMock:
        return MagicMock(allowed=action == "query")

    mock_cerbos.check.side_effect = _default_check
    mock_cerbos_cls.return_value = mock_cerbos


def _build_cache_context(query: str, claims: JWTClaims) -> QueryCacheContext:
    semantic_context = get_semantic_layer_service().match_query(query)
    version = (
        "|".join(sorted(str(entry["active_version_id"]) for entry in semantic_context if entry.get("active_version_id")))
        if semantic_context
        else get_semantic_layer_service().cache_invalidated_at.isoformat()
    )
    freshness = (
        "|".join(sorted(str(entry["freshness_rule"]) for entry in semantic_context if entry.get("freshness_rule")))
        if semantic_context
        else "sql:adhoc"
    )
    return QueryCacheContext(
        query=query,
        normalized_intent=normalize_query_intent(query),
        owner_user_id=claims.sub,
        department_id=claims.department,
        role_scope="user",
        semantic_layer_version=version,
        data_freshness_class=freshness,
    )


class TestChatQueryEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_returns_stream_handle_with_request_id_and_trace_id(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Doanh thu HCM tháng 3?", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "streaming"
        UUID(body["request_id"])
        UUID(body["trace_id"])

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_sensitive_query_requires_approval_when_user_lacks_authority(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Show employee salary by region", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approval_required"
        assert body["approval_state"] == "APPROVAL_REQUESTED"
        assert body["approval_request_id"]
        assert get_stream_queue().verify_owner(body["request_id"], sample_claims.sub) is False

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_approved_sensitive_query_can_execute(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        store = get_approval_store()
        intent = QueryIntent(
            user_id=sample_claims.sub,
            department=sample_claims.department,
            sensitivity_tier=2,
            intent_type="chat_query",
            filters={"query_preview": "Show employee salary by region"},
            estimated_row_count=100,
            query_digest=hashlib.sha256("Show employee salary by region".encode("utf-8")).hexdigest(),
        )
        approval_request = create_approval_request(intent, store=store)
        store.decide(
            approval_request.request_id,
            ApprovalDecision(approver_id="approver-1", decision="approved", reason="ok"),
        )

        resp = client.post(
            "/v1/chat/query",
            json={
                "query": "Show employee salary by region",
                "session_id": str(uuid4()),
                "approval_request_id": approval_request.request_id,
            },
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "streaming"
        assert get_stream_queue().verify_owner(body["request_id"], sample_claims.sub) is True

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_sensitive_query_with_authority_still_requires_cerbos_allow(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        claims = JWTClaims(
            sub=sample_claims.sub,
            email=sample_claims.email,
            department=sample_claims.department,
            roles=sample_claims.roles,
            clearance=sample_claims.clearance,
            raw=sample_claims.raw,
            approval_authority=True,
        )
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, claims)
        mock_cerbos = mock_cerbos_cls.return_value

        def _check(principal: JWTClaims, resource_kind: str, resource_id: str, action: str, **_: object) -> MagicMock:
            return MagicMock(allowed=action == "query")

        mock_cerbos.check.side_effect = _check

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Show employee salary by region", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approval_required"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_sensitive_query_bypasses_approval_only_when_cerbos_allows(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        claims = JWTClaims(
            sub=sample_claims.sub,
            email=sample_claims.email,
            department=sample_claims.department,
            roles=sample_claims.roles,
            clearance=sample_claims.clearance,
            raw=sample_claims.raw,
            approval_authority=True,
        )
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, claims)
        mock_cerbos = mock_cerbos_cls.return_value

        def _check(principal: JWTClaims, resource_kind: str, resource_id: str, action: str, **_: object) -> MagicMock:
            return MagicMock(allowed=action in {"query", "query_sensitive"})

        mock_cerbos.check.side_effect = _check

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Show employee salary by region", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "streaming"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_query_handle_surfaces_unverified_data_source_warning(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        service = get_user_role_management_service()
        service.create_role(name="sales_analyst", schema_allowlist=["SALES_ANALYTICS"], actor="admin")
        service.create_user(
            user_id=sample_claims.sub,
            email=sample_claims.email,
            department=sample_claims.department,
            roles=["sales_analyst"],
            ldap_groups=["sales"],
        )
        with patch.object(
            service,
            "_probe_oracle_connection",
            return_value={"ok": False, "available_schemas": []},
        ):
            service.create_data_source(
                name="sales-primary",
                host="fail-sales-host",
                port=1521,
                service_name="SALESPDB1",
                username="sales_user",
                password="secret",
                schema_allowlist=["SALES_ANALYTICS"],
                actor="admin",
            )

        resp = client.post(
            "/v1/chat/query",
            json={"query": "show sales revenue", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Kết nối thất bại - kiểm tra thông tin trước khi dùng"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_query_denies_when_no_authorized_data_source_matches_principal(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        service = get_user_role_management_service()
        service.create_role(name="finance_analyst", schema_allowlist=["FINANCE_ANALYTICS"], actor="admin")
        with patch.object(
            service,
            "_probe_oracle_connection",
            return_value={"ok": True, "available_schemas": ["FINANCE_ANALYTICS"]},
        ):
            service.create_data_source(
                name="finance-primary",
                host="oracle-finance",
                port=1521,
                service_name="FINPDB1",
                username="finance_user",
                password="secret",
                schema_allowlist=["FINANCE_ANALYTICS"],
                actor="admin",
            )

        resp = client.post(
            "/v1/chat/query",
            json={"query": "show sales revenue", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 403

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_query_does_not_authorize_based_on_department_substring_in_data_source_name(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        service = get_user_role_management_service()
        service.create_role(name="finance_analyst", schema_allowlist=["FINANCE_ANALYTICS"], actor="admin")
        with patch.object(
            service,
            "_probe_oracle_connection",
            return_value={"ok": True, "available_schemas": ["FINANCE_ANALYTICS"]},
        ):
            service.create_data_source(
                name="sales-finance-bridge",
                host="oracle-finance",
                port=1521,
                service_name="FINPDB1",
                username="finance_user",
                password="secret",
                schema_allowlist=["FINANCE_ANALYTICS"],
                actor="admin",
            )

        resp = client.post(
            "/v1/chat/query",
            json={"query": "show sales revenue", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 403

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_approval_request_cannot_be_reused_for_different_long_query_with_same_prefix(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        store = get_approval_store()
        query_a = "Show employee salary by region for all managers in north division with allowance details A"
        intent = QueryIntent(
            user_id=sample_claims.sub,
            department=sample_claims.department,
            sensitivity_tier=2,
            intent_type="chat_query",
            filters={"query_preview": " ".join(query_a.split())[:80]},
            estimated_row_count=100,
            query_digest=hashlib.sha256(" ".join(query_a.split()).encode("utf-8")).hexdigest(),
        )
        approval_request = create_approval_request(intent, store=store)
        store.decide(
            approval_request.request_id,
            ApprovalDecision(approver_id="approver-1", decision="approved", reason="ok"),
        )

        query_b = "Show employee salary by region for all managers in north division with allowance details B"
        resp = client.post(
            "/v1/chat/query",
            json={
                "query": query_b,
                "session_id": str(uuid4()),
                "approval_request_id": approval_request.request_id,
            },
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 409

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_empty_query_returns_400_invalid_query(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "   ", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 400
        body = resp.json()
        assert "invalid-query" in body.get("type", "")
        assert "detail" in body

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_query_too_long_returns_400(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "x" * 2001, "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 400
        assert "invalid-query" in resp.json().get("type", "")

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    @patch("orchestration.routes.query.asyncio.create_task")
    def test_semantic_cache_hit_bypasses_graph_execution_for_same_scope(
        self,
        mock_create_task: MagicMock,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        mock_create_task.side_effect = lambda coro: coro.close()
        cache = reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))
        source_query = "Doanh thu Q1 2026 theo chi nhánh?"
        cache.store(
            CachedQueryResult.build(
                context=_build_cache_context(source_query, sample_claims),
                answer="cached revenue answer",
                rows=[{"branch": "HCM", "revenue": 100}],
                generated_sql="SELECT revenue FROM sales_summary",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Cho tôi xem doanh thu Q1 2026 chia theo chi nhánh?", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["cache_hit"] is True
        assert body["freshness_indicator"]
        assert body["cache_similarity"] >= 0.85
        mock_create_task.assert_not_called()

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    @patch("orchestration.routes.query.asyncio.create_task")
    def test_force_refresh_invalidates_cache_and_runs_live_query(
        self,
        mock_create_task: MagicMock,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        mock_create_task.side_effect = lambda coro: coro.close()
        cache = reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))
        query = "Doanh thu Q1 2026 theo chi nhánh?"
        context = _build_cache_context(query, sample_claims)
        cache.store(
            CachedQueryResult.build(
                context=context,
                answer="cached revenue answer",
                rows=[{"branch": "HCM", "revenue": 100}],
                generated_sql="SELECT revenue FROM sales_summary",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        resp = client.post(
            "/v1/chat/query",
            json={"query": query, "session_id": str(uuid4()), "force_refresh": True},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        assert resp.json()["cache_hit"] is False
        mock_create_task.assert_called_once()
        assert cache.find_best_match(context) is None

    def test_missing_auth_header_returns_auth_failed_code(self, client: TestClient) -> None:
        resp = client.post(
            "/v1/chat/query",
            json={"query": "test query", "session_id": str(uuid4())},
        )
        assert resp.status_code == 401
        assert resp.json() == {"code": "AUTH_FAILED"}

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    def test_invalid_jwt_returns_auth_failed_code(
        self,
        mock_decode: MagicMock,
        client: TestClient,
    ) -> None:
        mock_decode.side_effect = Exception("invalid token signature")
        resp = client.post(
            "/v1/chat/query",
            json={"query": "test query", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer bad-jwt"},
        )
        assert resp.status_code == 401
        assert resp.json() == {"code": "AUTH_FAILED"}


class TestSqlExplanationStub:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_sql_explanation_returns_data_source(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        # Must pre-register explanation (owned by caller) — endpoint returns 404 for unknown IDs
        from orchestration.explanation.generator import SqlExplanationGenerator
        from orchestration.routes.query import _explanation_store
        req_id = str(uuid4())
        gen = SqlExplanationGenerator()
        exp = gen.explain_kw(sql="SELECT revenue FROM sales_summary")
        _explanation_store[req_id] = (sample_claims.sub, exp)

        resp = client.get(
            f"/v1/chat/query/{req_id}/sql-explanation",
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "data_source" in body
        assert body.get("raw_sql") is None


class TestMetricsEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_metrics_endpoint_exposes_cache_counters(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        cache = reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))
        source_query = "Doanh thu Q1 2026 theo chi nhánh?"
        cache.store(
            CachedQueryResult.build(
                context=_build_cache_context(source_query, sample_claims),
                answer="cached revenue answer",
                rows=[{"branch": "HCM", "revenue": 100}],
                generated_sql="SELECT revenue FROM sales_summary",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        query_resp = client.post(
            "/v1/chat/query",
            json={"query": "Cho tôi xem doanh thu Q1 2026 chia theo chi nhánh?", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert query_resp.status_code == 200

        metrics_resp = client.get("/metrics")

        assert metrics_resp.status_code == 200
        assert "aial_semantic_query_cache_hits_total 1.0" in metrics_resp.text
        assert "aial_semantic_query_cache_hit_rate 1.0" in metrics_resp.text


class TestCrossDomainExecution:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_cross_domain_query_route_returns_stream_handle(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth_mocks(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)

        resp = client.post(
            "/v1/chat/query",
            json={"query": "Chi phí vận hành Q1 so với ngân sách được duyệt?", "session_id": str(uuid4())},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "streaming"
        assert "FINANCE" in body["message"]
        assert "BUDGET" in body["message"]

    def test_cross_domain_background_runner_emits_conflict_and_audits_subqueries(self, sample_claims: JWTClaims) -> None:
        from orchestration.routes.query import _run_cross_domain_query_and_cache_explanation

        async def _run() -> None:
            request_id = str(uuid4())
            session_id = str(uuid4())
            queue = get_stream_queue()
            queue.create(request_id, owner_user_id=sample_claims.sub)
            get_audit_read_model()._records.clear()  # noqa: SLF001

            await _run_cross_domain_query_and_cache_explanation(
                request_id=request_id,
                query="Chi phí vận hành Q1 so với ngân sách được duyệt?",
                session_id=session_id,
                principal=sample_claims,
                trace_id=str(uuid4()),
            )

            events = list(queue.drain(request_id))
            done_events = [event for event in events if event.type == SseEventType.DONE]
            assert done_events
            done_event = done_events[0].data
            assert done_event["confidence_state"] == "cross-source-conflict"
            assert "FINANCE" in done_event["conflict_detail"]
            assert len(done_event["provenance"]) == 2

            records = get_audit_read_model().search(
                AuditFilter(request_id=request_id, action="cross_domain_subquery"),
                page=1,
                page_size=20,
            )
            assert len(records) == 2
            assert {record.data_sources[0] for record in records} == {"finance-primary", "budget-primary"}

        asyncio.run(_run())


class TestRuntimeSecurityWiring:
    def test_background_runner_applies_column_and_pii_masking(self, sample_claims: JWTClaims) -> None:
        from orchestration.routes.query import _run_graph_and_cache_explanation

        async def _run() -> None:
            request_id = str(uuid4())
            queue = get_stream_queue()
            queue.create(request_id, owner_user_id=sample_claims.sub)

            with patch("orchestration.routes.query.invoke_query_graph") as mock_invoke:
                mock_invoke.return_value = {
                    "sql_result": [
                        {
                            "salary": 50000,
                            "notes": "Contact user@company.com at 0912345678",
                        }
                    ],
                    "column_sensitivity": {"salary": ColumnSensitivity.CONFIDENTIAL},
                    "free_text_columns": ["notes"],
                    "generated_sql": "SELECT salary, notes FROM employees",
                    "final_response": "done",
                }
                await _run_graph_and_cache_explanation(
                    request_id=request_id,
                    query="Show employee salary and notes",
                    session_id=str(uuid4()),
                    principal=sample_claims,
                    trace_id=str(uuid4()),
                )

            events = list(queue.drain(request_id))
            row_events = [event for event in events if event.type == SseEventType.ROW]
            assert row_events, "secured row event should be emitted"
            secured_row = row_events[0].data["rows"][0]
            assert secured_row["salary"] == "***"
            assert "user@company.com" not in secured_row["notes"]
            assert "0912345678" not in secured_row["notes"]

        asyncio.run(_run())

    def test_background_runner_masks_free_text_when_pii_scan_is_async(self, sample_claims: JWTClaims) -> None:
        from orchestration.routes.query import _PII_SCAN_PENDING, _run_graph_and_cache_explanation

        async def _run() -> None:
            request_id = str(uuid4())
            queue = get_stream_queue()
            queue.create(request_id, owner_user_id=sample_claims.sub)

            large_rows = [
                {"notes": f"Contact user{i}@company.com at 0912345678"}
                for i in range(10_001)
            ]

            with patch("orchestration.routes.query.invoke_query_graph") as mock_invoke:
                mock_invoke.return_value = {
                    "sql_result": large_rows,
                    "free_text_columns": ["notes"],
                    "generated_sql": "SELECT notes FROM employees",
                    "final_response": "done",
                }
                await _run_graph_and_cache_explanation(
                    request_id=request_id,
                    query="Show employee notes",
                    session_id=str(uuid4()),
                    principal=sample_claims,
                    trace_id=str(uuid4()),
                )

            events = list(queue.drain(request_id))
            row_events = [event for event in events if event.type == SseEventType.ROW]
            assert row_events, "placeholder row event should still be emitted"
            first_row = row_events[0].data["rows"][0]
            assert first_row["notes"] == _PII_SCAN_PENDING
            assert "user0@company.com" not in str(first_row)

        asyncio.run(_run())

    def test_background_runner_applies_runtime_row_limit(self, sample_claims: JWTClaims) -> None:
        from orchestration.routes.query import _run_graph_and_cache_explanation

        async def _run() -> None:
            request_id = str(uuid4())
            queue = get_stream_queue()
            queue.create(request_id, owner_user_id=sample_claims.sub)

            with patch("orchestration.routes.query.invoke_query_graph") as mock_invoke:
                mock_invoke.return_value = {
                    "sql_result": [{"row": index} for index in range(5)],
                    "generated_sql": "SELECT * FROM sales",
                    "final_response": "done",
                }
                await _run_graph_and_cache_explanation(
                    request_id=request_id,
                    query="Show rows",
                    session_id=str(uuid4()),
                    principal=sample_claims,
                    trace_id=str(uuid4()),
                    execution_settings={"data_source": "sales-primary", "row_limit": 2, "query_timeout_seconds": 30},
                )

            events = list(queue.drain(request_id))
            row_events = [event for event in events if event.type == SseEventType.ROW]
            assert len(row_events[0].data["rows"]) == 2

        asyncio.run(_run())

    def test_background_runner_uses_semantic_and_memory_context_in_output(self, sample_claims: JWTClaims) -> None:
        from orchestration.routes.query import _explanation_store, _run_graph_and_cache_explanation

        async def _run() -> None:
            request_id = str(uuid4())
            queue = get_stream_queue()
            queue.create(request_id, owner_user_id=sample_claims.sub)

            await _run_graph_and_cache_explanation(
                request_id=request_id,
                query="Doanh thu thuần tháng 3",
                session_id=str(uuid4()),
                principal=sample_claims,
                trace_id=str(uuid4()),
                semantic_context=[{"term": "doanh thu thuần", "formula": "SUM(NET_REVENUE)"}],
                memory_context={"summaries": [{"topic": "monthly revenue trend"}]},
                preference_context=[{"label": "doanh thu thuần"}],
            )

            events = list(queue.drain(request_id))
            done_events = [event for event in events if event.type == SseEventType.DONE]
            assert done_events
            answer = done_events[0].data.get("answer", "")
            assert "doanh thu thuần" in answer
            assert "memory:1" in answer

            _, explanation = _explanation_store[request_id]
            assert "NET_REVENUE" in (explanation.raw_sql or "")

        asyncio.run(_run())
