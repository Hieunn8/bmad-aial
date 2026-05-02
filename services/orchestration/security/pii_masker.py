"""PII Masking with Presidio — Story 4.3 (FR-A5).

- Inline scan for rows × free_text_cols ≤ 10,000 cells.
- Async stub for > 10,000 cells (real: Celery job).
- clearance ≥ 3 → bypass masking (Cerbos must grant clearance_threshold first).
- SanitizedLogger strips PII before any metric/log emission.
- Hooks into post_query_hook — NOT pre-execution_hook.
- Vietnamese recognizers: CMND (12-digit), Vietnamese phone patterns.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False

_CLEARANCE_BYPASS = 3
_INLINE_CELL_LIMIT = 10_000

# Vietnamese replacements
_REPLACEMENTS = {
    "PERSON": "<TÊN_ĐƯỢC_ẨN>",
    "EMAIL_ADDRESS": "<EMAIL_ĐƯỢC_ẨN>",
    "PHONE_NUMBER": "<SĐT_ĐƯỢC_ẨN>",
    "ID_CARD_VN": "<CMND_ĐƯỢC_ẨN>",
}

# Simple regex fallback patterns
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b")
_PHONE_RE = re.compile(r"\b(0[3-9]\d{8}|\+84\d{9})\b")
_CMND_RE = re.compile(r"\b\d{12}\b")


@dataclass
class PiiMaskResult:
    text: str
    entities_found: list[str] = field(default_factory=list)

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "entities_found": list(set(self.entities_found)),
            "masked_count": len(self.entities_found),
        }


@dataclass
class PiiScanResult:
    mode: str  # "inline" | "async"
    rows: list[dict[str, Any]] = field(default_factory=list)
    scan_id: str | None = None


def _mask_with_regex(text: str) -> tuple[str, list[str]]:
    entities: list[str] = []
    if _EMAIL_RE.search(text):
        text = _EMAIL_RE.sub("<EMAIL_ĐƯỢC_ẨN>", text)
        entities.append("EMAIL_ADDRESS")
    if _PHONE_RE.search(text):
        text = _PHONE_RE.sub("<SĐT_ĐƯỢC_ẨN>", text)
        entities.append("PHONE_NUMBER")
    if _CMND_RE.search(text):
        text = _CMND_RE.sub("<CMND_ĐƯỢC_ẨN>", text)
        entities.append("ID_CARD_VN")
    return text, entities


class PiiMasker:
    def __init__(self) -> None:
        if _PRESIDIO_AVAILABLE:
            # Add Vietnamese CMND recognizer
            cmnd_recognizer = PatternRecognizer(
                supported_entity="ID_CARD_VN",
                patterns=[Pattern(name="cmnd-12", regex=r"\b\d{12}\b", score=0.85)],
            )
            self._analyzer = AnalyzerEngine()
            self._analyzer.registry.add_recognizer(cmnd_recognizer)
            self._anonymizer = AnonymizerEngine()
        else:
            self._analyzer = None
            self._anonymizer = None

    def mask_text(self, text: str, *, user_clearance: int = 0) -> PiiMaskResult:
        if user_clearance >= _CLEARANCE_BYPASS:
            return PiiMaskResult(text=text)
        if not _PRESIDIO_AVAILABLE or self._analyzer is None:
            masked, entities = _mask_with_regex(text)
            return PiiMaskResult(text=masked, entities_found=entities)
        try:
            results = self._analyzer.analyze(text=text, language="en")
            entities = [r.entity_type for r in results]
            operators = {
                ent: OperatorConfig("replace", {"new_value": _REPLACEMENTS.get(ent, "<ẨN>")})
                for ent in set(entities)
            }
            anonymized = self._anonymizer.anonymize(
                text=text, analyzer_results=results, operators=operators
            )
            return PiiMaskResult(text=anonymized.text, entities_found=entities)
        except Exception:
            masked, entities = _mask_with_regex(text)
            return PiiMaskResult(text=masked, entities_found=entities)

    def scan_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        free_text_columns: list[str],
        user_clearance: int = 0,
    ) -> PiiScanResult:
        cell_count = len(rows) * len(free_text_columns)
        if cell_count > _INLINE_CELL_LIMIT:
            return PiiScanResult(mode="async", scan_id=str(uuid.uuid4()))

        masked_rows: list[dict[str, Any]] = []
        for row in rows:
            new_row = dict(row)
            for col in free_text_columns:
                if col in new_row and isinstance(new_row[col], str):
                    result = self.mask_text(new_row[col], user_clearance=user_clearance)
                    new_row[col] = result.text
            masked_rows.append(new_row)
        return PiiScanResult(mode="inline", rows=masked_rows)


class SanitizedLogger:
    """Strips PII before emitting any log/metric. Used before Presidio metrics output."""

    def __init__(self, sink: Callable[[str], None] | None = None) -> None:
        self._sink = sink or print
        self._masker = PiiMasker()

    def log(self, message: str) -> None:
        result = self._masker.mask_text(message)
        self._sink(result.text)
