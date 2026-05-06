"""LLM-enhanced Vietnamese time expression parser.

Priority chain:
  1. LLM (Anthropic Haiku or OpenAI) when AIAL_TIME_PARSER_PROVIDER is set
  2. Regex fallback — covers common Vietnamese patterns offline

Env vars:
  AIAL_TIME_PARSER_PROVIDER  — "anthropic" | "openai" | "" (regex-only)
  AIAL_TIME_PARSER_MODEL     — model override
  ANTHROPIC_API_KEY          — required for anthropic provider
  OPENAI_API_KEY             — required for openai provider
  OPENAI_API_BASE_URL        — base URL override for openai provider
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx


@dataclass(frozen=True)
class ParsedTimeFilter:
    kind: str
    start: date | None
    end: date | None  # always exclusive

    def to_sql_clause(self, column: str = "PERIOD_DATE") -> str | None:
        """Returns SQL WHERE fragment, or None if no filter / latest_record intent."""
        if self.kind in ("none", "latest_record") or not self.start or not self.end:
            return None
        return f"{column} >= DATE '{self.start.isoformat()}' AND {column} < DATE '{self.end.isoformat()}'"

    def to_dict(self) -> dict[str, Any] | None:
        """Dict for embedding in semantic_plan — includes resolved ISO dates."""
        if self.kind == "none":
            return None
        result: dict[str, Any] = {"kind": self.kind}
        if self.start:
            result["start"] = self.start.isoformat()
        if self.end:
            result["end"] = self.end.isoformat()
        return result


_NO_FILTER = ParsedTimeFilter(kind="none", start=None, end=None)
_LATEST_RECORD = ParsedTimeFilter(kind="latest_record", start=None, end=None)

_SYSTEM_PROMPT = """You parse Vietnamese time expressions into structured dates. Today is {today}.

Return ONLY a JSON object:
{{
  "kind": "<kind>",
  "start": "<YYYY-MM-DD or null>",
  "end": "<YYYY-MM-DD or null>"
}}

Valid kinds: today, yesterday, current_week, previous_week, current_month, previous_month,
current_year, previous_year, last_N_days, last_N_months, date_range, quarter, specific_month,
latest_record, none

