"""Cube Core runtime adapter for governed semantic queries.

When metric['_query_plan'] is set (DSL v2), builds Cube query from QueryPlan.
Falls back to metric['_semantic_plan'] dict (legacy) otherwise.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

import httpx

from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.cube_model import infer_cube_dimension_name, infer_cube_name, infer_measure_name

if TYPE_CHECKING:
    from orchestration.semantic.dsl import QueryPlan


@dataclass(frozen=True)
class CubeRuntimeExecution:
    rows: list[dict[str, Any]]
    runtime_query: dict[str, Any] | None
    data_source: str | None
    generated_sql: str
    warning: str | None = None
    provenance: list[dict[str, Any]] = field(default_factory=list)
    max_available_date: str | None = None


def semantic_runtime_mode() -> str:
    return os.getenv("AIAL_SEMANTIC_RUNTIME", "legacy").strip().lower() or "legacy"


def is_cube_runtime_enabled() -> bool:
    return semantic_runtime_mode() == "cube"


class CubeSemanticRuntimeClient:
    def __init__(
        self,
        *,
        api_url: str | None = None,
        api_secret: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._api_url = (api_url or os.getenv("AIAL_CUBE_API_URL", "")).rstrip("/")
        self._api_secret = api_secret if api_secret is not None else os.getenv("CUBEJS_API_SECRET", "")
        self._timeout_seconds = timeout_seconds or float(os.getenv("AIAL_CUBE_TIMEOUT_SECONDS", "8"))

    @property
    def configured(self) -> bool:
        return bool(self._api_url and self._api_secret)

    def execute(
        self,
        *,
        query: str,
        semantic_context: list[dict[str, Any]] | None,
        principal: JWTClaims,
        row_limit: int | None = None,
    ) -> CubeRuntimeExecution:
        if not semantic_context:
            return CubeRuntimeExecution(rows=[], runtime_query=None, data_source=None, generated_sql="")
        metric = semantic_context[0]
        cube_query = build_cube_query(metric=metric, row_limit=row_limit)
        data_source = _metric_data_source(metric)
        if not self.configured:
            return CubeRuntimeExecution(
                rows=[],
                runtime_query=cube_query,
                data_source=data_source,
                generated_sql=_debug_sql(cube_query),
                warning="Cube Core chưa được cấu hình, chỉ sinh semantic runtime query.",
                provenance=[_provenance(metric=metric, principal=principal, cube_query=cube_query)],
            )
        try:
            response = httpx.post(
                f"{self._api_url}/load",
                json={"query": cube_query},
                headers={
                    "Authorization": f"Bearer {self._api_secret}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            rows = _extract_rows(body)
            rows = _apply_derived_postprocess(rows, metric)
            return CubeRuntimeExecution(
                rows=rows,
                runtime_query=cube_query,
                data_source=data_source,
                generated_sql=_debug_sql(cube_query),
                provenance=[_provenance(metric=metric, principal=principal, cube_query=cube_query)],
            )
        except Exception as exc:
            return CubeRuntimeExecution(
                rows=[],
                runtime_query=cube_query,
                data_source=data_source,
                generated_sql=_debug_sql(cube_query),
                warning=f"Không thực thi được Cube Core query: {exc}",
                provenance=[_provenance(metric=metric, principal=principal, cube_query=cube_query)],
            )


def build_cube_query(*, metric: dict[str, Any], row_limit: int | None = None) -> dict[str, Any]:
    query_plan: QueryPlan | None = metric.get("_query_plan")
    if query_plan is not None:
        return _build_cube_query_from_plan(metric=metric, plan=query_plan, row_limit=row_limit)
    return _build_cube_query_legacy(metric=metric, row_limit=row_limit)


# ── DSL v2: build from QueryPlan ──────────────────────────────────────────────

def _build_cube_query_from_plan(
    *,
    metric: dict[str, Any],
    plan: QueryPlan,
    row_limit: int | None,
) -> dict[str, Any]:
    cube_name = infer_cube_name(metric)
    measures: list[str] = []
    for mref in plan.metrics:
        # Resolve measure name via catalog lookup or infer from term
        measure_name = _infer_measure_for_term(metric, mref.term)
        measures.append(f"{cube_name}.{measure_name}")

    dimensions = [
        f"{cube_name}.{infer_cube_dimension_name(col)}"
        for col in plan.group_by
        if col
    ]

    filters = _cube_filters_from_plan(cube_name, plan)

    cube_query: dict[str, Any] = {
        "measures": measures or [f"{cube_name}.{infer_measure_name(metric)}"],
        "dimensions": dimensions,
        "filters": filters,
    }

    # Time dimension
    time_dimension_col = str(metric.get("time_dimension") or "PERIOD_DATE")
    time_payload = _cube_time_dimension_from_plan(cube_name, time_dimension_col, plan)
    if time_payload:
        cube_query["timeDimensions"] = [time_payload]

    # Sort
    if plan.sort:
        order: dict[str, str] = {}
        for s in plan.sort:
            # Resolve sort column to cube member name
            col = s.column
            if col in plan.group_by:
                member = f"{cube_name}.{infer_cube_dimension_name(col)}"
            else:
                member = f"{cube_name}.{_infer_measure_for_term(metric, col)}"
            order[member] = s.direction
        cube_query["order"] = order

    # Limit — plan.limit takes priority over row_limit arg
    effective_limit = plan.limit or row_limit
    if effective_limit and effective_limit > 0:
        cube_query["limit"] = effective_limit

    return {k: v for k, v in cube_query.items() if v not in (None, [], {})}


_TIME_COLS = {"PERIOD_DATE", "PERIOD_MONTH", "PERIOD_WEEK", "PERIOD_QUARTER", "PERIOD_YEAR"}


def _cube_filters_from_plan(cube_name: str, plan: QueryPlan) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    for f in plan.filters:
        if f.column.upper() in _TIME_COLS:
            continue  # time ranges go in timeDimensions, not filters
        member = f"{cube_name}.{infer_cube_dimension_name(f.column)}"
        if f.op == "eq":
            filters.append({"member": member, "operator": "equals", "values": [str(v) for v in f.values]})
        elif f.op == "ne":
            filters.append({"member": member, "operator": "notEquals", "values": [str(v) for v in f.values]})
        elif f.op == "in":
            filters.append({"member": member, "operator": "equals", "values": [str(v) for v in f.values]})
        elif f.op == "not_in":
            filters.append({"member": member, "operator": "notEquals", "values": [str(v) for v in f.values]})
        elif f.op == "between" and len(f.values) == 2:
            filters.append({"member": member, "operator": "gte", "values": [str(f.values[0])]})
            filters.append({"member": member, "operator": "lte", "values": [str(f.values[1])]})
        elif f.op == "like":
            filters.append({"member": member, "operator": "contains", "values": [str(v) for v in f.values]})
        elif f.op == "is_null":
            filters.append({"member": member, "operator": "notSet", "values": []})
        elif f.op == "not_null":
            filters.append({"member": member, "operator": "set", "values": []})
    return filters


def _cube_time_dimension_from_plan(
    cube_name: str,
    time_dimension: str,
    plan: QueryPlan,
) -> dict[str, Any] | None:
    if not plan.time:
        return None
    t = plan.time
    payload: dict[str, Any] = {
        "dimension": f"{cube_name}.{infer_cube_dimension_name(time_dimension)}",
    }
    if t.start and t.end:
        # DSL end is EXCLUSIVE; Cube dateRange is INCLUSIVE on both sides.
        # Subtract 1 day so Cube doesn't pull the next-period boundary date.
        inclusive_end = _exclusive_to_inclusive_end(t.end)
        payload["dateRange"] = [t.start, inclusive_end]
    if t.grain:
        payload["granularity"] = t.grain
    if t.compare_to and t.compare_to != "custom":
        payload["compareDateRange"] = _resolve_compare_date_range(t)
    return payload if (payload.get("dateRange") or payload.get("granularity")) else None


def _exclusive_to_inclusive_end(end_str: str) -> str:
    """Convert exclusive DSL end date to inclusive Cube end date (subtract 1 day)."""
    try:
        end = date.fromisoformat(end_str)
        return (end - timedelta(days=1)).isoformat()
    except ValueError:
        return end_str


def _resolve_compare_date_range(t: QueryPlan) -> list[list[str]] | None:
    if not t.start or not t.end:
        return None
    inclusive_end = _exclusive_to_inclusive_end(t.end)
    return [[t.start, inclusive_end]]


def _infer_measure_for_term(metric: dict[str, Any], term: str) -> str:
    catalog_measure = metric.get("_measure_name")
    if catalog_measure and metric.get("term") == term:
        return str(catalog_measure)
    return infer_measure_name(metric)


# ── Legacy: build from _semantic_plan dict ────────────────────────────────────

def _build_cube_query_legacy(*, metric: dict[str, Any], row_limit: int | None) -> dict[str, Any]:
    cube_name = infer_cube_name(metric)
    measure_name = infer_measure_name(metric)
    semantic_plan = metric.get("_semantic_plan") if isinstance(metric.get("_semantic_plan"), dict) else {}
    dimensions = [
        f"{cube_name}.{infer_cube_dimension_name(str(item))}"
        for item in semantic_plan.get("dimensions", [])
        if str(item).strip()
    ]
    cube_query: dict[str, Any] = {
        "measures": [f"{cube_name}.{measure_name}"],
        "dimensions": dimensions,
        "filters": _cube_filters_legacy(cube_name, semantic_plan),
    }
    time_dimension = str(metric.get("time_dimension") or "").strip()
    if not time_dimension:
        time_dimension = _infer_time_dimension_from_metric(metric)
    time_payload = _cube_time_dimension_legacy(cube_name, time_dimension, semantic_plan)
    if time_payload:
        cube_query["timeDimensions"] = [time_payload]
    if row_limit is not None and row_limit > 0:
        cube_query["limit"] = row_limit
    return {key: value for key, value in cube_query.items() if value not in (None, [], {})}


def _cube_time_dimension_legacy(
    cube_name: str,
    time_dimension: str,
    semantic_plan: dict[str, Any],
) -> dict[str, Any] | None:
    time_filter = semantic_plan.get("time_filter") if isinstance(semantic_plan, dict) else None
    if not time_dimension or not isinstance(time_filter, dict):
        return None
    if time_filter.get("kind") == "latest_record":
        return None
    payload: dict[str, Any] = {"dimension": f"{cube_name}.{infer_cube_dimension_name(time_dimension)}"}
    start = time_filter.get("start")
    end = time_filter.get("end")
    if start and end:
        payload["dateRange"] = [str(start), str(end)]
    if semantic_plan.get("intent") == "metric_breakdown":
        payload["granularity"] = "day"
    return payload


def _cube_filters_legacy(cube_name: str, semantic_plan: dict[str, Any]) -> list[dict[str, str]]:
    entity_filters = semantic_plan.get("entity_filters", {}) if isinstance(semantic_plan, dict) else {}
    filters: list[dict[str, str]] = []
    if isinstance(entity_filters, dict):
        for column, value in entity_filters.items():
            if value:
                filters.append(
                    {
                        "member": f"{cube_name}.{infer_cube_dimension_name(str(column))}",
                        "operator": "equals",
                        "values": [str(value)],
                    }
                )
    return filters


# ── Derived post-processing (not native to Cube) ──────────────────────────────

def _apply_derived_postprocess(rows: list[dict[str, Any]], metric: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply DerivedMetric calculations (ratio, share_of_total, etc.) on Python side."""
    query_plan: QueryPlan | None = metric.get("_query_plan")
    if not query_plan or not query_plan.derived:
        return rows
    result = [dict(row) for row in rows]
    for derived in query_plan.derived:
        result = _apply_single_derived(result, derived)
    return result


