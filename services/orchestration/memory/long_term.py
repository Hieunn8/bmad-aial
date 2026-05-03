"""Long-term conversation memory and preference service for Epic 5B."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from difflib import SequenceMatcher
from math import sqrt
from uuid import uuid4

_DEFAULT_RETENTION_DAYS = 90
_SIMILARITY_THRESHOLD = 0.7
_RAW_VALUE_PATTERN = re.compile(r"\b\d+(?:[\.,]\d+)?%?\b|[\w.\-]+@[\w.\-]+")


def _tokenize(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-zA-Z0-9_]+", value.casefold()) if token}


def _cosine_similarity(left: str, right: str) -> float:
    left_tokens = Counter(_tokenize(left))
    right_tokens = Counter(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    dot = sum(left_tokens[token] * right_tokens[token] for token in set(left_tokens) & set(right_tokens))
    left_norm = sqrt(sum(count * count for count in left_tokens.values()))
    right_norm = sqrt(sum(count * count for count in right_tokens.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


def _semantic_similarity(query: str, *candidates: str) -> float:
    scores = []
    for candidate in candidates:
        if not candidate:
            continue
        scores.append(_cosine_similarity(query, candidate))
        scores.append(SequenceMatcher(None, query.casefold(), candidate.casefold()).ratio())
    return max(scores, default=0.0)


def _assert_no_raw_values(value: str) -> None:
    if _RAW_VALUE_PATTERN.search(value):
        raise ValueError("memory entries must not store raw values or PII")


@dataclass(frozen=True)
class ConversationSummary:
    summary_id: str
    user_id: str
    department_id: str
    session_id: str
    sensitivity_level: int
    created_at: datetime
    expires_at: datetime
    intent_type: str
    topic: str
    filter_context: str
    summary_text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "summary_id": self.summary_id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "session_id": self.session_id,
            "sensitivity_level": self.sensitivity_level,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "intent_type": self.intent_type,
            "topic": self.topic,
            "filter_context": self.filter_context,
            "summary_text": self.summary_text,
        }


@dataclass(frozen=True)
class SavedTemplate:
    template_id: str
    user_id: str
    name: str
    query_intent: str
    filters: str
    time_range: str
    output_format: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "template_id": self.template_id,
            "user_id": self.user_id,
            "name": self.name,
            "query_intent": self.query_intent,
            "filters": self.filters,
            "time_range": self.time_range,
            "output_format": self.output_format,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class HistoryEntry:
    entry_id: str
    user_id: str
    department_id: str
    session_id: str
    created_at: datetime
    intent_type: str
    topic: str
    filter_context: str
    key_result_summary: str

    def to_dict(self) -> dict[str, object]:
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "intent_type": self.intent_type,
            "topic": self.topic,
            "filter_context": self.filter_context,
            "key_result_summary": self.key_result_summary,
        }


class ConversationMemoryService:
    def __init__(self) -> None:
        self._summaries: dict[str, list[ConversationSummary]] = defaultdict(list)
        self._templates: dict[str, list[SavedTemplate]] = defaultdict(list)
        self._history: dict[str, list[HistoryEntry]] = defaultdict(list)
        self._learning_disabled: set[str] = set()
        self._kpi_usage: dict[str, Counter[str]] = defaultdict(Counter)
        self._session_turns: dict[tuple[str, str], int] = defaultdict(int)

    def set_learning_enabled(self, *, user_id: str, enabled: bool) -> bool:
        if enabled:
            self._learning_disabled.discard(user_id)
        else:
            self._learning_disabled.add(user_id)
        return enabled

    def store_session_summary(
        self,
        *,
        user_id: str,
        department_id: str,
        session_id: str,
        sensitivity_level: int,
        intent_type: str,
        topic: str,
        filter_context: str,
        summary_text: str,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
    ) -> ConversationSummary:
        for value in (topic, filter_context, summary_text):
            _assert_no_raw_values(value)
        summary = ConversationSummary(
            summary_id=str(uuid4()),
            user_id=user_id,
            department_id=department_id,
            session_id=session_id,
            sensitivity_level=sensitivity_level,
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=retention_days),
            intent_type=intent_type,
            topic=topic,
            filter_context=filter_context,
            summary_text=summary_text,
        )
        self._summaries[user_id].append(summary)
        return summary

    def record_interaction(
        self,
        *,
        user_id: str,
        department_id: str,
        session_id: str,
        intent_type: str,
        topic: str,
        filter_context: str,
        key_result_summary: str,
        sensitivity_level: int,
        matched_metrics: list[str],
    ) -> HistoryEntry:
        for value in (topic, filter_context, key_result_summary):
            _assert_no_raw_values(value)
        if user_id not in self._learning_disabled:
            for metric in matched_metrics:
                self._kpi_usage[user_id][metric] += 1
        entry = HistoryEntry(
            entry_id=str(uuid4()),
            user_id=user_id,
            department_id=department_id,
            session_id=session_id,
            created_at=datetime.now(UTC),
            intent_type=intent_type,
            topic=topic,
            filter_context=filter_context,
            key_result_summary=key_result_summary,
        )
        self._history[user_id].append(entry)
        session_key = (user_id, session_id)
        self._session_turns[session_key] += 1
        if self._session_turns[session_key] % 10 == 0:
            self.store_session_summary(
                user_id=user_id,
                department_id=department_id,
                session_id=session_id,
                sensitivity_level=sensitivity_level,
                intent_type=intent_type,
                topic=topic,
                filter_context=filter_context,
                summary_text=f"Intent {intent_type} on topic {topic}",
            )
        return entry

    def get_recent_summaries(
        self,
        *,
        user_id: str,
        department_id: str,
        clearance: int,
        query: str,
        limit: int = 30,
    ) -> list[ConversationSummary]:
        candidates = [
            summary
            for summary in self._summaries.get(user_id, [])
            if summary.expires_at >= datetime.now(UTC)
            and summary.sensitivity_level <= clearance
            and summary.department_id == department_id
        ]
        ranked = [
            (
                summary,
                _semantic_similarity(
                    query,
                    summary.topic,
                    summary.filter_context,
                    summary.summary_text,
                    f"{summary.topic} {summary.filter_context} {summary.summary_text}",
                ),
            )
            for summary in candidates
        ]
        ranked = [item for item in ranked if item[1] >= _SIMILARITY_THRESHOLD]
        ranked.sort(key=lambda item: (item[1], item[0].created_at), reverse=True)
        return [summary for summary, _ in ranked[:limit]]

    def build_context_bundle(
        self,
        *,
        user_id: str,
        department_id: str,
        clearance: int,
        query: str,
    ) -> dict[str, object]:
        summaries = self.get_recent_summaries(
            user_id=user_id,
            department_id=department_id,
            clearance=clearance,
            query=query,
        )
        token_budget_increase_percent = min(20, len(summaries) * 5)
        return {
            "summaries": [summary.to_dict() for summary in summaries],
            "token_budget_increase_percent": token_budget_increase_percent,
            "threshold": _SIMILARITY_THRESHOLD,
        }

    def save_template(
        self,
        *,
        user_id: str,
        name: str,
        query_intent: str,
        filters: str,
        time_range: str,
        output_format: str,
    ) -> SavedTemplate:
        for value in (query_intent, filters):
            _assert_no_raw_values(value)
        template = SavedTemplate(
            template_id=str(uuid4()),
            user_id=user_id,
            name=name.strip(),
            query_intent=query_intent.strip(),
            filters=filters.strip(),
            time_range=time_range.strip(),
            output_format=output_format.strip(),
            created_at=datetime.now(UTC),
        )
        self._templates[user_id].append(template)
        return template

    def list_templates(self, *, user_id: str) -> list[SavedTemplate]:
        return list(self._templates.get(user_id, []))

    def get_suggestions(self, *, user_id: str) -> list[dict[str, object]]:
        suggestions: list[dict[str, object]] = []
        for metric, count in self._kpi_usage[user_id].most_common(3):
            suggestions.append({"type": "kpi", "label": metric, "uses": count})
        for template in self._templates.get(user_id, [])[: max(0, 3 - len(suggestions))]:
            suggestions.append({"type": "template", "label": template.name, "template_id": template.template_id})
        return suggestions[:3]

    def search_history(
        self,
        *,
        user_id: str,
        keyword: str | None = None,
        topic: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[HistoryEntry]:
        results = list(self._history.get(user_id, []))
        if keyword:
            normalized = keyword.casefold()
            results = [
                entry
                for entry in results
                if normalized in entry.topic.casefold()
                or normalized in entry.filter_context.casefold()
                or normalized in entry.key_result_summary.casefold()
            ]
        if topic:
            normalized_topic = topic.casefold()
            results = [entry for entry in results if normalized_topic in entry.topic.casefold()]
        if date_from:
            results = [entry for entry in results if entry.created_at >= date_from]
        if date_to:
            results = [entry for entry in results if entry.created_at <= date_to]
        results.sort(key=lambda item: item.created_at, reverse=True)
        return results

    def reuse_history_entry(self, *, user_id: str, entry_id: str) -> dict[str, object]:
        entry = next((item for item in self._history.get(user_id, []) if item.entry_id == entry_id), None)
        if entry is None:
            raise KeyError(entry_id)
        return {
            "intent_type": entry.intent_type,
            "topic": entry.topic,
            "filters": entry.filter_context,
        }

    def memory_audit(self, *, user_id: str | None = None) -> list[dict[str, str]]:
        violations: list[dict[str, str]] = []
        summary_users = [user_id] if user_id is not None else list(self._summaries)
        for summary_user_id in summary_users:
            for summary in self._summaries.get(summary_user_id, []):
                for field_name in ("topic", "filter_context", "summary_text"):
                    value = getattr(summary, field_name)
                    if _RAW_VALUE_PATTERN.search(value):
                        violations.append({"user_id": summary_user_id, "entry_type": "summary", "field": field_name})
        template_users = [user_id] if user_id is not None else list(self._templates)
        for template_user_id in template_users:
            for template in self._templates.get(template_user_id, []):
                for field_name in ("query_intent", "filters"):
                    value = getattr(template, field_name)
                    if _RAW_VALUE_PATTERN.search(value):
                        violations.append({"user_id": template_user_id, "entry_type": "template", "field": field_name})
        history_users = [user_id] if user_id is not None else list(self._history)
        for history_user_id in history_users:
            for entry in self._history.get(history_user_id, []):
                for field_name in ("topic", "filter_context", "key_result_summary"):
                    value = getattr(entry, field_name)
                    if _RAW_VALUE_PATTERN.search(value):
                        violations.append({"user_id": history_user_id, "entry_type": "history", "field": field_name})
        return violations


_service = ConversationMemoryService()


def get_conversation_memory_service() -> ConversationMemoryService:
    return _service


def reset_conversation_memory_service() -> None:
    global _service
    _service = ConversationMemoryService()
