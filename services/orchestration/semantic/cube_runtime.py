"""Cube Core runtime adapter for governed semantic queries."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.cube_model import infer_cube_dimension_name, infer_cube_name, infer_measure_name


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
        "filters": _cube_filters(cube_name, semantic_plan),
    }
    time_dimension = str(metric.get("time_dimension") or "").strip()
    if not time_dimension:
        time_dimension = _infer_time_dimension_from_metric(metric)
    time_payload = _cube_time_dimension(cube_name, time_dimension, semantic_plan)
    if time_payload:
        cube_query["timeDimensions"] = [time_payload]
    if row_limit is not None and row_limit > 0:
        cube_query["limit"] = row_limit
    return {key: value for key, value in cube_query.items() if value not in (None, [], {})}


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


def _cube_time_dimension(
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


def _cube_filters(cube_name: str, semantic_plan: dict[str, Any]) -> list[dict[str, str]]:
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