def _apply_single_derived(rows: list[dict[str, Any]], derived: Any) -> list[dict[str, Any]]:
    from orchestration.semantic.dsl import DerivedMetric
    d: DerivedMetric = derived
    result = [dict(row) for row in rows]
    if d.expr == "ratio" and len(d.inputs) >= 2:
        for row in result:
            num = _to_float(row.get(d.inputs[0]))
            den = _to_float(row.get(d.inputs[1]))
            row[d.name] = round(num / den * 100, 4) if den else None
    elif d.expr == "share_of_total" and d.inputs:
        total = sum(_to_float(row.get(d.inputs[0])) for row in result)
        for row in result:
            val = _to_float(row.get(d.inputs[0]))
            row[d.name] = round(val / total * 100, 4) if total else None
    elif d.expr in ("diff", "pct_change") and len(d.inputs) >= 2:
        for row in result:
            curr = _to_float(row.get(d.inputs[0]))
            prev = _to_float(row.get(d.inputs[1]))
            if d.expr == "diff":
                row[d.name] = curr - prev
            else:
                row[d.name] = round((curr - prev) / prev * 100, 4) if prev else None
    return result


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ── Shared helpers ────────────────────────────────────────────────────────────

def execute_cube_semantic_query(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    principal: JWTClaims,
    row_limit: int | None = None,
) -> CubeRuntimeExecution:
    return CubeSemanticRuntimeClient().execute(
        query=query,
        semantic_context=semantic_context,
        principal=principal,
        row_limit=row_limit,
    )


