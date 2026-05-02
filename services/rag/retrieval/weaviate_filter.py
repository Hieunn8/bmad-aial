"""Weaviate Filter Builder — Story 3.2.

Translates PolicyDecision into a Weaviate where-filter applied BEFORE vector scoring.
Keeps PolicyEnforcementService and WeaviateFilterBuilder separate (AC requirement).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass
class WeaviateFilter:
    """Simplified filter representation (real impl uses weaviate-client Filter objects)."""
    department_filter: list[str] = field(default_factory=list)
    max_classification: int = 0
    effective_date_cutoff: str | None = None

    def __str__(self) -> str:
        parts = []
        if self.department_filter:
            parts.append(f"department in {self.department_filter}")
        if self.max_classification is not None:
            parts.append(f"classification <= {self.max_classification}")
        if self.effective_date_cutoff:
            parts.append(f"effective_date >= {self.effective_date_cutoff}")
        return " AND ".join(parts)


class WeaviateFilterBuilder:
    def build(
        self,
        decision: PolicyDecision,  # noqa: F821
        *,
        staleness_threshold_days: int = 180,
    ) -> WeaviateFilter | None:
        """Return None if policy denies access entirely."""

        if not decision.allowed:
            return None

        cutoff = (date.today() - timedelta(days=staleness_threshold_days)).isoformat()

        return WeaviateFilter(
            department_filter=decision.allowed_departments,
            max_classification=decision.max_classification,
            effective_date_cutoff=cutoff,
        )

    @staticmethod
    def access_notice(decision: PolicyDecision) -> str:  # noqa: F821
        """Return user-facing notice when filtering restricts results."""
        if decision.allowed and len(decision.allowed_departments) <= 1:
            return "Kết quả có thể bị giới hạn bởi quyền truy cập của bạn"
        return ""
