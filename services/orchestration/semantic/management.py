"""Semantic layer management service for Epic 5B.1."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import ndiff
from typing import Any
from uuid import uuid4

from orchestration.persistence.config_catalog_store import get_config_catalog_store
from orchestration.semantic.glossary import SEED_GLOSSARY


def _normalize_str_list(values: list[str] | None) -> list[str]:
    return [value.strip() for value in values or [] if value.strip()]


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
    security: dict[str, object] | None = None
    rollback_reason: str | None = None

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
            "security": self.security,
            "rollback_reason": self.rollback_reason,
        }


class SemanticLayerService:
    def __init__(self, *, catalog_store: Any | None = None) -> None:
        self._versions: dict[str, list[KpiDefinitionVersion]] = {}
        self._active_versions: dict[str, str] = {}
        self._catalog_store = catalog_store
        self._cache_invalidated_at = datetime.now(UTC)
        if not self._load_persisted_state():
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
        security: dict[str, object] | None = None,
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
            security=dict(security) if security else None,
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
            security=dict(target.security) if target.security else None,
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
        normalized_query = query.casefold()
        matches: list[dict[str, object]] = []
        for metric in self.list_metrics():
            terms = [str(metric["term"]).casefold(), *(alias.casefold() for alias in metric.get("aliases", []))]
            if any(term in normalized_query for term in terms):
                matches.append(metric)
        return matches

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
        security=dict(payload["security"]) if isinstance(payload.get("security"), dict) else None,
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
