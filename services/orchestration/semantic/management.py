"""Semantic layer management service for Epic 5B.1."""

from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import ndiff
from typing import Any
from uuid import uuid4

from embedding.client import BGE_MODEL_NAME, DIMS, _hash_embed

from aial_shared.auth.keycloak import JWTClaims
from orchestration.persistence.config_catalog_store import get_config_catalog_store
from orchestration.semantic.glossary import SEED_GLOSSARY
from orchestration.semantic.resolver import SemanticResolveDecision, SemanticResolver


def _normalize_str_list(values: list[str] | None) -> list[str]:
    return [value.strip() for value in values or [] if value.strip()]


def _stringify_retrieval_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key}: {_stringify_retrieval_value(item)}" for key, item in sorted(value.items()))
    if isinstance(value, list):
        return " ".join(_stringify_retrieval_value(item) for item in value)
    return str(value)


def _semantic_match_text(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value).casefold())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return " ".join(without_marks.replace("đ", "d").split())


@dataclass(frozen=True)
class KpiDefinitionVersion:
    version_id: str
    term: str
    definition: str
    formula: str
    owner: str
    freshness_rule: str
    changed_by: str
    timestamp: datetime
    previous_formula: str | None
    action: str
    aliases: list[str] = field(default_factory=list)
    aggregation: str | None = None
    grain: str | None = None
    unit: str | None = None
    dimensions: list[str] = field(default_factory=list)
    source: dict[str, object] | None = None
    joins: list[dict[str, str]] = field(default_factory=list)
    certified_filters: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    negative_examples: list[str] = field(default_factory=list)
    security: dict[str, object] | None = None
    cube_name: str | None = None
    measure_name: str | None = None
    time_dimension: str | None = None
    cube_dimensions: list[str] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)
    display_format: str | None = None
    semantic_runtime_status: str | None = None
    semantic_runtime_errors: list[str] = field(default_factory=list)
    last_runtime_synced_at: str | None = None
    rollback_reason: str | None = None

    @property
    def retrieval_text(self) -> str:
        parts = [
            f"Tên semantic: {self.term}",
            f"Từ đồng nghĩa: {', '.join(self.aliases)}",
            f"Định nghĩa: {self.definition}",
            f"Công thức: {self.formula}",
            f"Chủ sở hữu: {self.owner}",
            f"Độ tươi dữ liệu: {self.freshness_rule}",
            f"Kiểu tổng hợp: {self.aggregation or ''}",
            f"Hạt dữ liệu: {self.grain or ''}",
            f"Đơn vị: {self.unit or ''}",
            f"Chiều phân tích: {', '.join(self.dimensions)}",
            f"Nguồn dữ liệu: {_stringify_retrieval_value(self.source)}",
            f"Join: {_stringify_retrieval_value(self.joins)}",
            f"Examples: {' '.join(self.examples)}",
            f"Negative examples: {' '.join(self.negative_examples)}",
            f"Bộ lọc chuẩn: {', '.join(self.certified_filters)}",
            f"Bảo mật: {_stringify_retrieval_value(self.security)}",
        ]
        return " ".join(part for part in parts if part.strip())

    def to_dict(self) -> dict[str, object]:
        return {
            "version_id": self.version_id,
            "term": self.term,
            "definition": self.definition,
            "formula": self.formula,
            "owner": self.owner,
            "freshness_rule": self.freshness_rule,
            "changed_by": self.changed_by,
            "timestamp": self.timestamp.isoformat(),
            "previous_formula": self.previous_formula,
            "action": self.action,
            "aliases": self.aliases,
            "aggregation": self.aggregation,
            "grain": self.grain,
            "unit": self.unit,
            "dimensions": self.dimensions,
            "source": self.source,
            "joins": self.joins,
            "certified_filters": self.certified_filters,
            "examples": self.examples,
            "negative_examples": self.negative_examples,
            "security": self.security,
            "cube_name": self.cube_name,
            "measure_name": self.measure_name,
            "time_dimension": self.time_dimension,
            "cube_dimensions": self.cube_dimensions,
            "primary_key": self.primary_key,
            "display_format": self.display_format,
            "semantic_runtime_status": self.semantic_runtime_status,
            "semantic_runtime_errors": self.semantic_runtime_errors,
            "last_runtime_synced_at": self.last_runtime_synced_at,
            "rollback_reason": self.rollback_reason,
            "retrieval_text": self.retrieval_text,
        }

    @property
    def is_deleted(self) -> bool:
        return self.action == "delete"


