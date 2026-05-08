"""LLM-based full semantic query understanding.

Replaces (and wraps) the deterministic SemanticPlanner with an LLM that:
  - Understands long-winded / synonym-heavy Vietnamese queries
  - Identifies the correct semantic term from registry candidates
  - Extracts time filter, dimensions, and intent in one pass
  - Generates natural Vietnamese clarification when ambiguous

Priority chain (first success wins):
  1. AIAL_QUERY_ANALYZER_PROVIDER=anthropic  → Anthropic Haiku (fast, cheap)
  2. AIAL_QUERY_ANALYZER_PROVIDER=openai     → OpenAI gpt-4o-mini
  3. (not set)                               → return None → deterministic fallback

Env vars:
  AIAL_QUERY_ANALYZER_PROVIDER  — "anthropic" | "openai" | ""
  AIAL_QUERY_ANALYZER_MODEL     — model override
  ANTHROPIC_API_KEY / OPENAI_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from orchestration.semantic.resolver import SemanticPlannerOutput, SemanticResolveCandidate

logger = logging.getLogger(__name__)

# ─── Prompt ───────────────────────────────────────────────────────────────────

_SYSTEM = """\
You are a Vietnamese business analytics query router.
Today is {today}.

Your job: map the user's question to exactly ONE of the registered semantic metrics below,
extract query parameters, and ask for clarification only when truly necessary.

{metrics_block}

Return ONLY a JSON object — no other text:
{{
  "selected_term": "<exact term from the list above, or null>",
  "intent": "metric_value" | "metric_breakdown" | "definition" | "latest_date",
  "time_filter": {{"kind":"<kind>","start":"<YYYY-MM-DD or null>","end":"<YYYY-MM-DD or null>"}} | null,
  "dimensions": ["REGION_CODE" | "CHANNEL_CODE" | "PRODUCT_CODE" | "CATEGORY_NAME"],
  "entity_filters": {{"REGION_CODE": "HCM"}},
  "confidence": 0.0,
  "needs_clarification": false,
  "clarification_question": null,
  "rationale": "<one sentence in English>"
}}

RULES:
1. selected_term must match one of the listed terms EXACTLY (case-sensitive), or be null.
2. Synonyms and aliases listed under each metric all map to the same term.
3. time_filter.end is EXCLUSIVE (= last included day + 1).
   Common patterns: hôm nay/today → {{start:today,end:tomorrow}},
   hôm qua/yesterday, tuần này/this week (Mon–Sun), tháng này/this month, N ngày gần đây.
4. intent:
   - "metric_value"    → user wants a single aggregated number
   - "metric_breakdown"→ user asks to group/split by region/channel/product/category
   - "definition"      → user asks what the metric means (no data needed)
   - "latest_date"     → user asks which date has the most recent data
5. dimensions: GROUP BY columns — only when user asks "theo khu vực / theo kênh / theo sản phẩm".
6. entity_filters: WHERE conditions for specific values the user mentioned:
   - "HCM" / "Hồ Chí Minh" / "Sài Gòn" → {{"REGION_CODE": "HCM"}}
   - "Hà Nội" / "HN" → {{"REGION_CODE": "HN"}}
   - "Đà Nẵng" / "miền Trung" → {{"REGION_CODE": "DANANG"}}
   - "online" → {{"CHANNEL_CODE": "ONLINE"}}
   - "retail" / "bán lẻ" → {{"CHANNEL_CODE": "RETAIL"}}
   - "B2B" → {{"CHANNEL_CODE": "B2B"}}
   DO NOT set the same column in both dimensions and entity_filters (filter wins).
7. needs_clarification = true ONLY when:
   a) Two or more metrics match equally well and context cannot disambiguate.
   b) The query is unrelated to ALL listed metrics.
   DO NOT ask about time or missing filters — queries without time are valid (all-time data).
