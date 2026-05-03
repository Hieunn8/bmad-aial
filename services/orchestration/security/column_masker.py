"""Column-level Security — Story 4.2 (FR-A4).

Masking/exclusion applied in Oracle Connector result processing layer, NOT frontend.
Presidio skips structured (non-free-text) columns — overlap-free design.
Audit records: field name + action, never the masked value.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class ColumnSensitivity(IntEnum):
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3


@dataclass
class ColumnResult:
    """Annotated column value — carries free_text flag for Presidio routing."""

    name: str
    value: Any
    is_free_text: bool = False
    sensitivity: ColumnSensitivity = ColumnSensitivity.PUBLIC


def apply_column_security(
    rows: list[dict[str, Any]],
    *,
    schema: dict[str, ColumnSensitivity],
    user_clearance: int,
    return_audit: bool = False,
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply column masking per clearance level.

    INTERNAL (≥1): replace value with '***' for clearance < 1.
    CONFIDENTIAL (≥2): replace value with '***' for clearance < 2.
    SECRET (≥3): exclude column entirely (name AND value) for clearance < 3.
    Untagged columns default to PUBLIC — no restriction.
    """
    processed: list[dict[str, Any]] = []
    audit_records: list[dict[str, Any]] = []

    for row in rows:
        new_row: dict[str, Any] = {}
        for col, val in row.items():
            sensitivity = schema.get(col, ColumnSensitivity.PUBLIC)
            if sensitivity == ColumnSensitivity.SECRET and user_clearance < 3:
                # Exclude entirely — name AND value absent
                audit_records.append({"field": col, "action": "excluded"})
                continue
            elif sensitivity == ColumnSensitivity.CONFIDENTIAL and user_clearance < 2:
                new_row[col] = "***"
                audit_records.append({"field": col, "action": "masked"})
            elif sensitivity == ColumnSensitivity.INTERNAL and user_clearance < 1:
                new_row[col] = "***"
                audit_records.append({"field": col, "action": "masked"})
            else:
                new_row[col] = val
        processed.append(new_row)

    if return_audit:
        return processed, audit_records
    return processed
