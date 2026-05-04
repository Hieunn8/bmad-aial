"""Admin control center service for Epic 5A.

In-memory walking-skeleton service covering:
  - user and role management
  - Oracle data source configuration with Vault storage seam
  - audit dashboard export/lifecycle helpers
  - system health snapshot + alert management

Later stories can replace these stores with Keycloak, Vault, PostgreSQL,
Prometheus, and Grafana adapters without changing route contracts.
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from aial_shared.auth.keycloak import JWTClaims
from orchestration.persistence.config_catalog_store import get_config_catalog_store

_RETENTION_DAYS = 90
_AUDIT_RETENTION_DAYS = 365
_DEFAULT_LDAP_SYNC_MINUTES = 15
_DEFAULT_QUERY_TIMEOUT_SECONDS = 30
_DEFAULT_ROW_LIMIT = 50_000
_DEFAULT_CONNECTION_TIMEOUT_SECONDS = 5
_DEFAULT_REFRESH_INTERVAL_SECONDS = 30
_DEFAULT_LATENCY_THRESHOLD_MS = 8_000


@dataclass
class RoleDefinition:
    name: str
    schema_allowlist: list[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    data_source_names: list[str] = field(default_factory=list)
    metric_allowlist: list[str] = field(default_factory=list)
    cerbos_policy_status: str = "synced"
    data_source_config_status: str = "persisted"


@dataclass
class UserAccount:
    user_id: str
    email: str
    department: str
    roles: list[str] = field(default_factory=list)
    ldap_groups: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    is_deleted: bool = False
    deleted_at: datetime | None = None
    retention_until: datetime | None = None
    sessions_revoked_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["sessions_revoked"] = self.sessions_revoked_at is not None
        for key in ("created_at", "updated_at", "deleted_at", "retention_until", "sessions_revoked_at"):
            value = data[key]
            data[key] = value.isoformat() if isinstance(value, datetime) else value
        return data


@dataclass
class LdapSyncStatus:
    interval_minutes: int = _DEFAULT_LDAP_SYNC_MINUTES
    last_run_at: datetime | None = None
    synced_users: int = 0
    last_result: str = "never_run"

    def to_dict(self) -> dict[str, object]:
        return {
            "interval_minutes": self.interval_minutes,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "synced_users": self.synced_users,
            "last_result": self.last_result,
        }


@dataclass
class DataSourceConfig:
    name: str
    host: str
    port: int
    service_name: str
    schema_allowlist: list[str]
    query_timeout_seconds: int
    row_limit: int
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    vault_secret_ref: str
    description: str | None = None
    warning_message: str | None = None
    connection_timeout_seconds: int = _DEFAULT_CONNECTION_TIMEOUT_SECONDS
    last_test_at: datetime | None = None
    available_schemas: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "host": self.host,
            "port": self.port,
            "service_name": self.service_name,
            "schema_allowlist": self.schema_allowlist,
            "query_timeout_seconds": self.query_timeout_seconds,
            "row_limit": self.row_limit,
            "status": self.status,
            "warning_message": self.warning_message,
            "connection_timeout_seconds": self.connection_timeout_seconds,
            "last_test_at": self.last_test_at.isoformat() if self.last_test_at else None,
            "available_schemas": self.available_schemas,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "credentials_status": "stored_in_vault",
            "vault_secret_ref": self.vault_secret_ref,
            "query_warning": self.query_warning,
        }

    @property
    def query_warning(self) -> str | None:
        if self.status == "UNVERIFIED":
            return "Kết nối thất bại - kiểm tra thông tin trước khi dùng"
        return None


@dataclass
class AlertSetting:
    scope_type: str
    scope_id: str
    metric_name: str
    threshold: float
    created_by: str
    updated_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "metric_name": self.metric_name,
            "threshold": self.threshold,
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
        }


@dataclass
class HealthAlert:
    alert_id: str
    metric_name: str
    current_value: float
    threshold: float
    affected_service: str
    triggered_at: datetime
    status: str = "ACTIVE"
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    audit_logged_at: datetime | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "alert_id": self.alert_id,
            "metric_name": self.metric_name,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "affected_service": self.affected_service,
            "triggered_at": self.triggered_at.isoformat(),
            "status": self.status,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "audit_logged_at": self.audit_logged_at.isoformat() if self.audit_logged_at else None,
        }


@dataclass
class HealthSnapshot:
    p50_latency_ms: dict[str, int]
    p95_latency_ms: dict[str, int]
    cache_hit_ratio: float
    error_rate_percent: float
    token_cost_per_day: float
    active_oracle_connections: int
    weaviate_index_status: str
    refreshed_at: datetime
    grafana_embed_url: str
    time_range: str = "last_30_minutes"
    refresh_interval_seconds: int = _DEFAULT_REFRESH_INTERVAL_SECONDS
    historical_days: int = 7

    def to_dict(self, alerts: list[HealthAlert], settings: list[AlertSetting]) -> dict[str, object]:
        return {
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "cache_hit_ratio": self.cache_hit_ratio,
            "error_rate_percent": self.error_rate_percent,
            "token_cost_per_day": self.token_cost_per_day,
            "active_oracle_connections": self.active_oracle_connections,
            "weaviate_index_status": self.weaviate_index_status,
            "refreshed_at": self.refreshed_at.isoformat(),
            "time_range": self.time_range,
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "historical_days": self.historical_days,
            "historical_data_retention_months": 12,
            "grafana_embed_url": self.grafana_embed_url,
            "alerts": [alert.to_dict() for alert in alerts],
            "alert_settings": [setting.to_dict() for setting in settings],
        }


class UserRoleManagementService:
    def __init__(self, *, catalog_store: Any | None = None) -> None:
        self._users: dict[str, UserAccount] = {}
        self._roles: dict[str, RoleDefinition] = {}
        self._sync_status = LdapSyncStatus()
        self._data_sources: dict[str, DataSourceConfig] = {}
        self._vault_secrets: dict[str, dict[str, str]] = {}
        self._catalog_store = catalog_store
        self._health_snapshot = HealthSnapshot(
            p50_latency_ms={"sql": 850, "rag": 1_200, "hybrid": 1_550, "forecast": 2_300},
            p95_latency_ms={"sql": 2_400, "rag": 3_600, "hybrid": 4_800, "forecast": 6_400},
            cache_hit_ratio=0.82,
            error_rate_percent=0.7,
            token_cost_per_day=18.45,
            active_oracle_connections=6,
            weaviate_index_status="HEALTHY",
            refreshed_at=datetime.now(UTC),
            grafana_embed_url="http://localhost:3000/d/aial-overview/admin-health?viewPanel=7",
        )
        self._alert_settings: dict[tuple[str, str, str], AlertSetting] = {}
        self._alerts: dict[str, HealthAlert] = {}
        self._load_persisted_catalog()

    def _load_persisted_catalog(self) -> None:
        if self._catalog_store is None:
            return
        for payload in self._catalog_store.load_roles():
            role = _role_from_payload(payload)
            self._roles[role.name] = role
        for payload in self._catalog_store.load_data_sources():
            secret_payload = payload.pop("_secret_payload", {})
            data_source = _data_source_from_payload(payload)
            self._data_sources[data_source.name] = data_source
            self._vault_secrets[data_source.vault_secret_ref] = {
                "username": str(secret_payload.get("username", "")),
                "password": str(secret_payload.get("password", "")),
            }

    def _invalidate_query_cache_for_user(self, user_id: str) -> None:
        from orchestration.cache.query_result_cache import get_query_result_cache

        get_query_result_cache().invalidate_user_entries(user_id)

    def create_role(
        self,
        *,
        name: str,
        schema_allowlist: list[str],
        actor: str,
        description: str | None = None,
        data_source_names: list[str] | None = None,
        metric_allowlist: list[str] | None = None,
    ) -> RoleDefinition:
        normalized = name.strip()
        if not normalized:
            raise ValueError("role name is required")
        if normalized in self._roles:
            raise ValueError("role already exists")
        normalized_schemas = _normalize_schema_allowlist(schema_allowlist)
        if not normalized_schemas:
            raise ValueError("schema_allowlist must not be empty")
        now = datetime.now(UTC)
        role = RoleDefinition(
            name=normalized,
            schema_allowlist=normalized_schemas,
            created_by=actor,
            created_at=now,
            updated_at=now,
            description=description.strip() if description else None,
            data_source_names=sorted({item.strip() for item in data_source_names or [] if item.strip()}),
            metric_allowlist=sorted({item.strip() for item in metric_allowlist or [] if item.strip()}),
        )
        self._roles[normalized] = role
        self._persist_role(role)
        return role

    def list_roles(self) -> list[RoleDefinition]:
        return sorted(self._roles.values(), key=lambda role: role.name)

    def create_user(
        self,
        *,
        user_id: str,
        email: str,
        department: str,
        roles: list[str],
        ldap_groups: list[str],
    ) -> UserAccount:
        normalized_user_id = user_id.strip()
        if not normalized_user_id:
            raise ValueError("user_id is required")
        if normalized_user_id in self._users and not self._users[normalized_user_id].is_deleted:
            raise ValueError("user already exists")
        self._validate_roles(roles)
        now = datetime.now(UTC)
        user = UserAccount(
            user_id=normalized_user_id,
            email=email.strip(),
            department=department.strip(),
            roles=sorted(set(role.strip() for role in roles if role.strip())),
            ldap_groups=sorted(set(group.strip() for group in ldap_groups if group.strip())),
            created_at=now,
            updated_at=now,
        )
        self._users[normalized_user_id] = user
        return user

    def list_users(self, *, include_deleted: bool = False) -> list[UserAccount]:
        users = self._users.values()
        if not include_deleted:
            users = [user for user in users if not user.is_deleted]
        return sorted(users, key=lambda user: user.user_id)

    def get_user(self, user_id: str) -> UserAccount | None:
        return self._users.get(user_id)

    def update_user(
        self,
        user_id: str,
        *,
        email: str | None = None,
        department: str | None = None,
        roles: list[str] | None = None,
        ldap_groups: list[str] | None = None,
    ) -> UserAccount:
        user = self._require_user(user_id)
        if roles is not None:
            self._validate_roles(roles)
            user.roles = sorted(set(role.strip() for role in roles if role.strip()))
        if ldap_groups is not None:
            user.ldap_groups = sorted(set(group.strip() for group in ldap_groups if group.strip()))
        if email is not None:
            user.email = email.strip()
        if department is not None:
            user.department = department.strip()
        user.updated_at = datetime.now(UTC)
        user.is_deleted = False
        self._invalidate_query_cache_for_user(user.user_id)
        return user

    def soft_delete_user(self, user_id: str) -> UserAccount:
        user = self._require_user(user_id)
        now = datetime.now(UTC)
        user.is_deleted = True
        user.deleted_at = now
        user.retention_until = now + timedelta(days=_RETENTION_DAYS)
        user.sessions_revoked_at = now
        user.updated_at = now
        self._invalidate_query_cache_for_user(user.user_id)
        return user

    def preview_bulk_import(self, csv_content: str) -> dict[str, object]:
        rows = self._parse_csv(csv_content)
        valid_rows: list[dict[str, object]] = []
        errors: list[dict[str, object]] = []
        for index, row in enumerate(rows, start=2):
            row_errors = self._validate_csv_row(row)
            if row_errors:
                errors.append({"row": index, "errors": row_errors, "data": row})
                continue
            valid_rows.append(row)
        return {
            "valid_rows": len(valid_rows),
            "invalid_rows": len(errors),
            "errors": errors,
            "preview": valid_rows[:20],
        }

    def commit_bulk_import(self, csv_content: str) -> list[UserAccount]:
        preview = self.preview_bulk_import(csv_content)
        if preview["invalid_rows"]:
            raise ValueError("bulk import has validation errors")

        imported: list[UserAccount] = []
        for row in self._parse_csv(csv_content):
            roles = _split_csv_multi_value(row.get("roles", ""))
            ldap_groups = _split_csv_multi_value(row.get("ldap_groups", ""))
            user = self.get_user(row["user_id"])
            if user is None:
                imported.append(
                    self.create_user(
                        user_id=row["user_id"],
                        email=row["email"],
                        department=row["department"],
                        roles=roles,
                        ldap_groups=ldap_groups,
                    )
                )
            else:
                imported.append(
                    self.update_user(
                        row["user_id"],
                        email=row["email"],
                        department=row["department"],
                        roles=roles,
                        ldap_groups=ldap_groups,
                    )
                )
        return imported

    def run_ldap_sync(
        self,
        *,
        updates: list[dict[str, object]],
        interval_minutes: int | None = None,
    ) -> LdapSyncStatus:
        if interval_minutes is not None and interval_minutes > 0:
            self._sync_status.interval_minutes = interval_minutes
        synced = 0
        for update in updates:
            user = self._users.get(str(update["user_id"]))
            if user is None:
                continue
            roles = update.get("roles")
            if isinstance(roles, list):
                self._validate_roles([str(role) for role in roles])
            self.update_user(
                user.user_id,
                department=str(update.get("department", user.department)),
                roles=[str(role) for role in roles] if isinstance(roles, list) else user.roles,
                ldap_groups=[str(group) for group in update.get("ldap_groups", user.ldap_groups)]
                if isinstance(update.get("ldap_groups"), list)
                else user.ldap_groups,
            )
            synced += 1
        self._sync_status.last_run_at = datetime.now(UTC)
        self._sync_status.synced_users = synced
        self._sync_status.last_result = "success"
        return self._sync_status

    def get_sync_status(self) -> LdapSyncStatus:
        return self._sync_status

    def resolve_runtime_principal(self, principal: JWTClaims) -> JWTClaims:
        managed_user = self._users.get(principal.sub)
        if managed_user is None:
            return principal
        if managed_user.is_deleted:
            raise PermissionError("User account is soft-deleted")
        return JWTClaims(
            sub=principal.sub,
            email=managed_user.email or principal.email,
            department=managed_user.department or principal.department,
            roles=tuple(managed_user.roles) if managed_user.roles else principal.roles,
            clearance=principal.clearance,
            raw=principal.raw,
            region=principal.region,
            approval_authority=principal.approval_authority,
        )

    def create_data_source(
        self,
        *,
        name: str,
        host: str,
        port: int,
        service_name: str,
        username: str,
        password: str,
        schema_allowlist: list[str],
        query_timeout_seconds: int = _DEFAULT_QUERY_TIMEOUT_SECONDS,
        row_limit: int = _DEFAULT_ROW_LIMIT,
        actor: str,
        description: str | None = None,
    ) -> DataSourceConfig:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("data source name is required")
        if normalized_name in self._data_sources:
            raise ValueError("data source already exists")
        normalized_schemas = _normalize_schema_allowlist(schema_allowlist)
        if not normalized_schemas:
            raise ValueError("schema_allowlist must not be empty")
        now = datetime.now(UTC)
        vault_ref = f"vault://oracle/{normalized_name}"
        probe = self._probe_oracle_connection(
            host=host.strip(),
            port=port,
            service_name=service_name.strip(),
            username=username.strip(),
            password=password,
            timeout_seconds=_DEFAULT_CONNECTION_TIMEOUT_SECONDS,
        )
        status = "VERIFIED" if probe["ok"] else "UNVERIFIED"
        warning_message = None if probe["ok"] else "Kết nối thất bại - kiểm tra thông tin trước khi dùng"
        available_schemas = probe["available_schemas"]
        if probe["ok"]:
            missing_schemas = sorted(set(normalized_schemas) - set(available_schemas))
            if missing_schemas:
                raise ValueError(f"schema allowlist not found in Oracle: {missing_schemas}")
        config = DataSourceConfig(
            name=normalized_name,
            host=host.strip(),
            port=port,
            service_name=service_name.strip(),
            schema_allowlist=normalized_schemas,
            query_timeout_seconds=query_timeout_seconds,
            row_limit=row_limit,
            status=status,
            created_by=actor,
            created_at=now,
            updated_at=now,
            vault_secret_ref=vault_ref,
            description=description.strip() if description else None,
            warning_message=warning_message,
            last_test_at=now,
            available_schemas=available_schemas,
        )
        self._data_sources[normalized_name] = config
        self._vault_secrets[vault_ref] = {"username": username.strip(), "password": password}
        self._persist_data_source(config, username=username.strip(), password=password)
        return config

    def update_data_source(
        self,
        name: str,
        *,
        host: str | None = None,
        port: int | None = None,
        service_name: str | None = None,
        username: str | None = None,
        password: str | None = None,
        schema_allowlist: list[str] | None = None,
        query_timeout_seconds: int | None = None,
        row_limit: int | None = None,
        actor: str,
        description: str | None = None,
    ) -> tuple[DataSourceConfig, dict[str, dict[str, object]]]:
        config = self.get_data_source(name)
        if config is None:
            raise KeyError(name)
        changes: dict[str, dict[str, object]] = {}
        current_secret = self._vault_secrets[config.vault_secret_ref]
        next_host = host.strip() if host is not None else config.host
        next_port = port if port is not None else config.port
        next_service_name = service_name.strip() if service_name is not None else config.service_name
        next_username = username.strip() if username is not None else current_secret["username"]
        next_password = password if password is not None else current_secret["password"]
        next_schemas = (
            _normalize_schema_allowlist(schema_allowlist) if schema_allowlist is not None else config.schema_allowlist
        )
        probe = self._probe_oracle_connection(
            host=next_host,
            port=next_port,
            service_name=next_service_name,
            username=next_username,
            password=next_password,
            timeout_seconds=config.connection_timeout_seconds,
        )
        if probe["ok"]:
            missing_schemas = sorted(set(next_schemas) - set(probe["available_schemas"]))
            if missing_schemas:
                raise ValueError(f"schema allowlist not found in Oracle: {missing_schemas}")
        for field_name, old_value, new_value in (
            ("description", config.description, description.strip() if description else config.description),
            ("host", config.host, next_host),
            ("port", config.port, next_port),
            ("service_name", config.service_name, next_service_name),
            ("schema_allowlist", config.schema_allowlist, next_schemas),
            (
                "query_timeout_seconds",
                config.query_timeout_seconds,
                query_timeout_seconds or config.query_timeout_seconds,
            ),
            ("row_limit", config.row_limit, row_limit or config.row_limit),
        ):
            if old_value != new_value:
                changes[field_name] = {
                    "previous_value": old_value,
                    "new_value": new_value,
                    "changed_by": actor,
                }
        if description is not None:
            config.description = description.strip() if description else None
        if host is not None:
            config.host = next_host
        if port is not None:
            config.port = next_port
        if service_name is not None:
            config.service_name = next_service_name
        if schema_allowlist is not None:
            config.schema_allowlist = next_schemas
        if query_timeout_seconds is not None:
            config.query_timeout_seconds = query_timeout_seconds
        if row_limit is not None:
            config.row_limit = row_limit
        config.available_schemas = probe["available_schemas"]
        config.status = "VERIFIED" if probe["ok"] else "UNVERIFIED"
        config.warning_message = None if probe["ok"] else "Kết nối thất bại - kiểm tra thông tin trước khi dùng"
        config.last_test_at = datetime.now(UTC)
        config.updated_at = config.last_test_at
        if username is not None or password is not None:
            self._vault_secrets[config.vault_secret_ref] = {"username": next_username, "password": next_password}
        self._persist_data_source(config, username=next_username, password=next_password)
        return config, changes

    def list_data_sources(self) -> list[DataSourceConfig]:
        return sorted(self._data_sources.values(), key=lambda item: item.name)

    def get_data_source(self, name: str) -> DataSourceConfig | None:
        return self._data_sources.get(name)

    def get_query_execution_settings(self, name: str) -> dict[str, object]:
        config = self.get_data_source(name)
        if config is None:
            raise KeyError(name)
        return {
            "data_source": name,
            "row_limit": config.row_limit,
            "query_timeout_seconds": config.query_timeout_seconds,
            "status": config.status,
            "warning": config.query_warning,
        }

    def resolve_query_data_source(self, principal: JWTClaims) -> dict[str, object] | None:
        if not self._data_sources:
            return None
        principal_schemas: set[str] = set()
        preferred_data_sources: list[str] = []
        for role_name in principal.roles:
            role = self._roles.get(role_name)
            if role is not None:
                principal_schemas.update(role.schema_allowlist)
                preferred_data_sources.extend(role.data_source_names)
        seen: set[str] = set()
        ordered_data_sources: list[DataSourceConfig] = []
        for name in preferred_data_sources:
            config = self.get_data_source(name)
            if config is not None and config.name not in seen:
                ordered_data_sources.append(config)
                seen.add(config.name)
        for config in self.list_data_sources():
            if config.name in seen:
                continue
            ordered_data_sources.append(config)
        for config in ordered_data_sources:
            if principal_schemas and principal_schemas.intersection(config.schema_allowlist):
                return self.get_query_execution_settings(config.name)
        return None

    def allowed_metrics_for_principal(self, principal: JWTClaims) -> set[str]:
        allowed_metrics: set[str] = set()
        scoped = False
        for role_name in principal.roles:
            role = self._roles.get(role_name)
            if role is None:
                continue
            if role.metric_allowlist:
                scoped = True
                allowed_metrics.update(metric.casefold() for metric in role.metric_allowlist)
        return allowed_metrics if scoped else set()

    def import_role_mappings(self, *, roles: list[dict[str, object]], actor: str) -> list[RoleDefinition]:
        imported: list[RoleDefinition] = []
        for role in roles:
            imported.append(
                self.create_role(
                    name=str(role["name"]),
                    schema_allowlist=[str(item) for item in role.get("schema_allowlist", [])],
                    actor=actor,
                    description=str(role["description"]).strip() if role.get("description") else None,
                    data_source_names=[str(item) for item in role.get("data_source_names", [])],
                    metric_allowlist=[str(item) for item in role.get("metric_allowlist", [])],
                )
            )
        return imported

    def import_data_sources(self, *, data_sources: list[dict[str, object]], actor: str) -> list[DataSourceConfig]:
        imported: list[DataSourceConfig] = []
        for item in data_sources:
            imported.append(
                self.create_data_source(
                    name=str(item["name"]),
                    host=str(item["host"]),
                    port=int(item["port"]),
                    service_name=str(item["service_name"]),
                    username=str(item["username"]),
                    password=str(item["password"]),
                    schema_allowlist=[str(schema) for schema in item.get("schema_allowlist", [])],
                    query_timeout_seconds=int(item.get("query_timeout_seconds", _DEFAULT_QUERY_TIMEOUT_SECONDS)),
                    row_limit=int(item.get("row_limit", _DEFAULT_ROW_LIMIT)),
                    actor=actor,
                    description=str(item["description"]).strip() if item.get("description") else None,
                )
            )
        return imported

    def export_audit_records_csv(self, records: list[dict[str, object]]) -> str:
        output = io.StringIO()
        fieldnames = [
            "request_id",
            "timestamp",
            "user_id",
            "department_id",
            "intent_type",
            "data_sources",
            "policy_decision",
            "rows_returned",
            "status",
            "denial_reason",
            "cerbos_rule",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "request_id": record["request_id"],
                    "timestamp": record["timestamp"],
                    "user_id": record["user_id"],
                    "department_id": record["department_id"],
                    "intent_type": record["intent_type"],
                    "data_sources": "|".join(record["data_sources"]),
                    "policy_decision": record["policy_decision"],
                    "rows_returned": record["rows_returned"],
                    "status": record["status"],
                    "denial_reason": record.get("denial_reason"),
                    "cerbos_rule": record.get("cerbos_rule"),
                }
            )
        return output.getvalue()

    def set_health_snapshot(
        self,
        *,
        p50_latency_ms: dict[str, int],
        p95_latency_ms: dict[str, int],
        cache_hit_ratio: float,
        error_rate_percent: float,
        token_cost_per_day: float,
        active_oracle_connections: int,
        weaviate_index_status: str,
        grafana_embed_url: str | None = None,
        time_range: str = "last_30_minutes",
        refreshed_at: datetime | None = None,
    ) -> HealthSnapshot:
        self._health_snapshot = HealthSnapshot(
            p50_latency_ms=p50_latency_ms,
            p95_latency_ms=p95_latency_ms,
            cache_hit_ratio=cache_hit_ratio,
            error_rate_percent=error_rate_percent,
            token_cost_per_day=token_cost_per_day,
            active_oracle_connections=active_oracle_connections,
            weaviate_index_status=weaviate_index_status,
            refreshed_at=refreshed_at or datetime.now(UTC),
            grafana_embed_url=grafana_embed_url or self._health_snapshot.grafana_embed_url,
            time_range=time_range,
        )
        self._refresh_alerts()
        return self._health_snapshot

    def upsert_alert_setting(
        self,
        *,
        scope_type: str,
        scope_id: str,
        metric_name: str,
        threshold: float,
        actor: str,
    ) -> AlertSetting:
        if scope_type not in {"user", "department", "global"}:
            raise ValueError("scope_type must be one of: user, department, global")
        key = (scope_type, scope_id, metric_name)
        setting = AlertSetting(
            scope_type=scope_type,
            scope_id=scope_id,
            metric_name=metric_name,
            threshold=threshold,
            created_by=actor,
            updated_at=datetime.now(UTC),
        )
        self._alert_settings[key] = setting
        self._refresh_alerts()
        return setting

    def list_alert_settings(self) -> list[AlertSetting]:
        return sorted(
            self._alert_settings.values(),
            key=lambda item: (item.scope_type, item.scope_id, item.metric_name),
        )

    def get_health_dashboard(self, *, time_range: str = "last_30_minutes") -> dict[str, object]:
        snapshot = self._health_snapshot
        snapshot.time_range = time_range
        snapshot.historical_days = 7 if time_range == "last_7_days" else 1
        self._refresh_alerts()
        return snapshot.to_dict(self.list_active_alerts(), self.list_alert_settings())

    def list_active_alerts(self) -> list[HealthAlert]:
        return sorted(
            (alert for alert in self._alerts.values() if alert.status == "ACTIVE"),
            key=lambda item: item.triggered_at,
            reverse=True,
        )

    def acknowledge_alert(self, alert_id: str, *, actor: str) -> HealthAlert:
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise KeyError(alert_id)
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = datetime.now(UTC)
        alert.acknowledged_by = actor
        return alert

    def drain_pending_alert_audits(self) -> list[HealthAlert]:
        pending: list[HealthAlert] = []
        now = datetime.now(UTC)
        for alert in self._alerts.values():
            if alert.audit_logged_at is None:
                alert.audit_logged_at = now
                pending.append(alert)
        return sorted(pending, key=lambda item: item.triggered_at)

    def _refresh_alerts(self) -> None:
        threshold = self._resolve_threshold(metric_name="p95_latency_ms", scope_type="global", scope_id="default")
        for mode, current_value in self._health_snapshot.p95_latency_ms.items():
            alert_key = f"p95_latency_ms:{mode}"
            if current_value > threshold:
                existing = self._alerts.get(alert_key)
                if existing and existing.status == "ACTIVE":
                    existing.current_value = current_value
                    existing.threshold = threshold
                    continue
                self._alerts[alert_key] = HealthAlert(
                    alert_id=alert_key,
                    metric_name=f"p95_latency_ms.{mode}",
                    current_value=float(current_value),
                    threshold=threshold,
                    affected_service=mode,
                    triggered_at=self._health_snapshot.refreshed_at,
                )
            elif alert_key in self._alerts and self._alerts[alert_key].status == "ACTIVE":
                self._alerts[alert_key].status = "RESOLVED"

    def _resolve_threshold(self, *, metric_name: str, scope_type: str, scope_id: str) -> float:
        for key in ((scope_type, scope_id, metric_name), ("global", "default", metric_name)):
            setting = self._alert_settings.get(key)
            if setting is not None:
                return setting.threshold
        return float(_DEFAULT_LATENCY_THRESHOLD_MS)

    def _probe_oracle_connection(
        self,
        *,
        host: str,
        port: int,
        service_name: str,
        username: str,
        password: str,
        timeout_seconds: int,
    ) -> dict[str, object]:
        del port, service_name, username, password, timeout_seconds
        if not host or "fail" in host.lower() or "bad" in host.lower():
            return {"ok": False, "available_schemas": []}
        discovered = sorted({schema for role in self._roles.values() for schema in role.schema_allowlist})
        if not discovered:
            discovered = ["FINANCE_ANALYTICS", "SALES_ANALYTICS", "HR_ANALYTICS"]
        return {"ok": True, "available_schemas": discovered}

    def _require_user(self, user_id: str) -> UserAccount:
        user = self._users.get(user_id)
        if user is None:
            raise KeyError(user_id)
        return user

    def _persist_role(self, role: RoleDefinition) -> None:
        if self._catalog_store is None:
            return
        self._catalog_store.upsert_role(_role_to_payload(role), updated_at=role.updated_at)

    def _persist_data_source(self, config: DataSourceConfig, *, username: str, password: str) -> None:
        if self._catalog_store is None:
            return
        self._catalog_store.upsert_data_source(
            _data_source_to_payload(config),
            username=username,
            password=password,
            updated_at=config.updated_at,
        )

    def _validate_roles(self, roles: list[str]) -> None:
        missing_roles = [role for role in roles if role.strip() and role.strip() not in self._roles]
        if missing_roles:
            raise ValueError(f"unknown roles: {sorted(set(missing_roles))}")

    @staticmethod
    def _parse_csv(csv_content: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(csv_content))
        return [{key: (value or "").strip() for key, value in row.items()} for row in reader]

    def _validate_csv_row(self, row: dict[str, str]) -> list[str]:
        errors: list[str] = []
        if not row.get("user_id"):
            errors.append("user_id is required")
        if not row.get("email"):
            errors.append("email is required")
        if not row.get("department"):
            errors.append("department is required")
        roles = _split_csv_multi_value(row.get("roles", ""))
        missing_roles = [role for role in roles if role not in self._roles]
        if missing_roles:
            errors.append(f"unknown roles: {sorted(set(missing_roles))}")
        return errors


def _normalize_schema_allowlist(values: list[str]) -> list[str]:
    return sorted({value.strip().upper() for value in values if value.strip()})


def _split_csv_multi_value(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def _role_to_payload(role: RoleDefinition) -> dict[str, object]:
    return {
        "name": role.name,
        "schema_allowlist": list(role.schema_allowlist),
        "created_by": role.created_by,
        "created_at": role.created_at.isoformat(),
        "updated_at": role.updated_at.isoformat(),
        "description": role.description,
        "data_source_names": list(role.data_source_names),
        "metric_allowlist": list(role.metric_allowlist),
        "cerbos_policy_status": role.cerbos_policy_status,
        "data_source_config_status": role.data_source_config_status,
    }


def _role_from_payload(payload: dict[str, object]) -> RoleDefinition:
    return RoleDefinition(
        name=str(payload["name"]),
        schema_allowlist=[str(item) for item in payload.get("schema_allowlist", [])],
        created_by=str(payload["created_by"]),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        description=str(payload["description"]) if payload.get("description") else None,
        data_source_names=[str(item) for item in payload.get("data_source_names", [])],
        metric_allowlist=[str(item) for item in payload.get("metric_allowlist", [])],
        cerbos_policy_status=str(payload.get("cerbos_policy_status", "synced")),
        data_source_config_status=str(payload.get("data_source_config_status", "persisted")),
    )


def _data_source_to_payload(config: DataSourceConfig) -> dict[str, object]:
    return {
        "name": config.name,
        "description": config.description,
        "host": config.host,
        "port": config.port,
        "service_name": config.service_name,
        "schema_allowlist": list(config.schema_allowlist),
        "query_timeout_seconds": config.query_timeout_seconds,
        "row_limit": config.row_limit,
        "status": config.status,
        "created_by": config.created_by,
        "created_at": config.created_at.isoformat(),
        "updated_at": config.updated_at.isoformat(),
        "vault_secret_ref": config.vault_secret_ref,
        "warning_message": config.warning_message,
        "connection_timeout_seconds": config.connection_timeout_seconds,
        "last_test_at": config.last_test_at.isoformat() if config.last_test_at else None,
        "available_schemas": list(config.available_schemas),
    }


def _data_source_from_payload(payload: dict[str, object]) -> DataSourceConfig:
    return DataSourceConfig(
        name=str(payload["name"]),
        description=str(payload["description"]) if payload.get("description") else None,
        host=str(payload["host"]),
        port=int(payload["port"]),
        service_name=str(payload["service_name"]),
        schema_allowlist=[str(item) for item in payload.get("schema_allowlist", [])],
        query_timeout_seconds=int(payload["query_timeout_seconds"]),
        row_limit=int(payload["row_limit"]),
        status=str(payload["status"]),
        created_by=str(payload["created_by"]),
        created_at=_parse_datetime(payload["created_at"]),
        updated_at=_parse_datetime(payload["updated_at"]),
        vault_secret_ref=str(payload["vault_secret_ref"]),
        warning_message=str(payload["warning_message"]) if payload.get("warning_message") else None,
        connection_timeout_seconds=int(payload.get("connection_timeout_seconds", _DEFAULT_CONNECTION_TIMEOUT_SECONDS)),
        last_test_at=_parse_datetime(payload["last_test_at"]) if payload.get("last_test_at") else None,
        available_schemas=[str(item) for item in payload.get("available_schemas", [])],
    )


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    return datetime.fromisoformat(str(value)).astimezone(UTC)


_service = UserRoleManagementService(catalog_store=get_config_catalog_store())


def get_user_role_management_service() -> UserRoleManagementService:
    return _service


def reset_user_role_management_service() -> None:
    global _service
    _service = UserRoleManagementService(catalog_store=get_config_catalog_store())