Rules:
- `end` is always EXCLUSIVE (the day AFTER the last included day)
- Weeks start on Monday
- "gần đây nhất" / "mới nhất" / "dữ liệu gần nhất" / "ngày nào có dữ liệu" → kind=latest_record, start=null, end=null
- No time reference in the query → kind=none, start=null, end=null
- Return ONLY the JSON object, no surrounding text or explanation"""


def parse_time_expression(query: str, *, today: date | None = None) -> ParsedTimeFilter:
    """Parse a Vietnamese query for time expression. LLM-first, regex fallback."""
    if today is None:
        today = datetime.now(UTC).date()
    result = _try_llm(query, today=today)
    if result is not None:
        return result
    return _regex_parse(query, today=today)


# ─── LLM path ─────────────────────────────────────────────────────────────────

def _try_llm(query: str, *, today: date) -> ParsedTimeFilter | None:
    provider = os.getenv("AIAL_TIME_PARSER_PROVIDER", "").strip().lower()
    if provider == "anthropic":
        return _anthropic_parse(query, today=today)
    if provider == "openai":
        return _openai_parse(query, today=today)
    return None


def _anthropic_parse(query: str, *, today: date) -> ParsedTimeFilter | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": os.getenv("AIAL_TIME_PARSER_MODEL", "claude-haiku-4-5-20251001"),
                "max_tokens": 150,
                "system": _SYSTEM_PROMPT.format(today=today.isoformat()),
                "messages": [{"role": "user", "content": query}],
            },
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=4.0,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return _parse_json_response(text)
    except Exception:
        return None


def _openai_parse(query: str, *, today: date) -> ParsedTimeFilter | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            json={
                "model": os.getenv("AIAL_TIME_PARSER_MODEL", "gpt-4o-mini"),
                "max_tokens": 150,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT.format(today=today.isoformat())},
                    {"role": "user", "content": query},
                ],
            },
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            timeout=4.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return _parse_json_response(text)
    except Exception:
        return None


def _parse_json_response(text: str) -> ParsedTimeFilter | None:
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    kind = str(payload.get("kind") or "none").strip()
    start = _iso_to_date(str(payload.get("start") or ""))
    end = _iso_to_date(str(payload.get("end") or ""))
    if kind == "latest_record":
        return _LATEST_RECORD
    if kind == "none" or not start:
        return None  # defer to regex for safer handling
    return ParsedTimeFilter(kind=kind, start=start, end=end)


def _iso_to_date(value: str) -> date | None:
    if not value or value.lower() in ("null", "none", ""):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ─── Regex fallback ────────────────────────────────────────────────────────────

def _normalize(value: str) -> str:
    nfd = unicodedata.normalize("NFD", value.casefold())
    stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return " ".join(stripped.replace("đ", "d").split())


def _regex_parse(query: str, *, today: date) -> ParsedTimeFilter:  # noqa: C901
    """Comprehensive regex parser for Vietnamese time expressions."""
    t = _normalize(query)

    # ── latest record — must precede "gan day" patterns ───────────────────────
    if re.search(r"gan day nhat|moi nhat|gan nhat|du lieu gan nhat|ngay moi nhat", t):
        return _LATEST_RECORD

    # ── specific relative days ────────────────────────────────────────────────
    if re.search(r"\bhom nay\b|ngay hom nay|\btoday\b", t):
        return ParsedTimeFilter("today", today, today + timedelta(days=1))
    if re.search(r"\bhom qua\b|ngay hom qua|\byesterday\b", t):
        d = today - timedelta(days=1)
        return ParsedTimeFilter("yesterday", d, today)

    # ── N days ago ────────────────────────────────────────────────────────────
    m = re.search(r"\b(\d{1,3})\s*ngay\s*(gan day|qua|vua qua|truoc)\b", t)
    if m:
        n = max(1, min(int(m.group(1)), 366))
        return ParsedTimeFilter("recent_days", today - timedelta(days=n - 1), today + timedelta(days=1))

    # ── N months ago — checked before generic "gan day" to avoid false match ──
    m = re.search(r"\b(\d{1,2})\s*thang\s*(qua|gan day|truoc|gan nhat)\b", t)
    if m:
        n = max(1, min(int(m.group(1)), 24))
        y, mo = today.year, today.month - n
        while mo <= 0:
            mo += 12
            y -= 1
        return ParsedTimeFilter("recent_months", date(y, mo, 1), today + timedelta(days=1))

    if re.search(r"may ngay nay|gan day|vua qua", t):
        return ParsedTimeFilter("recent_days", today - timedelta(days=6), today + timedelta(days=1))

    # ── week ──────────────────────────────────────────────────────────────────
    if re.search(r"\btuan nay\b|this week", t):
        start = today - timedelta(days=today.weekday())
        return ParsedTimeFilter("current_week", start, start + timedelta(days=7))
    if re.search(r"\btuan truoc\b|last week", t):
        start = today - timedelta(days=today.weekday() + 7)
        return ParsedTimeFilter("previous_week", start, start + timedelta(days=7))

    # ── month ─────────────────────────────────────────────────────────────────
    if re.search(r"\bthang nay\b|this month", t):
        start = today.replace(day=1)
        em = today.month + 1 if today.month < 12 else 1
        ey = today.year if today.month < 12 else today.year + 1
        return ParsedTimeFilter("current_month", start, date(ey, em, 1))
    if re.search(r"\bthang truoc\b|\bthang qua\b|last month", t):
        first_this = today.replace(day=1)
        last_month_last = first_this - timedelta(days=1)
        return ParsedTimeFilter("previous_month", last_month_last.replace(day=1), first_this)

    # ── year ──────────────────────────────────────────────────────────────────
    if re.search(r"\bnam nay\b|this year", t):
        return ParsedTimeFilter("current_year", date(today.year, 1, 1), date(today.year + 1, 1, 1))
    if re.search(r"\bnam truoc\b|\bnam ngoai\b|last year", t):
        return ParsedTimeFilter("previous_year", date(today.year - 1, 1, 1), date(today.year, 1, 1))

    # ── year + quarter ────────────────────────────────────────────────────────
    year_m = re.search(r"\b(20\d{2})\b", t)
    if year_m:
        year = int(year_m.group(1))
        q_m = re.search(r"\bq([1-4])\b|qu[yý]\s*([1-4])", t)
        if q_m:
            q = int(q_m.group(1) or q_m.group(2))
            sm = (q - 1) * 3 + 1
            em = sm + 3
            end_date = date(year + 1, 1, 1) if em > 12 else date(year, em, 1)
            return ParsedTimeFilter("quarter", date(year, sm, 1), end_date)
        return ParsedTimeFilter("year", date(year, 1, 1), date(year + 1, 1, 1))

    # ── specific month number (without year → assume current year) ────────────
    m = re.search(r"\bthang\s*([1-9]|1[0-2])\b", t)
    if m:
        mo = int(m.group(1))
        em = mo + 1 if mo < 12 else 1
        ey = today.year if mo < 12 else today.year + 1
        return ParsedTimeFilter("specific_month", date(today.year, mo, 1), date(ey, em, 1))

    return _NO_FILTER
