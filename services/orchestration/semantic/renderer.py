"""Renderer LLM (Pass 2) — formats query results according to QueryPlan.output.

Supports 4 output formats: number, table, report, chart_hint.
Falls back to deterministic templates when LLM is unavailable.

Env vars:
  AIAL_QUERY_ANALYZER_PROVIDER  — shared with planner ("anthropic" | "openai")
  AIAL_QUERY_RENDERER_MODEL     — model override (default: haiku / gpt-4.1-mini)
  ANTHROPIC_API_KEY / OPENAI_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

from orchestration.semantic.dsl import OutputFormat, QueryPlan

logger = logging.getLogger(__name__)

_DIM_LABELS: dict[str, str] = {
    "REGION_CODE": "Khu vực",
    "CHANNEL_CODE": "Kênh",
    "PRODUCT_CODE": "Sản phẩm",
    "CATEGORY_NAME": "Danh mục",
    "PERIOD_MONTH": "Tháng",
    "PERIOD_WEEK": "Tuần",
    "PERIOD_QUARTER": "Quý",
    "PERIOD_YEAR": "Năm",
    "PERIOD_DATE": "Ngày",
}

_RENDERER_SYSTEM = """\
You are AIAL's analytics result formatter. Locale: vi.

You receive:
- ORIGINAL QUESTION: {question}
- QUERY PLAN: {plan_json}
- ROWS: {rows_json}
- METADATA: {metadata_json}

OUTPUT: render the answer in format="{output_format}":

If format=number:
  Single sentence with the value, unit, scope (filters + time).
  Example: "Doanh thu HCM tháng 1/2026: **37.69 triệu VND**."

If format=table:
  Markdown table with header row labels in Vietnamese.
  Group_by columns first, then metric columns. Apply sort from plan.sort.
  Numbers: VND → tỷ/triệu (≥1B/≥1M); orders → integer with commas.
  If plan.output.show_total → append a "**Tổng cộng**" row.
  After the table, 1-2 sentences highlighting key insight (largest/smallest/notable diff).

If format=report:
  Structured Vietnamese text:
    1. **Tóm tắt** (1-2 câu chính)
    2. **Chi tiết** (bullet points with numbers in context)
    3. **So sánh / xu hướng** (if compare_to or grain)
    4. **Lưu ý** (data freshness, caveats)
  Length: 150-400 words.

If format=chart_hint:
  JSON only: {{"chart_type": ..., "x": "<dim>", "y": ["<metric>"], "series": null, "labels": {{}}}}

ALWAYS append at end (any format):
> Nguồn: {data_source_footer}

