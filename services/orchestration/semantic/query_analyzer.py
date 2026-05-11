"""LLM-based full semantic query understanding.

When AIAL_SEMANTIC_DSL_V2=true  → analyze_query() returns QueryPlan (new path).
When AIAL_SEMANTIC_DSL_V2=false → analyze_query() returns SemanticPlannerOutput (legacy path).

Priority chain (first success wins):
  1. AIAL_QUERY_ANALYZER_PROVIDER=anthropic  → Anthropic Haiku
  2. AIAL_QUERY_ANALYZER_PROVIDER=openai     → OpenAI gpt-4.1-mini
  3. (not set)                               → return None → deterministic fallback

Env vars:
  AIAL_SEMANTIC_DSL_V2           — "true" enables QueryPlan mode
  AIAL_QUERY_ANALYZER_PROVIDER   — "anthropic" | "openai" | ""
  AIAL_QUERY_ANALYZER_MODEL      — model override
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

_DSL_V2_FLAG = "AIAL_SEMANTIC_DSL_V2"


def _dsl_v2_enabled() -> bool:
    return os.getenv(_DSL_V2_FLAG, "").strip().lower() == "true"


# ─── Legacy prompt (returns SemanticPlannerOutput) ────────────────────────────

_SYSTEM_LEGACY = """\
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


# ─── DSL v2 prompt (returns QueryPlan) ───────────────────────────────────────

_SYSTEM_DSL = """\
You are AIAL's analytics query planner.
Today is {today}. User locale: vi.

Convert the user's question into a STRICT JSON QueryPlan.
Available metrics (catalog):
{metrics_block}

Allowed dimension columns (per metric):
{dimensions_block}

Allowed filter operators: eq, ne, in, not_in, between, like, is_null, not_null
Allowed time grains: day, week, month, quarter, year
Allowed compare_to: previous_period, previous_year, year_to_date_prev, custom
Output formats: number, table, report, chart_hint, auto

OUTPUT: JSON only, schema:
{{
  "metrics": [{{"term": "<exact catalog term>", "alias": "<optional>"}}],
  "filters": [{{"column": "<dim>", "op": "<op>", "values": [...]}}],
  "group_by": ["<dim_column>"],
  "time": {{"column": "PERIOD_DATE", "start": "<YYYY-MM-DD or null>", "end": "<YYYY-MM-DD or null>",
            "grain": "<grain or null>", "compare_to": "<compare_period or null>"}},
  "derived": [{{"name": "<col>", "expr": "<expr>", "inputs": ["<alias1>", "<alias2>"]}}],
  "sort": [{{"column": "<col>", "direction": "asc|desc"}}],
  "limit": null,
  "output": {{"format": "auto", "chart_type": null, "show_total": false, "locale": "vi"}},
  "confidence": 0.9,
  "needs_clarification": false,
  "clarification_question": null,
  "rationale": "<one sentence in English>"
}}

RULES:
1. metrics[].term must match catalog EXACTLY. If unsure → metrics:[], needs_clarification:true.
2. time.end is EXCLUSIVE (last_included_day + 1).
   "tháng 1" → start:"2026-01-01", end:"2026-02-01"
   "Q1 2026"  → start:"2026-01-01", end:"2026-04-01"
3. FILTER + GROUP_BY FOR SPECIFIC VALUES (CRITICAL RULE):
   When user names ≥2 specific values for any dimension (e.g. "HCM và HN", "HCM với Hà Nội",
   "online và retail", "kênh A và kênh B") — WITH OR WITHOUT "so sánh":
   a) Add filter: {{"column": "REGION_CODE", "op": "in", "values": ["HCM", "HN"]}}
   b) Add group_by: ["REGION_CODE"]
   BOTH are MANDATORY. The filter restricts results to ONLY those values.
   Omitting filter → ALL other regions (e.g. DANANG) will incorrectly appear.
4. "so sánh" / "compare" / "vs" / "và" between two locations → ALWAYS apply rule 3.
5. Top-N: "top N" / "N cao nhất" → sort desc + limit=N + group_by the noun.
6. Bottom-N: "thấp nhất" / "ít nhất" → sort asc + limit + group_by.
7. Share: "tỷ trọng" / "%" → derived: share_of_total + group_by.
8. Ratio: "biên" / "margin" / "X/Y" → derived: ratio over 2 metrics.
9. TIME GRAIN (CRITICAL — default is NO grain):
   - SET grain ONLY for explicit time series: "theo tuần/tháng/quý/năm", "xu hướng", "trend",
     "6 tháng gần đây theo tháng", "doanh thu từng tháng"
   - DO NOT SET grain for: "tháng 1", "Q1 2026", "năm 2025", "tháng này" — these are PERIODS not series.
   - When in doubt: leave grain as null.
10. Period comparison: "so với tháng trước/năm trước" → compare_to + format=report or table.
11. Definition: "X là gì" → rationale="definition_only".
12. Latest date: "dữ liệu gần nhất" → rationale="latest_date".
13. Vague query → metrics:[], needs_clarification:true, clarification_question with options.
14. NEVER invent column names not in the dimensions list.
15. confidence ∈ [0,1]. If <0.55 → needs_clarification:true.
16. DATE COLUMNS IN FILTERS — ABSOLUTELY FORBIDDEN:
    NEVER put PERIOD_DATE or any date/time column in "filters".
    Time ranges ALWAYS go in time.start / time.end ONLY.
    WRONG: {{"filters": [{{"column": "PERIOD_DATE", "op": "in", "values": ["2026-01-01"]}}]}}
    RIGHT:  {{"time": {{"start": "2026-01-01", "end": "2026-02-01"}}, "filters": []}}

Dimension value normalization:
- "Hồ Chí Minh" / "HCM" / "Sài Gòn" → "HCM"
- "Hà Nội" / "HN" / "thủ đô" → "HN"
- "Đà Nẵng" / "miền Trung" → "DANANG"
- "online" / "trực tuyến" → "ONLINE"
- "retail" / "bán lẻ" → "RETAIL"
- "B2B" → "B2B"
"""