def _infer_time_dimension_from_metric(metric: dict[str, Any]) -> str:
    for dimension in metric.get("dimensions", []):
        column = str(dimension)
        if "DATE" in column.upper() or "TIME" in column.upper():
            return column
    return "PERIOD_DATE"


def _metric_data_source(metric: dict[str, Any]) -> str | None:
    source = metric.get("source") if isinstance(metric.get("source"), dict) else None
    if not source:
        return None
    return str(source.get("data_source") or source.get("table") or "") or None


def _extract_rows(body: dict[str, Any]) -> list[dict[str, Any]]:
    data = body.get("data")
    if isinstance(data, list):
        return [dict(row) for row in data if isinstance(row, dict)]
    result = body.get("result")
    if isinstance(result, dict) and isinstance(result.get("data"), list):
        return [dict(row) for row in result["data"] if isinstance(row, dict)]
    return []


def _debug_sql(cube_query: dict[str, Any]) -> str:
    return "CUBE_REST_QUERY " + repr(cube_query)


def _provenance(*, metric: dict[str, Any], principal: JWTClaims, cube_query: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime": "cube",
        "term": metric.get("term"),
        "cube_name": infer_cube_name(metric),
        "measure_name": infer_measure_name(metric),
        "active_version_id": metric.get("active_version_id") or metric.get("version_id"),
        "user_id": principal.sub,
        "department": principal.department,
        "query": cube_query,
    }