NEVER invent numbers not in ROWS.
NEVER reference filters/columns not in PLAN.
If ROWS empty → say so, suggest reasons (filter quá hẹp, kỳ chưa có dữ liệu). DO NOT fabricate.
"""


def render(
    *,
    question: str,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    metric: dict[str, Any],
) -> str:
    """Render query result to a user-facing answer string."""
    fmt = plan.effective_output_format(len(rows))

    if not rows and plan.rationale not in ("definition_only", "inventory"):
        return _render_no_data(plan=plan, metric=metric)

    if plan.rationale == "definition_only":
        return _render_definition(plan=plan, metric=metric)

    if plan.rationale == "inventory":
        return ""  # caller (query.py) handles inventory separately

    llm_answer = _call_renderer_llm(question=question, plan=plan, rows=rows, metric=metric, fmt=fmt)
    if llm_answer:
        return llm_answer

    return _deterministic_render(plan=plan, rows=rows, metric=metric, fmt=fmt)


# ── LLM renderer ──────────────────────────────────────────────────────────────

def _call_renderer_llm(
    *,
    question: str,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    metric: dict[str, Any],
    fmt: OutputFormat,
) -> str | None:
    provider = os.getenv("AIAL_QUERY_ANALYZER_PROVIDER", "").strip().lower()
    if not provider:
        return None

    metadata = _build_metadata(metric)
    data_source_footer = f"{metadata.get('data_source', '')} — {metadata.get('freshness_rule', 'cập nhật hằng ngày')}"
    system = _RENDERER_SYSTEM.format(
        question=question,
        plan_json=plan.model_dump_json(exclude_none=True),
        rows_json=json.dumps(rows[:100], ensure_ascii=False, default=str),
        metadata_json=json.dumps(metadata, ensure_ascii=False),
        output_format=fmt,
        data_source_footer=data_source_footer,
    )

    model_override = os.getenv("AIAL_QUERY_RENDERER_MODEL", "")
    if provider == "anthropic":
        return _anthropic_render(system=system, model_override=model_override)
    if provider == "openai":
        return _openai_render(system=system, model_override=model_override)
    return None


def _anthropic_render(*, system: str, model_override: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    model = model_override or "claude-haiku-4-5-20251001"
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": model,
                "max_tokens": 1500,
                "system": system,
                "messages": [{"role": "user", "content": "Render the answer now."}],
            },
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        return str(resp.json()["content"][0]["text"]).strip()
    except Exception as exc:
        logger.warning("Renderer Anthropic call failed: %s", exc)
        return None


def _openai_render(*, system: str, model_override: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    base = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = model_override or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            json={
                "model": model,
                "max_tokens": 1500,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": "Render the answer now."},
                ],
            },
            headers={"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
            timeout=10.0,
        )
        resp.raise_for_status()
        return str(resp.json()["choices"][0]["message"]["content"]).strip()
    except Exception as exc:
        logger.warning("Renderer OpenAI call failed: %s", exc)
        return None


# ── Deterministic fallbacks ───────────────────────────────────────────────────

def _deterministic_render(
    *,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    metric: dict[str, Any],
    fmt: OutputFormat,
) -> str:
    term = str(metric.get("term") or "metric")
    unit = str(metric.get("unit") or "").strip()
    formula = str(metric.get("formula") or "").strip()
    source_name = _metric_source_name(metric)
    freshness = str(metric.get("freshness_rule") or "cập nhật hằng ngày")

    if fmt == "number":
        return _render_number(plan=plan, rows=rows, term=term, unit=unit, formula=formula,
                              source_name=source_name, freshness=freshness)
    if fmt in ("table", "auto"):
        return _render_table(plan=plan, rows=rows, term=term, unit=unit,
                             source_name=source_name, freshness=freshness)
    if fmt == "report":
        return _render_report(plan=plan, rows=rows, term=term, unit=unit, formula=formula,
                              source_name=source_name, freshness=freshness)
    if fmt == "chart_hint":
        return _render_chart_hint(plan=plan, rows=rows, term=term)
    return _render_table(plan=plan, rows=rows, term=term, unit=unit,
                         source_name=source_name, freshness=freshness)


def _render_number(
    *,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    term: str,
    unit: str,
    formula: str,
    source_name: str,
    freshness: str,
) -> str:
    first_row = rows[0] if rows else {}
    value = _find_metric_value(first_row)
    rendered_value = _format_value(value, unit=unit)

    scope_parts: list[str] = []
    for f in plan.filters:
        label = _DIM_LABELS.get(f.column, f.column)
        vals = ", ".join(str(v) for v in f.values)
        scope_parts.append(f"{label}: {vals}")
    if plan.time and plan.time.start and plan.time.end:
        scope_parts.append(f"kỳ {plan.time.start} → {plan.time.end}")

    scope = f" ({', '.join(scope_parts)})" if scope_parts else ""
    lines = [
        f"**{term}**{scope}: {rendered_value}.",
        "",
    ]
    if formula:
        lines.append(f"Cách tính: {formula}.")
    lines.append(f"> Nguồn: {source_name} — {freshness}.")
    return "\n".join(lines)


def _render_table(
    *,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    term: str,
    unit: str,
    source_name: str,
    freshness: str,
) -> str:
    if not rows:
        return f"Không có dữ liệu cho `{term}`.\n\n> Nguồn: {source_name} — {freshness}."

    all_keys = list(rows[0].keys())
    dim_keys = [k for k in all_keys if k in _DIM_LABELS or k in plan.group_by]
    metric_keys = [k for k in all_keys if k not in dim_keys]
    ordered_keys = dim_keys + metric_keys

    headers = [_DIM_LABELS.get(k, k.replace("_", " ").title()) for k in ordered_keys]
    header_row = "| " + " | ".join(headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"

    data_rows: list[str] = []
    totals: dict[str, float] = {k: 0.0 for k in metric_keys}
    for row in rows:
        cells: list[str] = []
        for k in ordered_keys:
            val = row.get(k)
            if k in metric_keys:
                try:
                    fval = float(val)  # type: ignore[arg-type]
                    totals[k] += fval
                    cells.append(_format_value(fval, unit=unit))
                except (TypeError, ValueError):
                    cells.append(str(val) if val is not None else "—")
            else:
                cells.append(str(val) if val is not None else "—")
        data_rows.append("| " + " | ".join(cells) + " |")

    table_lines = [header_row, separator, *data_rows]

    if plan.output.show_total and metric_keys:
        total_cells: list[str] = []
        for k in ordered_keys:
            if k in metric_keys:
                total_cells.append(_format_value(totals[k], unit=unit))
            elif k == ordered_keys[0]:
                total_cells.append("**Tổng cộng**")
            else:
                total_cells.append("")
        table_lines.append("| " + " | ".join(total_cells) + " |")

    insight = _table_insight(rows=rows, metric_keys=metric_keys, dim_keys=dim_keys)
    footer = f"\n> Nguồn: {source_name} — {freshness}."
    return "\n".join(table_lines) + (f"\n\n{insight}" if insight else "") + footer


def _render_report(
    *,
    plan: QueryPlan,
    rows: list[dict[str, Any]],
    term: str,
    unit: str,
    formula: str,
    source_name: str,
    freshness: str,
) -> str:
    if not rows:
        return f"Không có dữ liệu `{term}` cho kỳ yêu cầu.\n\n> Nguồn: {source_name} — {freshness}."

    lines: list[str] = []
    # Tóm tắt
    total = sum(_safe_float(row, k) for row in rows for k in row if k not in plan.group_by)
    rendered_total = _format_value(total, unit=unit)
    time_scope = ""
    if plan.time and plan.time.start and plan.time.end:
        time_scope = f" từ {plan.time.start} đến {plan.time.end}"
    lines.append(f"**Tóm tắt**\n\n{term}{time_scope}: {rendered_total} tổng cộng trên {len(rows)} nhóm.")

    # Chi tiết
    lines.append("\n**Chi tiết**\n")
    for row in rows[:10]:
        metric_keys = [k for k in row if k not in _DIM_LABELS and k not in plan.group_by]
        dim_parts = [str(row.get(d, "")) for d in plan.group_by if d in row]
        val_parts = [_format_value(row.get(k), unit=unit) for k in metric_keys]
        label = " / ".join(dim_parts) if dim_parts else "(Tổng)"
        lines.append(f"- {label}: {', '.join(val_parts)}")

    # So sánh / xu hướng
    if plan.time and plan.time.compare_to:
        lines.append(f"\n**So sánh**\n\nSo sánh kỳ: {plan.time.compare_to}.")
    elif plan.derived:
        lines.append(f"\n**Xu hướng**\n\nĐã tính: {', '.join(d.name for d in plan.derived)}.")

    # Lưu ý
    lines.append(f"\n**Lưu ý**\n\n> Nguồn: {source_name} — {freshness}.")
    return "\n".join(lines)


def _render_chart_hint(*, plan: QueryPlan, rows: list[dict[str, Any]], term: str) -> str:
    x_col = plan.group_by[0] if plan.group_by else "PERIOD_DATE"
    y_cols = [m.alias or m.term for m in plan.metrics] or [term]
    chart_type = plan.output.chart_type or "bar"
    hint = {
        "chart_type": chart_type,
        "x": x_col,
        "y": y_cols,
        "series": plan.group_by[1] if len(plan.group_by) > 1 else None,
        "labels": {k: _DIM_LABELS.get(k, k) for k in plan.group_by},
        "row_count": len(rows),
    }
    return json.dumps(hint, ensure_ascii=False)


def _render_no_data(*, plan: QueryPlan, metric: dict[str, Any]) -> str:
    term = str(metric.get("term") or "metric")
    source_name = _metric_source_name(metric)
    filter_parts: list[str] = []
    for f in plan.filters:
        label = _DIM_LABELS.get(f.column, f.column)
        vals = ", ".join(str(v) for v in f.values)
        filter_parts.append(f"{label}: {vals}")
    if plan.time and plan.time.start and plan.time.end:
        filter_parts.append(f"kỳ {plan.time.start} → {plan.time.end}")
    filter_str = " | ".join(filter_parts)
    hint = "Thử bỏ bộ lọc thời gian hoặc mở rộng phạm vi để xem dữ liệu có sẵn."
    return (
        f"Không tìm thấy dữ liệu `{term}`"
        + (f" ({filter_str})" if filter_str else "")
        + f" trong nguồn `{source_name}`.\n{hint}"
    )


def _render_definition(*, plan: QueryPlan, metric: dict[str, Any]) -> str:
    term = str(metric.get("term") or "")
    definition = str(metric.get("definition") or "")
    formula = str(metric.get("formula") or "")
    unit = str(metric.get("unit") or "")
    freshness = str(metric.get("freshness_rule") or "")
    source_name = _metric_source_name(metric)
    lines = [f"**{term}**\n"]
    if definition:
        lines.append(definition)
    if formula:
        lines.append(f"\nCách tính: `{formula}`")
    if unit:
        lines.append(f"Đơn vị: {unit}")
    if freshness:
        lines.append(f"\n> {freshness}. Nguồn: {source_name}.")
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_metadata(metric: dict[str, Any]) -> dict[str, Any]:
    source = metric.get("source") if isinstance(metric.get("source"), dict) else {}
    return {
        "term": metric.get("term"),
        "definition": metric.get("definition"),
        "formula": metric.get("formula"),
        "unit": metric.get("unit"),
        "freshness_rule": metric.get("freshness_rule"),
        "data_source": source.get("data_source") or f"{source.get('schema', '')}.{source.get('table', '')}",
    }


def _metric_source_name(metric: dict[str, Any]) -> str:
    source = metric.get("source") if isinstance(metric.get("source"), dict) else {}
    ds = source.get("data_source")
    if ds:
        return str(ds)
    schema = source.get("schema", "")
    table = source.get("table", "")
    return f"{schema}.{table}" if schema and table else table or "oracle"


def _find_metric_value(row: dict[str, Any]) -> Any:
    for key in row:
        upper = key.upper()
        if "METRIC_VALUE" in upper or "NET_REVENUE" in upper or "GROSS_MARGIN" in upper \
                or "ORDER_COUNT" in upper or "BUDGET_AMOUNT" in upper:
            return row[key]
    return next(iter(row.values()), None) if row else None


def _format_value(value: Any, *, unit: str = "") -> str:
    if isinstance(value, (int, float)):
        unit_lower = unit.casefold()
        if unit_lower == "vnd":
            if abs(value) >= 1_000_000_000:
                return f"{value / 1_000_000_000:,.2f} tỷ VND"
            if abs(value) >= 1_000_000:
                return f"{value / 1_000_000:,.2f} triệu VND"
        suffix = f" {unit}" if unit else ""
        return f"{value:,.0f}{suffix}"
    if value is None:
        return "—"
    suffix = f" {unit}" if unit else ""
    return f"{value}{suffix}"


def _safe_float(row: dict[str, Any], key: str) -> float:
    try:
        return float(row[key])
    except (TypeError, ValueError, KeyError):
        return 0.0


def _table_insight(
    *,
    rows: list[dict[str, Any]],
    metric_keys: list[str],
    dim_keys: list[str],
) -> str:
    if not metric_keys or not rows:
        return ""
    key = metric_keys[0]
    try:
        sorted_rows = sorted(rows, key=lambda r: float(r.get(key) or 0), reverse=True)
        top = sorted_rows[0]
        bot = sorted_rows[-1]
        top_dim = " / ".join(str(top.get(d, "")) for d in dim_keys) if dim_keys else "Tổng"
        bot_dim = " / ".join(str(bot.get(d, "")) for d in dim_keys) if dim_keys else "Tổng"
        if top_dim != bot_dim:
            return f"Cao nhất: **{top_dim}** — thấp nhất: **{bot_dim}**."
    except (TypeError, ValueError):
        pass
    return ""
