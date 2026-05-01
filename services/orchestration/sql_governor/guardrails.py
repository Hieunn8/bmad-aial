"""SQL Guardrails — two-layer AST + regex blocklist, plus query governor.

Layer 1 — AST (sqlglot Oracle dialect): blocks non-SELECT statements.
  Security invariant: parse failure → DENY (fail-closed, never fail-open).
Layer 2 — Regex blocklist: blocks dangerous Oracle-specific patterns.
Governor — appends FETCH FIRST 50000 ROWS ONLY when absent.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import sqlglot
    import sqlglot.expressions as exp

    _SQLGLOT_AVAILABLE = True
except ImportError:
    _SQLGLOT_AVAILABLE = False

# ---------------------------------------------------------------------------
# Blocked regex patterns (Oracle-specific dangerous constructs)
# ---------------------------------------------------------------------------

_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bCONNECT\s+BY\b", re.IGNORECASE),
    re.compile(r"\bXMLQUERY\b", re.IGNORECASE),
    re.compile(r"\bDBMS_\w+", re.IGNORECASE),
    re.compile(r"@\w+"),
    re.compile(r"\bFLASHBACK\b", re.IGNORECASE),
    re.compile(r"\bEXECUTE\s+IMMEDIATE\b", re.IGNORECASE),
]

_BLOCKED_AST_TYPES = (
    "Drop", "Create", "Insert", "Update", "Delete", "Alter", "Truncate",
)

_ROW_LIMIT = 50_000
_FETCH_FIRST_RE = re.compile(r"\bFETCH\s+FIRST\b", re.IGNORECASE)


@dataclass(frozen=True)
class SqlGuardResult:
    allowed: bool
    code: str | None = None
    reason: str | None = None


class SqlGuardrails:
    @staticmethod
    def validate(sql: str) -> SqlGuardResult:
        # Layer 1: AST check via sqlglot (if available)
        if _SQLGLOT_AVAILABLE:
            try:
                statements = sqlglot.parse(sql, dialect="oracle")
                for stmt in statements:
                    if stmt is None:
                        continue
                    for blocked_type in _BLOCKED_AST_TYPES:
                        cls = getattr(exp, blocked_type, None)
                        if cls and isinstance(stmt, cls):
                            return SqlGuardResult(allowed=False, code="SQL_UNSAFE_OPERATION", reason=blocked_type)
            except Exception as exc:
                # Fail-closed: unparseable SQL is treated as unsafe.
                # Do not fall through — a parse error could indicate obfuscated DDL/DML.
                logger.warning("sqlglot parse failed, denying SQL: %s", exc)
                return SqlGuardResult(allowed=False, code="SQL_PARSE_ERROR", reason=str(exc))

        # Layer 2: Regex blocklist — always runs
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(sql):
                return SqlGuardResult(allowed=False, code="SQL_UNSAFE_OPERATION", reason=pattern.pattern)

        # Keyword-based fallback (covers cases where sqlglot is unavailable)
        upper = sql.strip().upper()
        for keyword in ("DROP ", "INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "TRUNCATE "):
            if upper.startswith(keyword) or f" {keyword}" in f" {upper}":
                return SqlGuardResult(allowed=False, code="SQL_UNSAFE_OPERATION", reason=keyword.strip())

        return SqlGuardResult(allowed=True)


class QueryGovernor:
    @staticmethod
    def apply(sql: str) -> str:
        if not _FETCH_FIRST_RE.search(sql):
            return sql.rstrip().rstrip(";") + f" FETCH FIRST {_ROW_LIMIT} ROWS ONLY"
        return sql