# ─── Metrics block builders ───────────────────────────────────────────────────

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


def _build_dimensions_block(candidates: list[SemanticResolveCandidate]) -> str:
    all_dims: set[str] = set()
    for cand in candidates:
        for d in cand.metric.get("dimensions", []):
            all_dims.add(str(d))
    return ", ".join(sorted(all_dims)) or "REGION_CODE, CHANNEL_CODE, PRODUCT_CODE, CATEGORY_NAME"


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze_query(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date | None = None,
) -> SemanticPlannerOutput | None:
    """Analyze the full user query with LLM.

    Returns QueryPlan (wrapped in legacy adapter) when DSL v2 flag is on,
    or SemanticPlannerOutput directly in legacy mode.
    Returns None to trigger deterministic fallback.
    """
    if not candidates:
        return None
    if today is None:
        today = datetime.now(UTC).date()

    provider = os.getenv("AIAL_QUERY_ANALYZER_PROVIDER", "").strip().lower()
    if _dsl_v2_enabled():
        result = _analyze_dsl(query=query, candidates=candidates, today=today, provider=provider)
        if result is not None:
            return result
    else:
        if provider == "anthropic":
            return _anthropic_analyze_legacy(query=query, candidates=candidates, today=today)
        if provider == "openai":
            return _openai_analyze_legacy(query=query, candidates=candidates, today=today)
    return None


# ─── DSL v2 path ─────────────────────────────────────────────────────────────

def _analyze_dsl(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date,
    provider: str,
) -> SemanticPlannerOutput | None:
    """Call LLM with DSL prompt, parse QueryPlan, return as legacy SemanticPlannerOutput via adapter."""
    from orchestration.semantic.dsl import QueryPlan, queryplan_to_legacy_dict
    from orchestration.semantic.resolver import SemanticPlannerOutput

    system = _SYSTEM_DSL.format(
        today=today.isoformat(),
        metrics_block=_build_metrics_block(candidates),
        dimensions_block=_build_dimensions_block(candidates),
    )
    text = _call_llm(query=query, system=system, provider=provider, max_tokens=700)
    if text is None:
        return None

    plan = _parse_queryplan(text, candidates=candidates)
    if plan is None:
        return None

    legacy = queryplan_to_legacy_dict(plan)
    time_filter = legacy.get("time_filter")
    if isinstance(time_filter, dict) and not time_filter.get("start"):
        time_filter = None

    return SemanticPlannerOutput(
        status="ambiguous" if plan.needs_clarification else "selected",
        selected_term=str(legacy.get("selected_term") or ""),
        intent=str(legacy.get("intent") or "metric_value"),
        time_filter=time_filter,
        dimensions=list(plan.group_by),
        entity_filters={
            f.column: str(f.values[0])
            for f in plan.filters
            if f.op == "eq" and f.values
        },
        confidence=plan.confidence,
        needs_clarification=plan.needs_clarification,
        clarification_question=plan.clarification_question,
        rationale=plan.rationale or "dsl_v2_planner",
        query_plan=plan,
    )


