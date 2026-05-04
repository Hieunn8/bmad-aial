"""PostgreSQL persistence for config catalog state."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on", "postgres"}


class ConfigCatalogStore:
    """Persist config catalog records to PostgreSQL JSONB tables."""

    def __init__(self, dsn: str, *, schema: str = "public") -> None:
        self._dsn = dsn
        self._schema = schema.strip() or "public"
        self._validated_schema = self._validate_identifier(self._schema)
        self._schema_ready = False

    @classmethod
    def from_env(cls) -> ConfigCatalogStore | None:
        mode = os.getenv("AIAL_CONFIG_CATALOG_PERSISTENCE", "").strip()
        if mode and not _is_enabled(mode):
            return None
        dsn = os.getenv("DATABASE_URL", "").strip()
        if not dsn:
            return None
        schema = os.getenv("AIAL_CONFIG_CATALOG_SCHEMA", "public")
        return cls(dsn, schema=schema)

    @staticmethod
    def _validate_identifier(value: str) -> str:
        if not _IDENTIFIER_RE.fullmatch(value):
            raise ValueError(f"invalid SQL identifier: {value}")
        return value

    def _connect(self) -> Any:
        import psycopg

        return psycopg.connect(self._dsn)

    def _qualified(self, table: str) -> str:
        validated = self._validate_identifier(table)
        return f"{self._validated_schema}.{validated}"

    def ensure_schema(self) -> None:
        if self._schema_ready:
            return
        schema_name = self._validated_schema
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qualified("catalog_roles")} (
                        name TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qualified("catalog_data_sources")} (
                        name TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        secret_payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qualified("semantic_metric_versions")} (
                        version_id TEXT PRIMARY KEY,
                        term_normalized TEXT NOT NULL,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self._qualified("semantic_metric_heads")} (
                        term_normalized TEXT PRIMARY KEY,
                        active_version_id TEXT NOT NULL
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_semantic_metric_versions_term
                    ON {self._qualified("semantic_metric_versions")} (term_normalized, created_at)
                    """
                )
            conn.commit()
        self._schema_ready = True

    def load_roles(self) -> list[dict[str, object]]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT payload FROM {self._qualified('catalog_roles')} ORDER BY name")
                rows = cur.fetchall()
        return [dict(row[0]) for row in rows]

    def upsert_role(self, payload: dict[str, object], *, updated_at: datetime) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified("catalog_roles")} (name, payload, updated_at)
                    VALUES (%s, %s::jsonb, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        str(payload["name"]),
                        json.dumps(payload),
                        updated_at,
                    ),
                )
            conn.commit()

    def load_data_sources(self) -> list[dict[str, object]]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT payload, secret_payload FROM {self._qualified('catalog_data_sources')} ORDER BY name"
                )
                rows = cur.fetchall()
        items: list[dict[str, object]] = []
        for payload, secret_payload in rows:
            item = dict(payload)
            item["_secret_payload"] = dict(secret_payload)
            items.append(item)
        return items

    def upsert_data_source(
        self,
        payload: dict[str, object],
        *,
        username: str,
        password: str,
        updated_at: datetime,
    ) -> None:
        self.ensure_schema()
        secret_payload = {"username": username, "password": password}
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified("catalog_data_sources")} (name, payload, secret_payload, updated_at)
                    VALUES (%s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        secret_payload = EXCLUDED.secret_payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (
                        str(payload["name"]),
                        json.dumps(payload),
                        json.dumps(secret_payload),
                        updated_at,
                    ),
                )
            conn.commit()

    def load_semantic_state(self) -> tuple[list[dict[str, object]], dict[str, str]]:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT payload
                    FROM {self._qualified("semantic_metric_versions")}
                    ORDER BY term_normalized, created_at, version_id
                    """
                )
                version_rows = cur.fetchall()
                cur.execute(
                    f"SELECT term_normalized, active_version_id FROM {self._qualified('semantic_metric_heads')}"
                )
                head_rows = cur.fetchall()
        versions = [dict(row[0]) for row in version_rows]
        heads = {str(term): str(active_version_id) for term, active_version_id in head_rows}
        return versions, heads

    def append_semantic_version(
        self,
        payload: dict[str, object],
        *,
        term_normalized: str,
        active_version_id: str,
        created_at: datetime,
    ) -> None:
        self.ensure_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified("semantic_metric_versions")}
                    (version_id, term_normalized, payload, created_at)
                    VALUES (%s, %s, %s::jsonb, %s)
                    ON CONFLICT (version_id) DO NOTHING
                    """,
                    (
                        str(payload["version_id"]),
                        term_normalized,
                        json.dumps(payload),
                        created_at,
                    ),
                )
                cur.execute(
                    f"""
                    INSERT INTO {self._qualified("semantic_metric_heads")} (term_normalized, active_version_id)
                    VALUES (%s, %s)
                    ON CONFLICT (term_normalized) DO UPDATE SET
                        active_version_id = EXCLUDED.active_version_id
                    """,
                    (term_normalized, active_version_id),
                )
            conn.commit()


def get_config_catalog_store() -> ConfigCatalogStore | None:
    try:
        return ConfigCatalogStore.from_env()
    except Exception:
        return None