8. clarification_question: natural, concise Vietnamese (1–2 sentences). List the ambiguous options.
9. confidence: 0.0–1.0. Use ≥0.75 when you are confident. Below 0.55 implies needs_clarification."""


def _build_metrics_block(candidates: list[SemanticResolveCandidate]) -> str:
    lines: list[str] = []
    for i, cand in enumerate(candidates, 1):
        m = cand.metric
        term = str(m.get("term", ""))
        aliases = ", ".join(str(a) for a in m.get("aliases", []) if a)
        definition = str(m.get("definition", ""))
        dims = ", ".join(str(d) for d in m.get("dimensions", []) if d)
        examples = "; ".join(f'"{ex}"' for ex in m.get("examples", [])[:4] if ex)
        lines.append(f"## [{i}] {term}")
        if aliases:
            lines.append(f"   Aliases: {aliases}")
        if definition:
            lines.append(f"   Definition: {definition}")
        if dims:
            lines.append(f"   Dimensions: {dims}")
        if examples:
            lines.append(f"   Example queries: {examples}")
    return "\n".join(lines)


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze_query(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date | None = None,
) -> SemanticPlannerOutput | None:
    """Analyze the full user query with LLM. Returns None to trigger deterministic fallback."""
    if not candidates:
        return None
    if today is None:
        today = datetime.now(UTC).date()

    provider = os.getenv("AIAL_QUERY_ANALYZER_PROVIDER", "").strip().lower()
    if provider == "anthropic":
        return _anthropic_analyze(query=query, candidates=candidates, today=today)
    if provider == "openai":
        return _openai_analyze(query=query, candidates=candidates, today=today)
    return None


# ─── LLM calls ────────────────────────────────────────────────────────────────

def _build_prompt(*, candidates: list[SemanticResolveCandidate], today: date) -> str:
    return _SYSTEM.format(
        today=today.isoformat(),
        metrics_block=_build_metrics_block(candidates),
    )


def _anthropic_analyze(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date,
) -> SemanticPlannerOutput | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": os.getenv("AIAL_QUERY_ANALYZER_MODEL", "claude-haiku-4-5-20251001"),
                "max_tokens": 400,
                "system": _build_prompt(candidates=candidates, today=today),
                "messages": [{"role": "user", "content": query}],
            },
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=6.0,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
        return _parse_response(text, candidates=candidates)
    except Exception as exc:
        logger.warning("QueryAnalyzer Anthropic call failed: %s", exc)
        return None


def _openai_analyze(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date,
) -> SemanticPlannerOutput | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            json={
                "model": os.getenv("AIAL_QUERY_ANALYZER_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
                "max_tokens": 400,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": _build_prompt(candidates=candidates, today=today)},
                    {"role": "user", "content": query},
                ],
                "response_format": {"type": "json_object"},
            },
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            timeout=6.0,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return _parse_response(text, candidates=candidates)
    except Exception as exc:
        logger.warning("QueryAnalyzer OpenAI call failed: %s", exc)
        return None


# ─── Response parsing ─────────────────────────────────────────────────────────

def _parse_response(
    text: str,
    *,
    candidates: list[SemanticResolveCandidate],
) -> SemanticPlannerOutput | None:
    from orchestration.semantic.resolver import SemanticPlannerOutput

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None

    # Validate selected_term is in the candidate list
    selected_term = payload.get("selected_term")
    valid_terms = {str(c.metric.get("term", "")) for c in candidates}
    if selected_term and str(selected_term) not in valid_terms:
        logger.warning("LLM selected unknown term %r — discarding", selected_term)
        selected_term = None

    needs_clarification = bool(payload.get("needs_clarification", False))
    confidence = float(payload.get("confidence", 0.0))
    if confidence < 0.55 and not needs_clarification:
        needs_clarification = True

    time_filter = _parse_time_filter(payload.get("time_filter"))

    _VALID_DIMS = {"REGION_CODE", "CHANNEL_CODE", "PRODUCT_CODE", "CATEGORY_NAME"}
    # entity_filters: specific WHERE values
    entity_filters: dict[str, str] = {}
    raw_ef = payload.get("entity_filters") or {}
    if isinstance(raw_ef, dict):
        for col, val in raw_ef.items():
            if col in _VALID_DIMS and val and str(val).strip():
                entity_filters[col] = str(val).strip().upper()
    # dimensions: GROUP BY columns — remove any that are already entity_filtered
    dimensions = [
        d for d in payload.get("dimensions", [])
        if d in _VALID_DIMS and d not in entity_filters
    ]

    clarification_question = payload.get("clarification_question") or None
    if needs_clarification and not clarification_question:
        candidate_terms = [str(c.metric.get("term", "")) for c in candidates[:4]]
        clarification_question = (
            "Bạn muốn xem dữ liệu nào: "
            + ", ".join(f"`{t}`" for t in candidate_terms)
            + "? Vui lòng chỉ định rõ hơn."
        )

    return SemanticPlannerOutput(
        status="ambiguous" if needs_clarification else "selected",
        selected_term=str(selected_term) if selected_term else (
            str(candidates[0].metric.get("term", "")) if not needs_clarification else None
        ),
        intent=str(payload.get("intent") or "metric_value"),
        time_filter=time_filter,
        dimensions=dimensions,
        entity_filters=entity_filters,
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        rationale=str(payload.get("rationale") or "llm_query_analyzer"),
    )


def _parse_time_filter(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    kind = str(value.get("kind") or "none")
    if kind == "none":
        return None
    result: dict[str, Any] = {"kind": kind}
    start = value.get("start")
    end = value.get("end")
    if start and str(start).lower() not in ("null", "none", ""):
        result["start"] = str(start)
    if end and str(end).lower() not in ("null", "none", ""):
        result["end"] = str(end)
    if not result.get("start") and kind not in ("latest_record",):
        return None  # incomplete filter — let regex handle it
    return result