# ─── Legacy path ──────────────────────────────────────────────────────────────

def _anthropic_analyze_legacy(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date,
) -> SemanticPlannerOutput | None:
    system = _SYSTEM_LEGACY.format(
        today=today.isoformat(),
        metrics_block=_build_metrics_block(candidates),
    )
    text = _call_llm(query=query, system=system, provider="anthropic", max_tokens=400)
    if text is None:
        return None
    return _parse_response_legacy(text, candidates=candidates)


def _openai_analyze_legacy(
    *,
    query: str,
    candidates: list[SemanticResolveCandidate],
    today: date,
) -> SemanticPlannerOutput | None:
    system = _SYSTEM_LEGACY.format(
        today=today.isoformat(),
        metrics_block=_build_metrics_block(candidates),
    )
    text = _call_llm(query=query, system=system, provider="openai", max_tokens=400)
    if text is None:
        return None
    return _parse_response_legacy(text, candidates=candidates)


# ─── LLM call abstraction ─────────────────────────────────────────────────────

def _call_llm(*, query: str, system: str, provider: str, max_tokens: int) -> str | None:
    if provider == "anthropic":
        return _anthropic_call(query=query, system=system, max_tokens=max_tokens)
    if provider == "openai":
        return _openai_call(query=query, system=system, max_tokens=max_tokens)
    return None


def _anthropic_call(*, query: str, system: str, max_tokens: int) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": os.getenv("AIAL_QUERY_ANALYZER_MODEL", "claude-haiku-4-5-20251001"),
                "max_tokens": max_tokens,
                "system": system,
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
        return str(resp.json()["content"][0]["text"])
    except Exception as exc:
        logger.warning("QueryAnalyzer Anthropic call failed: %s", exc)
        return None


def _openai_call(*, query: str, system: str, max_tokens: int) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            json={
                "model": os.getenv("AIAL_QUERY_ANALYZER_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
                "max_tokens": max_tokens,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": query},
                ],
                "response_format": {"type": "json_object"},
            },
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            timeout=6.0,
        )
        resp.raise_for_status()
        return str(resp.json()["choices"][0]["message"]["content"])
    except Exception as exc:
        logger.warning("QueryAnalyzer OpenAI call failed: %s", exc)
        return None


# ─── Response parsing ─────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        return None


