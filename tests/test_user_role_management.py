"""Tests for Story 5A.1 - User & Role Management (FR-AD2)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import fakeredis
import pytest
from fastapi.testclient import TestClient
from orchestration.admin_control.user_role_management import (
    UserRoleManagementService,
    get_user_role_management_service,
    reset_user_role_management_service,
)
from orchestration.audit.read_model import AuditFilter, AuditRecord, get_audit_read_model
from orchestration.cache.query_result_cache import (
    CachedQueryResult,
    QueryCacheContext,
    normalize_query_intent,
    reset_query_result_cache,
)

from aial_shared.auth.keycloak import JWTClaims


@pytest.fixture(autouse=True)
def reset_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIAL_CONFIG_CATALOG_PERSISTENCE", "memory")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    reset_user_role_management_service()
    get_audit_read_model()._records.clear()  # noqa: SLF001 - test reset for module-level store
    reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture()
def admin_claims() -> JWTClaims:
    return JWTClaims(
        sub="admin-1",
        email="admin@aial.local",
        department="engineering",
        roles=("admin",),
        clearance=3,
        raw={},
    )


@pytest.fixture()
def regular_claims() -> JWTClaims:
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


class _CatalogStoreStub:
    def __init__(self) -> None:
        self.roles: list[dict[str, object]] = []
        self.data_sources: list[dict[str, object]] = []

    def load_roles(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.roles]

    def upsert_role(self, payload: dict[str, object], *, updated_at: datetime) -> None:
        del updated_at
        self.roles = [item for item in self.roles if item["name"] != payload["name"]]
        self.roles.append(dict(payload))

    def load_data_sources(self) -> list[dict[str, object]]:
        return [dict(item) for item in self.data_sources]

    def upsert_data_source(
        self,
        payload: dict[str, object],
        *,
        username: str,
        password: str,
        updated_at: datetime,
    ) -> None:
        del updated_at
        record = dict(payload)
        record["_secret_payload"] = {"username": username, "password": password}
        self.data_sources = [item for item in self.data_sources if item["name"] != payload["name"]]
        self.data_sources.append(record)


class TestRoleManagement:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_can_create_role_with_schema_allowlist_and_audit(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)

        resp = client.post(
            "/v1/admin/roles",
            json={"name": "finance_analyst", "schema_allowlist": ["FINANCE_ANALYTICS"]},
            headers={"Authorization": "Bearer fake-jwt"},
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["role"]["name"] == "finance_analyst"
        assert body["role"]["schema_allowlist"] == ["FINANCE_ANALYTICS"]
        assert body["role"]["cerbos_policy_status"] == "synced"
        assert body["role"]["data_source_config_status"] == "persisted"

        records = get_audit_read_model().search(audit_filter=AuditFilter(), page=1, page_size=20)
        assert any(r.intent_type == "admin:role_create" and r.user_id == admin_claims.sub for r in records)

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_non_admin_cannot_create_role(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        regular_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, regular_claims)

        resp = client.post(
            "/v1/admin/roles",
            json={"name": "finance_analyst", "schema_allowlist": ["FINANCE_ANALYTICS"]},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 403

    def test_catalog_roles_and_data_sources_reload_from_persistent_store(self) -> None:
        store = _CatalogStoreStub()
        service = UserRoleManagementService(catalog_store=store)

        role = service.create_role(
            name="finance_analyst",
            schema_allowlist=["finance_analytics"],
            actor="admin-1",
            description="Finance scoped access",
            data_source_names=["oracle-finance"],
            metric_allowlist=["doanh thu thuần"],
        )
        config = service.create_data_source(
            name="oracle-finance",
            description="Finance warehouse",
            host="db.company.local",
            port=1521,
            service_name="FINPRD",
            username="reader",
            password="secret",
            schema_allowlist=["FINANCE_ANALYTICS"],
            actor="admin-1",
        )

        reloaded = UserRoleManagementService(catalog_store=store)

        reloaded_role = reloaded.list_roles()[0]
        assert reloaded_role.name == role.name
        assert reloaded_role.data_source_names == ["oracle-finance"]
        assert reloaded_role.metric_allowlist == ["doanh thu thuần"]

        reloaded_source = reloaded.get_data_source(config.name)
        assert reloaded_source is not None
        assert reloaded_source.description == "Finance warehouse"
        assert reloaded_source.available_schemas == ["FINANCE_ANALYTICS"]


class TestUserManagement:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_can_create_user_with_role_assignment(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        role_resp = client.post(
            "/v1/admin/roles",
            json={"name": "finance_analyst", "schema_allowlist": ["FINANCE_ANALYTICS"]},
            headers=headers,
        )
        assert role_resp.status_code == 201

        resp = client.post(
            "/v1/admin/users",
            json={
                "user_id": "lan.finance",
                "email": "lan.finance@aial.local",
                "department": "finance",
                "roles": ["finance_analyst"],
                "ldap_groups": ["finance"],
            },
            headers=headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["user_id"] == "lan.finance"
        assert body["user"]["roles"] == ["finance_analyst"]

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_ldap_sync_updates_department_and_sync_status(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        client.post(
            "/v1/admin/users",
            json={
                "user_id": "minh.sales",
                "email": "minh.sales@aial.local",
                "department": "sales",
                "roles": [],
                "ldap_groups": ["sales"],
            },
            headers=headers,
        )

        sync_resp = client.post(
            "/v1/admin/users/ldap-sync",
            json={
                "updates": [
                    {
                        "user_id": "minh.sales",
                        "department": "finance",
                        "roles": [],
                        "ldap_groups": ["finance"],
                    }
                ]
            },
            headers=headers,
        )
        assert sync_resp.status_code == 200
        assert sync_resp.json()["sync"]["synced_users"] == 1
        assert sync_resp.json()["sync"]["interval_minutes"] == 15

        user_resp = client.get("/v1/admin/users/minh.sales", headers=headers)
        assert user_resp.status_code == 200
        assert user_resp.json()["user"]["department"] == "finance"

        status_resp = client.get("/v1/admin/users/sync-status", headers=headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["interval_minutes"] == 15
        assert status_resp.json()["last_run_at"] is not None

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_delete_user_soft_deletes_and_preserves_audit(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        model = get_audit_read_model()
        model.append(
            AuditRecord(
                request_id=str(uuid4()),
                user_id="deleted.user",
                department_id="sales",
                session_id=str(uuid4()),
                timestamp=datetime.now(UTC),
                intent_type="query",
                sensitivity_tier="LOW",
                sql_hash="abc",
                data_sources=["sales_summary"],
                rows_returned=1,
                latency_ms=10,
                policy_decision="ALLOW",
                status="SUCCESS",
            )
        )

        create_resp = client.post(
            "/v1/admin/users",
            json={
                "user_id": "deleted.user",
                "email": "deleted.user@aial.local",
                "department": "sales",
                "roles": [],
                "ldap_groups": ["sales"],
            },
            headers=headers,
        )
        assert create_resp.status_code == 201

        delete_resp = client.delete("/v1/admin/users/deleted.user", headers=headers)
        assert delete_resp.status_code == 200
        body = delete_resp.json()
        assert body["status"] == "deleted"
        assert body["user"]["is_deleted"] is True
        assert body["user"]["sessions_revoked"] is True
        assert body["user"]["retention_until"] is not None

        records = model.search(audit_filter=AuditFilter(user_id="deleted.user"), page=1, page_size=20)
        assert len(records) >= 1

    def test_update_user_invalidates_owned_semantic_cache_entries(self) -> None:
        service = get_user_role_management_service()
        service.create_role(name="sales_analyst", schema_allowlist=["SALES_ANALYTICS"], actor="admin")
        service.create_user(
            user_id="minh.sales",
            email="minh.sales@aial.local",
            department="sales",
            roles=["sales_analyst"],
            ldap_groups=["sales"],
        )
        cache = reset_query_result_cache(fakeredis.FakeRedis(decode_responses=True))
        context = QueryCacheContext(
            query="Doanh thu tháng 3",
            normalized_intent=normalize_query_intent("Doanh thu tháng 3"),
            owner_user_id="minh.sales",
            department_id="sales",
            role_scope="sales_analyst",
            semantic_layer_version="v1",
            data_freshness_class="daily",
        )
        cache.store(
            CachedQueryResult.build(
                context=context,
                answer="cached",
                rows=[{"revenue": 100}],
                generated_sql="SELECT revenue FROM sales",
                data_source="sales-primary",
                pii_scan_mode="inline",
            )
        )

        service.update_user("minh.sales", department="finance", roles=["sales_analyst"])

        assert cache.find_best_match(context) is None


class TestBulkImport:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_bulk_import_preview_validates_rows_before_commit(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        csv_content = (
            "user_id,email,department,roles,ldap_groups\n"
            "valid.user,valid@aial.local,finance,,finance\n"
            ",missing@aial.local,finance,,finance\n"
        )
        preview_resp = client.post(
            "/v1/admin/users/import/preview",
            json={"csv_content": csv_content},
            headers=headers,
        )
        assert preview_resp.status_code == 200
        preview = preview_resp.json()
        assert preview["valid_rows"] == 1
        assert preview["invalid_rows"] == 1
        assert preview["errors"]

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_bulk_import_commit_creates_users_when_csv_valid(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        csv_content = "user_id,email,department,roles,ldap_groups\nimported.user,imported@aial.local,finance,,finance\n"
        commit_resp = client.post(
            "/v1/admin/users/import/commit",
            json={"csv_content": csv_content},
            headers=headers,
        )
        assert commit_resp.status_code == 201
        body = commit_resp.json()
        assert body["imported"] == 1

        user_resp = client.get("/v1/admin/users/imported.user", headers=headers)
        assert user_resp.status_code == 200
        assert user_resp.json()["user"]["email"] == "imported@aial.local"


class TestDataSourceConfiguration:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_template_endpoint_returns_standardized_catalog_shape(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        resp = client.get("/v1/admin/config-catalog/template", headers=headers)

        assert resp.status_code == 200
        body = resp.json()
        assert body["catalog_version"]
        assert body["data_sources"]
        assert body["semantic_metrics"]
        assert body["role_mappings"]

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_create_data_source_stores_credentials_in_vault_and_audits_without_secret_values(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        with patch.object(
            get_user_role_management_service(),
            "_probe_oracle_connection",
            return_value={"ok": True, "available_schemas": ["FINANCE_ANALYTICS", "SALES_ANALYTICS"]},
        ):
            resp = client.post(
                "/v1/admin/data-sources",
                json={
                    "name": "oracle-finance",
                    "host": "oracle.internal",
                    "port": 1521,
                    "service_name": "FINPDB1",
                    "username": "finance_user",
                    "password": "super-secret",
                    "schema_allowlist": ["FINANCE_ANALYTICS"],
                    "query_timeout_seconds": 30,
                    "row_limit": 50000,
                },
                headers=headers,
            )

        assert resp.status_code == 201
        body = resp.json()["data_source"]
        assert body["status"] == "VERIFIED"
        assert body["credentials_status"] == "stored_in_vault"
        assert "password" not in str(body)
        assert body["query_warning"] is None

        audit_records = get_audit_read_model().search(
            AuditFilter(action="admin:data_source_create"),
            page=1,
            page_size=20,
        )
        assert len(audit_records) == 1
        assert "super-secret" not in str(audit_records[0].metadata)

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_failed_connection_is_saved_unverified_and_exposes_query_warning(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        with patch.object(
            get_user_role_management_service(),
            "_probe_oracle_connection",
            return_value={"ok": False, "available_schemas": []},
        ):
            resp = client.post(
                "/v1/admin/data-sources",
                json={
                    "name": "oracle-unverified",
                    "host": "fail-host.internal",
                    "port": 1521,
                    "service_name": "FINPDB1",
                    "username": "finance_user",
                    "password": "super-secret",
                    "schema_allowlist": ["FINANCE_ANALYTICS"],
                },
                headers=headers,
            )

        assert resp.status_code == 201
        assert resp.json()["data_source"]["status"] == "UNVERIFIED"
        detail_resp = client.get("/v1/admin/data-sources/oracle-unverified", headers=headers)
        assert detail_resp.status_code == 200
        expected_warning = "Kết nối thất bại - kiểm tra thông tin trước khi dùng"
        assert detail_resp.json()["query_execution"]["warning"] == expected_warning

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_update_data_source_row_limit_logs_previous_and_new_values(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        with patch.object(
            get_user_role_management_service(),
            "_probe_oracle_connection",
            return_value={"ok": True, "available_schemas": ["FINANCE_ANALYTICS"]},
        ):
            create_resp = client.post(
                "/v1/admin/data-sources",
                json={
                    "name": "oracle-finance",
                    "host": "oracle.internal",
                    "port": 1521,
                    "service_name": "FINPDB1",
                    "username": "finance_user",
                    "password": "super-secret",
                    "schema_allowlist": ["FINANCE_ANALYTICS"],
                    "row_limit": 50000,
                },
                headers=headers,
            )
            assert create_resp.status_code == 201

            update_resp = client.patch(
                "/v1/admin/data-sources/oracle-finance",
                json={"row_limit": 10000},
                headers=headers,
            )

        assert update_resp.status_code == 200
        changes = update_resp.json()["changes"]
        assert changes["row_limit"]["previous_value"] == 50000
        assert changes["row_limit"]["new_value"] == 10000
        assert changes["row_limit"]["changed_by"] == admin_claims.sub

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_can_import_standardized_config_catalog(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        with patch.object(
            get_user_role_management_service(),
            "_probe_oracle_connection",
            return_value={"ok": True, "available_schemas": ["FINANCE_ANALYTICS", "COMMON_DIM"]},
        ):
            resp = client.post(
                "/v1/admin/config-catalog/import",
                json={
                    "catalog_version": "2026-05-04",
                    "role_mappings": [
                        {
                            "name": "finance_analyst",
                            "description": "Finance analyst",
                            "schema_allowlist": ["FINANCE_ANALYTICS", "COMMON_DIM"],
                            "data_source_names": ["oracle-finance"],
                            "metric_allowlist": ["doanh thu thuan"],
                        }
                    ],
                    "data_sources": [
                        {
                            "name": "oracle-finance",
                            "description": "Primary finance warehouse",
                            "host": "oracle.internal",
                            "port": 1521,
                            "service_name": "FINPDB1",
                            "username": "finance_user",
                            "password": "super-secret",
                            "schema_allowlist": ["FINANCE_ANALYTICS", "COMMON_DIM"],
                            "query_timeout_seconds": 30,
                            "row_limit": 50000,
                        }
                    ],
                    "semantic_metrics": [
                        {
                            "term": "doanh thu thuan",
                            "aliases": ["net revenue"],
                            "definition": "Doanh thu sau chiet khau",
                            "formula": "SUM(NET_REVENUE)",
                            "aggregation": "sum",
                            "owner": "Finance",
                            "freshness_rule": "daily",
                            "grain": "daily_customer",
                            "unit": "VND",
                            "dimensions": ["date", "customer", "region"],
                            "source": {
                                "data_source": "oracle-finance",
                                "schema": "FINANCE_ANALYTICS",
                                "table": "F_SALES",
                            },
                            "joins": [{"target": "D_CUSTOMER", "on": "F_SALES.CUSTOMER_ID = D_CUSTOMER.CUSTOMER_ID"}],
                            "certified_filters": ["IS_DELETED = 0"],
                            "security": {"sensitivity_tier": 1, "allowed_roles": ["finance_analyst"]},
                        }
                    ],
                },
                headers=headers,
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["catalog_version"] == "2026-05-04"
        assert body["imported"]["roles"][0]["data_source_names"] == ["oracle-finance"]
        assert body["imported"]["data_sources"][0]["description"] == "Primary finance warehouse"
        assert body["imported"]["semantic_metrics"][0]["grain"] == "daily_customer"

        audit_records = get_audit_read_model().search(
            AuditFilter(action="admin:config_catalog_import"),
            page=1,
            page_size=20,
        )
        assert len(audit_records) == 1


class TestAuditDashboard:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_admin_can_filter_audit_logs_by_action_and_data_source(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        get_audit_read_model().append(
            AuditRecord(
                request_id="req-1",
                user_id="hoa@company.com",
                department_id="finance",
                session_id="session-1",
                timestamp=datetime.now(UTC),
                intent_type="query",
                sensitivity_tier="LOW",
                sql_hash="hash-1",
                data_sources=["oracle-finance"],
                rows_returned=5,
                latency_ms=120,
                policy_decision="ALLOW",
                status="SUCCESS",
            )
        )

        resp = client.get(
            "/v1/admin/audit-logs?action=query&data_source=oracle-finance",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_lifecycle_view_shows_denial_reason_and_cerbos_rule(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        model = get_audit_read_model()
        model.append(
            AuditRecord(
                request_id="req-42",
                user_id="hoa@company.com",
                department_id="finance",
                session_id="session-1",
                timestamp=datetime.now(UTC),
                intent_type="query_received",
                sensitivity_tier="LOW",
                sql_hash="hash-1",
                data_sources=["oracle-finance"],
                rows_returned=0,
                latency_ms=10,
                policy_decision="ALLOW",
                status="RECEIVED",
            )
        )
        model.append(
            AuditRecord(
                request_id="req-42",
                user_id="hoa@company.com",
                department_id="finance",
                session_id="session-1",
                timestamp=datetime.now(UTC),
                intent_type="query_denied",
                sensitivity_tier="LOW",
                sql_hash="hash-1",
                data_sources=["oracle-finance"],
                rows_returned=0,
                latency_ms=30,
                policy_decision="DENY",
                status="DENIED",
                denial_reason="approval_required",
                cerbos_rule="query_sensitive",
            )
        )

        resp = client.get("/v1/admin/audit-logs/req-42/lifecycle", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        assert resp.json()["event_count"] == 2
        assert resp.json()["events"][-1]["denial_reason"] == "approval_required"
        assert resp.json()["events"][-1]["cerbos_rule"] == "query_sensitive"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_export_audit_logs_returns_csv_and_logs_export_event(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        model = get_audit_read_model()
        model.append(
            AuditRecord(
                request_id="req-export",
                user_id="hoa@company.com",
                department_id="finance",
                session_id="session-1",
                timestamp=datetime.now(UTC),
                intent_type="query",
                sensitivity_tier="LOW",
                sql_hash="hash-1",
                data_sources=["oracle-finance"],
                rows_returned=5,
                latency_ms=120,
                policy_decision="ALLOW",
                status="SUCCESS",
            )
        )

        resp = client.get("/v1/admin/audit-logs/export", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "request_id,timestamp,user_id" in resp.text
        export_records = model.search(AuditFilter(action="admin:audit_export"), page=1, page_size=20)
        assert len(export_records) == 1

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_export_and_total_do_not_truncate_past_ten_thousand_rows(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        model = get_audit_read_model()
        for index in range(10_050):
            model.append(
                AuditRecord(
                    request_id=f"req-{index}",
                    user_id="hoa@company.com",
                    department_id="finance",
                    session_id="session-1",
                    timestamp=datetime.now(UTC),
                    intent_type="query",
                    sensitivity_tier="LOW",
                    sql_hash=f"hash-{index}",
                    data_sources=["oracle-finance"],
                    rows_returned=5,
                    latency_ms=120,
                    policy_decision="ALLOW",
                    status="SUCCESS",
                )
            )

        list_resp = client.get("/v1/admin/audit-logs", headers={"Authorization": "Bearer fake-jwt"})
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 10_050

        export_resp = client.get("/v1/admin/audit-logs/export", headers={"Authorization": "Bearer fake-jwt"})
        assert export_resp.status_code == 200
        assert export_resp.text.count("\n") == 10_051


class TestSystemHealthDashboard:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_dashboard_returns_metrics_and_30_second_refresh_contract(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        service = get_user_role_management_service()
        service.set_health_snapshot(
            p50_latency_ms={"sql": 900, "rag": 1200, "hybrid": 1600, "forecast": 2500},
            p95_latency_ms={"sql": 2600, "rag": 3400, "hybrid": 5000, "forecast": 6200},
            cache_hit_ratio=0.83,
            error_rate_percent=0.6,
            token_cost_per_day=22.4,
            active_oracle_connections=8,
            weaviate_index_status="HEALTHY",
        )
        headers = {"Authorization": "Bearer fake-jwt"}

        resp = client.get("/v1/admin/system-health?time_range=last_7_days", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["refresh_interval_seconds"] == 30
        assert body["historical_days"] == 7
        assert set(body["p50_latency_ms"].keys()) == {"sql", "rag", "hybrid", "forecast"}

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_latency_alert_can_be_configured_and_acknowledged_with_audit(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}

        setting_resp = client.put(
            "/v1/admin/system-health/alert-settings",
            json={
                "scope_type": "global",
                "scope_id": "default",
                "metric_name": "p95_latency_ms",
                "threshold": 4000,
            },
            headers=headers,
        )
        assert setting_resp.status_code == 200

        service = get_user_role_management_service()
        service.set_health_snapshot(
            p50_latency_ms={"sql": 1000, "rag": 1300, "hybrid": 1800, "forecast": 2700},
            p95_latency_ms={"sql": 4500, "rag": 3500, "hybrid": 3900, "forecast": 3800},
            cache_hit_ratio=0.8,
            error_rate_percent=1.2,
            token_cost_per_day=24.0,
            active_oracle_connections=9,
            weaviate_index_status="DEGRADED",
        )

        dashboard_resp = client.get("/v1/admin/system-health", headers=headers)
        assert dashboard_resp.status_code == 200
        alerts = dashboard_resp.json()["alerts"]
        assert len(alerts) == 1
        assert alerts[0]["metric_name"] == "p95_latency_ms.sql"

        ack_resp = client.post(
            f"/v1/admin/system-health/alerts/{alerts[0]['alert_id']}/acknowledge",
            headers=headers,
        )
        assert ack_resp.status_code == 200
        assert ack_resp.json()["alert"]["status"] == "ACKNOWLEDGED"

        audit_records = get_audit_read_model().search(
            AuditFilter(action="admin:health_alert_acknowledge"),
            page=1,
            page_size=20,
        )
        assert len(audit_records) == 1

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_fired_health_alert_is_logged_to_audit(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        service = get_user_role_management_service()
        service.upsert_alert_setting(
            scope_type="global",
            scope_id="default",
            metric_name="p95_latency_ms",
            threshold=4000,
            actor=admin_claims.sub,
        )
        service.set_health_snapshot(
            p50_latency_ms={"sql": 1000, "rag": 1300, "hybrid": 1800, "forecast": 2700},
            p95_latency_ms={"sql": 4500, "rag": 3500, "hybrid": 3900, "forecast": 3800},
            cache_hit_ratio=0.8,
            error_rate_percent=1.2,
            token_cost_per_day=24.0,
            active_oracle_connections=9,
            weaviate_index_status="DEGRADED",
        )

        resp = client.get("/v1/admin/system-health", headers=headers)
        assert resp.status_code == 200
        audit_records = get_audit_read_model().search(
            AuditFilter(action="admin:health_alert_fired"),
            page=1,
            page_size=20,
        )
        assert len(audit_records) >= 1
        assert any(
            record.metadata and record.metadata.get("metric_name") == "p95_latency_ms.sql" for record in audit_records
        )
