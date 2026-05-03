"""Semantic layer management service for Epic 5B.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from difflib import ndiff
from uuid import uuid4

from orchestration.semantic.glossary import SEED_GLOSSARY


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
            "rollback_reason": self.rollback_reason,
        }


class SemanticLayerService:
    def __init__(self) -> None:
        self._versions: dict[str, list[KpiDefinitionVersion]] = {}
        self._active_versions: dict[str, str] = {}
        self._cache_invalidated_at = datetime.now(UTC)
        self._seed()

    def _seed(self) -> None:
        for entry in SEED_GLOSSARY:
            version = KpiDefinitionVersion(
                version_id=str(uuid4()),
                term=entry["term"],
                definition=entry["definition"],
                formula=entry["formula"],
                owner=entry["owner"],
                freshness_rule=entry["freshness_rule"],
                changed_by="system-seed",
                timestamp=datetime.now(UTC),
                previous_formula=None,
                action="seed",
            )
            self._versions.setdefault(entry["term"].casefold(), []).append(version)
            self._active_versions[entry["term"].casefold()] = version.version_id

    def list_metrics(self) -> list[dict[str, object]]:
        metrics: list[dict[str, object]] = []
        for normalized_term in sorted(self._versions):
            active = self.get_metric(normalized_term)
            if active is None:
                continue
            metrics.append(
                {
                    "term": active.term,
                    "definition": active.definition,
                    "formula": active.formula,
                    "owner": active.owner,
                    "freshness_rule": active.freshness_rule,
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
        )
        self._versions.setdefault(normalized, []).append(version)
        self._active_versions[normalized] = version.version_id
        self._cache_invalidated_at = datetime.now(UTC)
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
            rollback_reason=reason.strip() if reason else None,
        )
        normalized = term.strip().casefold()
        self._versions.setdefault(normalized, []).append(version)
        self._active_versions[normalized] = version.version_id
        self._cache_invalidated_at = datetime.now(UTC)
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
            if str(metric["term"]).casefold() in normalized_query:
                matches.append(metric)
        return matches

    @property
    def cache_invalidated_at(self) -> datetime:
        return self._cache_invalidated_at


_service = SemanticLayerService()


def get_semantic_layer_service() -> SemanticLayerService:
    return _service


def reset_semantic_layer_service() -> None:
    global _service
    _service = SemanticLayerService()