class SemanticLayerService:
    def __init__(self, *, catalog_store: Any | None = None) -> None:
        self._versions: dict[str, list[KpiDefinitionVersion]] = {}
        self._active_versions: dict[str, str] = {}
        self._catalog_store = catalog_store
        self._cache_invalidated_at = datetime.now(UTC)
        self._resolver = SemanticResolver()
        if not self._load_persisted_state():
            if os.getenv("AIAL_SEED_SEMANTIC_GLOSSARY", "").strip().lower() in {"1", "true", "yes", "on"}:
                self._seed()

    def _seed(self) -> None:
        for entry in SEED_GLOSSARY:
            self._store_seed_entry(entry)

    def _store_seed_entry(self, entry: dict[str, object]) -> None:
        version = KpiDefinitionVersion(
            version_id=str(uuid4()),
            term=str(entry["term"]),
            definition=str(entry["definition"]),
            formula=str(entry["formula"]),
            owner=str(entry["owner"]),
            freshness_rule=str(entry["freshness_rule"]),
            changed_by="system-seed",
            timestamp=datetime.now(UTC),
            previous_formula=None,
            action="seed",
            aliases=_normalize_str_list(entry.get("aliases") if isinstance(entry.get("aliases"), list) else None),
            aggregation=str(entry["aggregation"]).strip() if entry.get("aggregation") else None,
            grain=str(entry["grain"]).strip() if entry.get("grain") else None,
            unit=str(entry["unit"]).strip() if entry.get("unit") else None,
            dimensions=_normalize_str_list(
                entry.get("dimensions") if isinstance(entry.get("dimensions"), list) else None
            ),
            source=dict(entry["source"]) if isinstance(entry.get("source"), dict) else None,
            joins=[dict(join) for join in entry.get("joins", []) if isinstance(join, dict)],
            certified_filters=_normalize_str_list(
                entry.get("certified_filters") if isinstance(entry.get("certified_filters"), list) else None
            ),
            examples=_normalize_str_list(entry.get("examples") if isinstance(entry.get("examples"), list) else None),
            negative_examples=_normalize_str_list(
                entry.get("negative_examples") if isinstance(entry.get("negative_examples"), list) else None
            ),
            security=dict(entry["security"]) if isinstance(entry.get("security"), dict) else None,
        )
        normalized_term = version.term.casefold()
        self._versions.setdefault(normalized_term, []).append(version)
        self._active_versions[normalized_term] = version.version_id
        self._persist_version(version, normalized_term)

    def _load_persisted_state(self) -> bool:
        if self._catalog_store is None:
            return False
        versions, active_versions = self._catalog_store.load_semantic_state()
        if not versions:
            return False
        for payload in versions:
            version = _version_from_payload(payload)
            normalized_term = version.term.casefold()
            self._versions.setdefault(normalized_term, []).append(version)
        self._active_versions = {key: value for key, value in active_versions.items()}
        self._cache_invalidated_at = max(
            version.timestamp for payload in self._versions.values() for version in payload
        )
        return True

    def list_metrics(self) -> list[dict[str, object]]:
        metrics: list[dict[str, object]] = []
        for normalized_term in sorted(self._versions):
            active = self.get_metric(normalized_term)
            if active is None:
                continue
            metrics.append(
                {
                    **active.to_dict(),
                    "active_version_id": active.version_id,
                    "version_count": len(self._versions[normalized_term]),
                    "cache_invalidated_at": self._cache_invalidated_at.isoformat(),
                }
            )
        return metrics

    def get_metric(self, term: str) -> KpiDefinitionVersion | None:
        normalized = term.strip().casefold()
        versions = self._versions.get(normalized)
        if not versions:
            return None
        active_id = self._active_versions[normalized]
        for version in versions:
            if version.version_id == active_id:
                if version.is_deleted:
                    return None
                return version
        return None

    def get_versions(self, term: str) -> list[KpiDefinitionVersion]:
        return list(self._versions.get(term.strip().casefold(), []))

    def publish_metric(
        self,
        *,
        term: str,
        definition: str,
        formula: str,
        owner: str,
        freshness_rule: str,
        changed_by: str,
        aliases: list[str] | None = None,
        aggregation: str | None = None,
        grain: str | None = None,
        unit: str | None = None,
        dimensions: list[str] | None = None,
        source: dict[str, object] | None = None,
        joins: list[dict[str, str]] | None = None,
        certified_filters: list[str] | None = None,
        examples: list[str] | None = None,
        negative_examples: list[str] | None = None,
        security: dict[str, object] | None = None,
        cube_name: str | None = None,
        measure_name: str | None = None,
        time_dimension: str | None = None,
        cube_dimensions: list[str] | None = None,
        primary_key: list[str] | None = None,
        display_format: str | None = None,
        semantic_runtime_status: str | None = None,
        semantic_runtime_errors: list[str] | None = None,
        last_runtime_synced_at: str | None = None,
    ) -> KpiDefinitionVersion:
        normalized = term.strip().casefold()
        previous = self.get_metric(term)
        version = KpiDefinitionVersion(
            version_id=str(uuid4()),
            term=term.strip(),
            definition=definition.strip(),
            formula=formula.strip(),
            owner=owner.strip(),
            freshness_rule=freshness_rule.strip(),
            changed_by=changed_by,
            timestamp=datetime.now(UTC),
            previous_formula=previous.formula if previous else None,
            action="publish",
            aliases=_normalize_str_list(aliases),
            aggregation=aggregation.strip() if aggregation else None,
            grain=grain.strip() if grain else None,
            unit=unit.strip() if unit else None,
            dimensions=_normalize_str_list(dimensions),
            source=dict(source) if source else None,
            joins=[dict(join) for join in joins or []],
            certified_filters=_normalize_str_list(certified_filters),
            examples=_normalize_str_list(examples),
            negative_examples=_normalize_str_list(negative_examples),
            security=dict(security) if security else None,
            cube_name=cube_name.strip() if cube_name else None,
            measure_name=measure_name.strip() if measure_name else None,
            time_dimension=time_dimension.strip() if time_dimension else None,
            cube_dimensions=_normalize_str_list(cube_dimensions),
            primary_key=_normalize_str_list(primary_key),
            display_format=display_format.strip() if display_format else None,
            semantic_runtime_status=semantic_runtime_status.strip() if semantic_runtime_status else None,
            semantic_runtime_errors=_normalize_str_list(semantic_runtime_errors),
            last_runtime_synced_at=last_runtime_synced_at,
        )
        self._versions.setdefault(normalized, []).append(version)
        self._active_versions[normalized] = version.version_id
        self._cache_invalidated_at = datetime.now(UTC)
        self._persist_version(version, normalized)
        return version

    def rollback_metric(
        self,
        *,
        term: str,
        target_version_id: str,
        changed_by: str,
        reason: str | None = None,
    ) -> KpiDefinitionVersion:
        current = self.get_metric(term)
        target = next((version for version in self.get_versions(term) if version.version_id == target_version_id), None)
        if target is None:
            raise KeyError(target_version_id)
        version = KpiDefinitionVersion(
            version_id=str(uuid4()),
            term=target.term,
            definition=target.definition,
            formula=target.formula,
            owner=target.owner,
            freshness_rule=target.freshness_rule,
            changed_by=changed_by,
            timestamp=datetime.now(UTC),
            previous_formula=current.formula if current else None,
            action="rollback",
            aliases=list(target.aliases),
            aggregation=target.aggregation,
            grain=target.grain,
            unit=target.unit,
            dimensions=list(target.dimensions),
            source=dict(target.source) if target.source else None,
            joins=[dict(join) for join in target.joins],
            certified_filters=list(target.certified_filters),
            examples=list(target.examples),
            negative_examples=list(target.negative_examples),
            security=dict(target.security) if target.security else None,
            cube_name=target.cube_name,
            measure_name=target.measure_name,
            time_dimension=target.time_dimension,
            cube_dimensions=list(target.cube_dimensions),
            primary_key=list(target.primary_key),
            display_format=target.display_format,
            semantic_runtime_status=target.semantic_runtime_status,
            semantic_runtime_errors=list(target.semantic_runtime_errors),
            last_runtime_synced_at=target.last_runtime_synced_at,
            rollback_reason=reason.strip() if reason else None,
        )
        normalized = term.strip().casefold()
        self._versions.setdefault(normalized, []).append(version)
        self._active_versions[normalized] = version.version_id
        self._cache_invalidated_at = datetime.now(UTC)
        self._persist_version(version, normalized)
        return version

    def delete_metric(self, *, term: str, changed_by: str, reason: str | None = None) -> KpiDefinitionVersion:
        current = self.get_metric(term)
        if current is None:
            raise KeyError(term)
        version = KpiDefinitionVersion(
            version_id=str(uuid4()),
            term=current.term,
            definition=current.definition,
            formula=current.formula,
            owner=current.owner,
            freshness_rule=current.freshness_rule,
            changed_by=changed_by,
            timestamp=datetime.now(UTC),
            previous_formula=current.formula,
            action="delete",
            aliases=list(current.aliases),
            aggregation=current.aggregation,
            grain=current.grain,
            unit=current.unit,
            dimensions=list(current.dimensions),
            source=dict(current.source) if current.source else None,
            joins=[dict(join) for join in current.joins],
            certified_filters=list(current.certified_filters),
            examples=list(current.examples),
            negative_examples=list(current.negative_examples),
            security=dict(current.security) if current.security else None,
            cube_name=current.cube_name,
            measure_name=current.measure_name,
            time_dimension=current.time_dimension,
            cube_dimensions=list(current.cube_dimensions),
            primary_key=list(current.primary_key),
            display_format=current.display_format,
            semantic_runtime_status=current.semantic_runtime_status,
            semantic_runtime_errors=list(current.semantic_runtime_errors),
            last_runtime_synced_at=current.last_runtime_synced_at,
            rollback_reason=reason.strip() if reason else None,
        )
        normalized = term.strip().casefold()
        self._versions.setdefault(normalized, []).append(version)
        self._active_versions[normalized] = version.version_id
        self._cache_invalidated_at = datetime.now(UTC)
        self._persist_version(version, normalized)
        return version

    def diff_versions(self, *, term: str, left_version_id: str, right_version_id: str) -> dict[str, object]:
        versions = {version.version_id: version for version in self.get_versions(term)}
        left = versions.get(left_version_id)
        right = versions.get(right_version_id)
        if left is None or right is None:
            raise KeyError("version not found")
        diff_rows: list[dict[str, str]] = []
        for token in ndiff(left.formula.split(), right.formula.split()):
            if token.startswith("+ "):
                diff_rows.append({"kind": "added", "value": token[2:]})
            elif token.startswith("- "):
                diff_rows.append({"kind": "removed", "value": token[2:]})
            elif token.startswith("  "):
                diff_rows.append({"kind": "unchanged", "value": token[2:]})
        return {
            "term": left.term,
            "left": left.to_dict(),
            "right": right.to_dict(),
            "diff": diff_rows,
        }

    def match_query(self, query: str) -> list[dict[str, object]]:
        normalized_query = _semantic_match_text(query)
        matches: list[dict[str, object]] = []
        for metric in self.list_metrics():
            terms = [
                _semantic_match_text(metric["term"]),
                *(_semantic_match_text(alias) for alias in metric.get("aliases", [])),
            ]
            if any(term in normalized_query for term in terms):
                matches.append(metric)
        return matches

    def resolve_query(
        self,
        *,
        query: str,
        principal: JWTClaims | None = None,
        allowed_terms: set[str] | None = None,
        top_k: int = 5,
    ) -> SemanticResolveDecision:
        return self._resolver.resolve(
            query=query,
            metrics=self.list_metrics(),
            principal=principal,
            allowed_terms=allowed_terms,
            top_k=top_k,
        )

    @property
    def cache_invalidated_at(self) -> datetime:
        return self._cache_invalidated_at

    def _persist_version(self, version: KpiDefinitionVersion, normalized_term: str) -> None:
        if self._catalog_store is None:
            return
        self._catalog_store.append_semantic_version(
            version.to_dict(),
            term_normalized=normalized_term,
            active_version_id=version.version_id,
            created_at=version.timestamp,
        )
        if hasattr(self._catalog_store, "upsert_semantic_embedding"):
            self._catalog_store.upsert_semantic_embedding(
                {
                    "version_id": version.version_id,
                    "term_normalized": normalized_term,
                    "retrieval_text": version.retrieval_text,
                    "embedding_model": BGE_MODEL_NAME,
                    "embedding_dimensions": DIMS,
                    "vector": _hash_embed(_semantic_match_text(version.retrieval_text), dims=DIMS),
                },
                updated_at=version.timestamp,
            )