def _parse_queryplan(
    text: str,
    *,
    candidates: list[SemanticResolveCandidate],
) -> Any | None:
    """Parse LLM output to QueryPlan. Returns None on failure."""
    from orchestration.semantic.dsl import (
        DerivedMetric,
        Filter,
        MetricRef,
        OutputSpec,
        QueryPlan,
        Sort,
        TimeRange,
    )

    payload = _extract_json(text)
    if payload is None:
        logger.warning("QueryAnalyzer DSL: no JSON in LLM response")
        return None

    from orchestration.semantic.resolver import normalize_semantic_text
    valid_terms = {str(c.metric.get("term", "")) for c in candidates}
    # Normalized map: stripped term → canonical term (handles LLM dropping diacritics)
    normalized_to_canonical = {normalize_semantic_text(t): t for t in valid_terms}

    def _resolve_term(raw: str) -> str | None:
        """Resolve LLM term to catalog term. Returns None if not resolvable."""
        if raw in valid_terms:
            return raw
        normalized = normalize_semantic_text(raw)
        return normalized_to_canonical.get(normalized)

    try:
        raw_metrics = payload.get("metrics") or []
        metrics = []
        for m in raw_metrics:
            if not isinstance(m, dict):
                continue
            raw_term = str(m.get("term", ""))
            canonical = _resolve_term(raw_term)
            if canonical:
                metrics.append(MetricRef(term=canonical, alias=m.get("alias") or None))

        raw_filters = payload.get("filters") or []
        filters = []
        for f in raw_filters:
            if isinstance(f, dict) and f.get("column") and f.get("op"):
                filters.append(Filter(
                    column=str(f["column"]),
                    op=f["op"],
                    values=list(f.get("values") or []),
                ))

        raw_time = payload.get("time")
        time_range: TimeRange | None = None
        if isinstance(raw_time, dict) and (raw_time.get("start") or raw_time.get("grain") or raw_time.get("compare_to")):
            time_range = TimeRange(
                column=str(raw_time.get("column") or "PERIOD_DATE"),
                start=raw_time.get("start") or None,
                end=raw_time.get("end") or None,
                grain=raw_time.get("grain") or None,
                compare_to=raw_time.get("compare_to") or None,
                compare_start=raw_time.get("compare_start") or None,
                compare_end=raw_time.get("compare_end") or None,
            )

        raw_derived = payload.get("derived") or []
        derived = []
        for d in raw_derived:
            if isinstance(d, dict) and d.get("name") and d.get("expr") and d.get("inputs"):
                derived.append(DerivedMetric(
                    name=str(d["name"]),
                    expr=d["expr"],
                    inputs=[str(i) for i in d["inputs"]],
                    partition_by=[str(p) for p in (d.get("partition_by") or [])],
                ))

        raw_sort = payload.get("sort") or []
        sort = []
        for s in raw_sort:
            if isinstance(s, dict) and s.get("column"):
                sort.append(Sort(
                    column=str(s["column"]),
                    direction=s.get("direction") or "desc",
                ))

        raw_output = payload.get("output") or {}
        output = OutputSpec(
            format=raw_output.get("format") or "auto",
            chart_type=raw_output.get("chart_type") or None,
            show_total=bool(raw_output.get("show_total", False)),
            locale=raw_output.get("locale") or "vi",
        ) if isinstance(raw_output, dict) else OutputSpec()

        confidence = float(payload.get("confidence") or 0.7)
        needs_clarification = bool(payload.get("needs_clarification", False))
        if confidence < 0.55:
            needs_clarification = True

        return QueryPlan(
            metrics=metrics,
            filters=filters,
            group_by=[str(g) for g in (payload.get("group_by") or [])],
            time=time_range,
            derived=derived,
            sort=sort,
            limit=int(payload["limit"]) if payload.get("limit") else None,
            output=output,
            confidence=confidence,
            needs_clarification=needs_clarification,
            clarification_question=payload.get("clarification_question") or None,
            rationale=str(payload.get("rationale") or "dsl_v2_planner"),
        )
    except Exception as exc:
        logger.warning("QueryAnalyzer DSL parse failed: %s", exc)
        return None


def _parse_response_legacy(
    text: str,
    *,
    candidates: list[SemanticResolveCandidate],
) -> SemanticPlannerOutput | None:
    from orchestration.semantic.resolver import SemanticPlannerOutput

    payload = _extract_json(text)
    if payload is None:
        return None

    selected_term = payload.get("selected_term")
    valid_terms = {str(c.metric.get("term", "")) for c in candidates}
    if selected_term and str(selected_term) not in valid_terms:
        logger.warning("LLM selected unknown term %r — discarding", selected_term)
        selected_term = None

    needs_clarification = bool(payload.get("needs_clarification", False))
    confidence = float(payload.get("confidence", 0.0))
    if confidence < 0.55 and not needs_clarification:
        needs_clarification = True

    time_filter = _parse_time_filter_legacy(payload.get("time_filter"))

    _VALID_DIMS = {"REGION_CODE", "CHANNEL_CODE", "PRODUCT_CODE", "CATEGORY_NAME"}
    entity_filters: dict[str, str] = {}
    raw_ef = payload.get("entity_filters") or {}
    if isinstance(raw_ef, dict):
        for col, val in raw_ef.items():
            if col in _VALID_DIMS and val and str(val).strip():
                entity_filters[col] = str(val).strip().upper()
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


def _parse_time_filter_legacy(value: Any) -> dict[str, Any] | None:
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
        return None
    return result
