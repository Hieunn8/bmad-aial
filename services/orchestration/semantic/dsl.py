"""Typed Query DSL for AIAL semantic layer.

LLM generates a QueryPlan JSON; validator checks it against the catalog;
executor maps it to Cube REST or Oracle SQL; renderer LLM formats the result.

See: docs/semantic/query-dsl-spec.md
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Filters ──────────────────────────────────────────────────────────────────

class Filter(BaseModel):
    """One predicate against a dimension column.

    Multi-value via op='in' / 'not_in'. Range via op='between' (values=[lo, hi]).
    Null checks via op='is_null'/'not_null' (values=[]).
    """
    model_config = ConfigDict(frozen=True)
    column: str
    op: Literal["eq", "ne", "in", "not_in", "between", "like", "is_null", "not_null"]
    values: list[str | int | float] = Field(default_factory=list)


# ── Time ─────────────────────────────────────────────────────────────────────

TimeGrain = Literal["day", "week", "month", "quarter", "year"]
ComparePeriod = Literal[
    "previous_period",
    "previous_year",
    "year_to_date_prev",
    "custom",
]


class TimeRange(BaseModel):
    """Time window for the query. end is EXCLUSIVE (last_included_day + 1)."""
    model_config = ConfigDict(frozen=True)
    column: str = "PERIOD_DATE"
    start: str | None = None           # ISO date YYYY-MM-DD; None = unbounded
    end: str | None = None             # ISO date YYYY-MM-DD, EXCLUSIVE
    grain: TimeGrain | None = None     # for time-series; None = aggregate
    compare_to: ComparePeriod | None = None
    compare_start: str | None = None   # required when compare_to='custom'
    compare_end: str | None = None


# ── Metrics ───────────────────────────────────────────────────────────────────

class MetricRef(BaseModel):
    """Reference to a governed metric in the catalog."""
    model_config = ConfigDict(frozen=True)
    term: str                          # exact registry term, e.g. "doanh thu thuần"
    alias: str | None = None           # output column name; default = term


# ── Derived calculations ──────────────────────────────────────────────────────

DerivedExpr = Literal[
    "ratio",           # numerator / denominator * 100  (tỷ trọng %)
    "diff",            # current - previous
    "pct_change",      # (current - previous) / previous * 100
    "yoy",             # current - same_period_last_year
    "share_of_total",  # value / SUM(value) over partition * 100
]


class DerivedMetric(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str                          # output column name
    expr: DerivedExpr
    inputs: list[str]                  # references to MetricRef.alias or .term
    partition_by: list[str] = Field(default_factory=list)  # for share_of_total


# ── Sort & limit ──────────────────────────────────────────────────────────────

class Sort(BaseModel):
    model_config = ConfigDict(frozen=True)
    column: str
    direction: Literal["asc", "desc"] = "desc"


# ── Output ────────────────────────────────────────────────────────────────────

OutputFormat = Literal[
    "number",      # 1 row, 1 metric → single formatted sentence
    "table",       # markdown table (default for >1 row OR breakdown)
    "report",      # structured text with sections + insights
    "chart_hint",  # JSON {chart_type, x, y, series} for frontend
    "auto",        # upgrade to table when >1 row, else number
]


class OutputSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    format: OutputFormat = "auto"
    chart_type: Literal["line", "bar", "pie", "stacked_bar"] | None = None
    show_total: bool = False
    locale: Literal["vi", "en"] = "vi"


# ── Top-level plan ────────────────────────────────────────────────────────────

class QueryPlan(BaseModel):
    """LLM-generated plan, validated against semantic catalog before execution."""
    model_config = ConfigDict(frozen=True)
    metrics: list[MetricRef] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    time: TimeRange | None = None
    derived: list[DerivedMetric] = Field(default_factory=list)
    sort: list[Sort] = Field(default_factory=list)
    limit: int | None = None
    output: OutputSpec = Field(default_factory=OutputSpec)
    # meta (set by planner LLM)
    confidence: float = 1.0
    needs_clarification: bool = False
    clarification_question: str | None = None
    rationale: str = ""

    def effective_output_format(self, row_count: int) -> OutputFormat:
        """Resolve 'auto' to concrete format based on actual row count."""
        fmt = self.output.format
        if fmt != "auto":
            return fmt
        return "table" if row_count > 1 else "number"

    def metric_aliases(self) -> dict[str, str]:
        """Map alias (or term) → term for all metrics."""
        return {(m.alias or m.term): m.term for m in self.metrics}

    def all_output_columns(self) -> set[str]:
        """All valid column names that can appear in sort/derived inputs."""
        cols: set[str] = set()
        cols.update(self.group_by)
        for m in self.metrics:
            cols.add(m.alias or m.term)
        for d in self.derived:
            cols.add(d.name)
        return cols


# ── Adapter: QueryPlan → legacy SemanticPlannerOutput dict ───────────────────

def queryplan_to_legacy_dict(plan: QueryPlan) -> dict[str, object]:
    """Lossy adapter for code that still reads metric['_semantic_plan'].

    Only covers simple eq filters → entity_filters. Does NOT cover op=in/not_in.
    Use only for audit log or backward-compat display — never in new code paths.
    """
    primary_filter = {
        f.column: f.values[0]
        for f in plan.filters
        if f.op == "eq" and f.values
    }
    time_filter: dict[str, object] | None = None
    if plan.time:
        time_filter = {
            "kind": "date_range",
            "start": plan.time.start,
            "end": plan.time.end,
        }
    intent = _derive_legacy_intent(plan)
    return {
        "selected_term": plan.metrics[0].term if plan.metrics else None,
        "intent": intent,
        "time_filter": time_filter,
        "dimensions": list(plan.group_by),
        "entity_filters": primary_filter,
        "confidence": plan.confidence,
        "needs_clarification": plan.needs_clarification,
        "clarification_question": plan.clarification_question,
        "rationale": plan.rationale or "queryplan_v2",
    }


def _derive_legacy_intent(plan: QueryPlan) -> str:
    if plan.rationale == "definition_only":
        return "definition"
    if plan.rationale == "latest_date":
        return "latest_date"
    if plan.group_by or any(f.op == "in" and len(f.values) > 1 for f in plan.filters):
        return "metric_breakdown"
    return "metric_value"