def _version_from_payload(payload: dict[str, object]) -> KpiDefinitionVersion:
    return KpiDefinitionVersion(
        version_id=str(payload["version_id"]),
        term=str(payload["term"]),
        definition=str(payload["definition"]),
        formula=str(payload["formula"]),
        owner=str(payload["owner"]),
        freshness_rule=str(payload["freshness_rule"]),
        changed_by=str(payload["changed_by"]),
        timestamp=_parse_datetime(payload["timestamp"]),
        previous_formula=str(payload["previous_formula"]) if payload.get("previous_formula") else None,
        action=str(payload["action"]),
        aliases=_normalize_str_list(payload.get("aliases") if isinstance(payload.get("aliases"), list) else None),
        aggregation=str(payload["aggregation"]).strip() if payload.get("aggregation") else None,
        grain=str(payload["grain"]).strip() if payload.get("grain") else None,
        unit=str(payload["unit"]).strip() if payload.get("unit") else None,
        dimensions=_normalize_str_list(
            payload.get("dimensions") if isinstance(payload.get("dimensions"), list) else None
        ),
        source=dict(payload["source"]) if isinstance(payload.get("source"), dict) else None,
        joins=[dict(join) for join in payload.get("joins", []) if isinstance(join, dict)],
        certified_filters=_normalize_str_list(
            payload.get("certified_filters") if isinstance(payload.get("certified_filters"), list) else None
        ),
        examples=_normalize_str_list(payload.get("examples") if isinstance(payload.get("examples"), list) else None),
        negative_examples=_normalize_str_list(
            payload.get("negative_examples") if isinstance(payload.get("negative_examples"), list) else None
        ),
        security=dict(payload["security"]) if isinstance(payload.get("security"), dict) else None,
        cube_name=str(payload["cube_name"]).strip() if payload.get("cube_name") else None,
        measure_name=str(payload["measure_name"]).strip() if payload.get("measure_name") else None,
        time_dimension=str(payload["time_dimension"]).strip() if payload.get("time_dimension") else None,
        cube_dimensions=_normalize_str_list(
            payload.get("cube_dimensions") if isinstance(payload.get("cube_dimensions"), list) else None
        ),
        primary_key=_normalize_str_list(
            payload.get("primary_key") if isinstance(payload.get("primary_key"), list) else None
        ),
        display_format=str(payload["display_format"]).strip() if payload.get("display_format") else None,
        semantic_runtime_status=(
            str(payload["semantic_runtime_status"]).strip() if payload.get("semantic_runtime_status") else None
        ),
        semantic_runtime_errors=_normalize_str_list(
            payload.get("semantic_runtime_errors")
            if isinstance(payload.get("semantic_runtime_errors"), list)
            else None
        ),
        last_runtime_synced_at=(
            str(payload["last_runtime_synced_at"]) if payload.get("last_runtime_synced_at") else None
        ),
        rollback_reason=str(payload["rollback_reason"]) if payload.get("rollback_reason") else None,
    )


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    return datetime.fromisoformat(str(value)).astimezone(UTC)


_service = SemanticLayerService(catalog_store=get_config_catalog_store())


def get_semantic_layer_service() -> SemanticLayerService:
    return _service


def reset_semantic_layer_service() -> None:
    global _service
    _service = SemanticLayerService(catalog_store=get_config_catalog_store())
