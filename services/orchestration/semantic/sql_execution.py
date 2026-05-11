"""Build and optionally execute governed SQL from semantic metadata.

When metric['_query_plan'] is present (DSL v2), builds SQL from QueryPlan:
  - op=in/not_in/between/like/is_null/not_null
  - time.grain → GROUP BY TRUNC(PERIOD_DATE, ...)
  - sort → ORDER BY
  - limit → FETCH FIRST N ROWS ONLY
  - derived post-process (ratio, share_of_total, pct_change, diff)

Falls back to legacy _semantic_plan dict path otherwise.
"""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.dsl import Filter, QueryPlan, TimeRange
from orchestration.semantic.time_parser import parse_time_expression
from orchestration.sql_governor.guardrails import QueryGovernor, SqlGuardrails

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_GRAIN_EXPR: dict[str, tuple[str, str]] = {
    "day":     ("PERIOD_DATE",                      "PERIOD_DATE"),
    "week":    ("TRUNC(PERIOD_DATE, 'IW') AS PERIOD_WEEK",  "TRUNC(PERIOD_DATE, 'IW')"),
    "month":   ("TRUNC(PERIOD_DATE, 'MM') AS PERIOD_MONTH", "TRUNC(PERIOD_DATE, 'MM')"),
    "quarter": ("TRUNC(PERIOD_DATE, 'Q') AS PERIOD_QUARTER","TRUNC(PERIOD_DATE, 'Q')"),
    "year":    ("EXTRACT(YEAR FROM PERIOD_DATE) AS PERIOD_YEAR", "EXTRACT(YEAR FROM PERIOD_DATE)"),
}


@dataclass(frozen=True)
class SemanticSqlPlan:
    sql: str
    parameters: dict[str, object]
    data_source: str
    metric_term: str
    qualified_table: str = ""


@dataclass(frozen=True)
class SemanticSqlExecution:
    plan: SemanticSqlPlan | None
    rows: list[dict[str, object]]
    warning: str | None = None
    max_available_date: str | None = None


def build_semantic_sql_plan(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    principal: JWTClaims,
) -> SemanticSqlPlan | None:
    if not semantic_context:
        return None
    metric = semantic_context[0]
    source = metric.get("source")
    if not isinstance(source, dict):
        return None
    table_name = _qualified_table(source)
    if table_name is None:
        return None
    formula = str(metric.get("formula", "")).strip()
    if not formula:
        return None

    query_plan: QueryPlan | None = metric.get("_query_plan")
    if query_plan is not None:
        return _build_sql_from_plan(
            query=query,
            metric=metric,
            plan=query_plan,
            table_name=table_name,
            formula=formula,
            source=source,
            principal=principal,
        )
    return _build_sql_legacy(
        query=query,
        metric=metric,
        table_name=table_name,
        formula=formula,
        source=source,
        principal=principal,
    )


# ── DSL v2: build from QueryPlan ──────────────────────────────────────────────

def _build_sql_from_plan(
    *,
    query: str,
    metric: dict[str, Any],
    plan: QueryPlan,
    table_name: str,
    formula: str,
    source: dict[str, Any],
    principal: JWTClaims,
) -> SemanticSqlPlan | None:
    parameters: dict[str, object] = {}
    where_parts: list[str] = ["1 = 1"]

    # Security: department scope
    if "admin" not in principal.roles and principal.department:
        where_parts.append("DEPARTMENT_SCOPE = :department_scope")
        parameters["department_scope"] = principal.department

    # Handle special rationale: latest_date
    if plan.rationale == "latest_date":
        sql = f"SELECT MAX(PERIOD_DATE) AS LATEST_DATE FROM {table_name} WHERE {' AND '.join(where_parts)}"
        governed = QueryGovernor.apply(sql)
        guard = SqlGuardrails.validate(governed)
        if not guard.allowed:
            raise ValueError(f"generated semantic SQL blocked: {guard.code} {guard.reason}")
        return SemanticSqlPlan(
            sql=governed,
            parameters=parameters,
            data_source=str(source.get("data_source") or table_name),
            metric_term=str(metric.get("term") or "semantic metric"),
            qualified_table=table_name,
        )

    # SELECT: group_by columns + grain + metrics
    select_parts: list[str] = []
    group_by_exprs: list[str] = []

    # Dimension columns from group_by
    for col in plan.group_by:
        if _IDENTIFIER_RE.fullmatch(col):
            select_parts.append(col)
            group_by_exprs.append(col)

    # Grain time bucket
    if plan.time and plan.time.grain:
        grain = plan.time.grain
        if grain in _GRAIN_EXPR:
            sel_expr, grp_expr = _GRAIN_EXPR[grain]
            select_parts.append(sel_expr)
            group_by_exprs.append(grp_expr)

    # Metrics formulas — one per MetricRef
    for mref in plan.metrics:
        col_alias = (mref.alias or mref.term).upper().replace(" ", "_")
        select_parts.append(f"{formula} AS {col_alias}")

    select_sql = ", ".join(select_parts) if select_parts else f"{formula} AS METRIC_VALUE"

    # Filters — skip time-dimension columns (handled by plan.time, not filters)
    _TIME_COLS = {"PERIOD_DATE", "PERIOD_MONTH", "PERIOD_WEEK", "PERIOD_QUARTER", "PERIOD_YEAR"}
    for i, f in enumerate(plan.filters):
        if f.column.upper() in _TIME_COLS:
            continue  # LLM sometimes puts date ranges in filters — ignore, use plan.time
        if not _IDENTIFIER_RE.fullmatch(f.column):
            continue
        frag, params = _filter_to_sql(f, i)
        if frag:
            where_parts.append(frag)
            parameters.update(params)

    # Time filter
    if plan.time:
        time_frag = _time_to_sql(plan.time)
        if time_frag:
            where_parts.append(time_frag)
    else:
        # Legacy fallback: parse time from raw query text
        parsed = parse_time_expression(query)
        clause = parsed.to_sql_clause()
        if clause:
            where_parts.append(clause)

    # Assemble SQL
    sql = f"SELECT {select_sql} FROM {table_name} WHERE {' AND '.join(where_parts)}"

    if group_by_exprs:
        sql += f" GROUP BY {', '.join(group_by_exprs)}"

    # Sort
    if plan.sort:
        order_parts: list[str] = []
        for s in plan.sort:
            col = s.column.upper().replace(" ", "_")
            direction = "ASC" if s.direction == "asc" else "DESC"
            order_parts.append(f"{col} {direction}")
        if order_parts:
            sql += f" ORDER BY {', '.join(order_parts)}"

    # Limit
    if plan.limit and plan.limit > 0:
        sql += f" FETCH FIRST {plan.limit} ROWS ONLY"

    governed = QueryGovernor.apply(sql)
    guard = SqlGuardrails.validate(governed)
    if not guard.allowed:
        raise ValueError(f"generated semantic SQL blocked: {guard.code} {guard.reason}")

    return SemanticSqlPlan(
        sql=governed,
        parameters=parameters,
        data_source=str(source.get("data_source") or table_name),
        metric_term=str(metric.get("term") or "semantic metric"),
        qualified_table=table_name,
    )


def _filter_to_sql(f: Filter, index: int) -> tuple[str, dict[str, object]]:
    col = f.column
    params: dict[str, object] = {}
    prefix = f"{col.lower()}_f{index}"
    if f.op == "eq" and f.values:
        k = f"{prefix}_0"
        params[k] = str(f.values[0]).upper()
        return f"{col} = :{k}", params
    if f.op == "ne" and f.values:
        k = f"{prefix}_0"
        params[k] = str(f.values[0]).upper()
        return f"{col} != :{k}", params
    if f.op == "in" and f.values:
        keys = [f"{prefix}_{j}" for j in range(len(f.values))]
        for key, val in zip(keys, f.values):
            params[key] = str(val).upper()
        placeholders = ", ".join(f":{k}" for k in keys)
        return f"{col} IN ({placeholders})", params
    if f.op == "not_in" and f.values:
        keys = [f"{prefix}_{j}" for j in range(len(f.values))]
        for key, val in zip(keys, f.values):
            params[key] = str(val).upper()
        placeholders = ", ".join(f":{k}" for k in keys)
        return f"{col} NOT IN ({placeholders})", params
    if f.op == "between" and len(f.values) == 2:
        lo_key = f"{prefix}_lo"
        hi_key = f"{prefix}_hi"
        params[lo_key] = f.values[0]
        params[hi_key] = f.values[1]
        return f"{col} BETWEEN :{lo_key} AND :{hi_key}", params
    if f.op == "like" and f.values:
        k = f"{prefix}_0"
        params[k] = f"%{f.values[0]}%"
        return f"{col} LIKE :{k}", params
    if f.op == "is_null":
        return f"{col} IS NULL", params
    if f.op == "not_null":
        return f"{col} IS NOT NULL", params
    return "", params


def _time_to_sql(t: TimeRange) -> str | None:
    if t.start and t.end:
        return f"PERIOD_DATE >= DATE '{t.start}' AND PERIOD_DATE < DATE '{t.end}'"
    return None


# ── Legacy path (from _semantic_plan dict) ────────────────────────────────────

def _build_sql_legacy(
    *,
    query: str,
    metric: dict[str, Any],
    table_name: str,
    formula: str,
    source: dict[str, Any],
    principal: JWTClaims,
) -> SemanticSqlPlan | None:
    semantic_plan = metric.get("_semantic_plan")
    plan_payload = semantic_plan if isinstance(semantic_plan, dict) else None
    planned_time = plan_payload.get("time_filter") if plan_payload else None
    is_latest_record = (isinstance(planned_time, dict) and planned_time.get("kind") == "latest_record") or (
        not planned_time and _is_latest_date_query(query)
    )
    if is_latest_record:
        select_sql = "MAX(PERIOD_DATE) AS LATEST_DATE"
        group_by: list[str] = []
    else:
        select_parts, group_by = _dimension_selectors(query, plan_payload)
        select_sql = ", ".join([*select_parts, f"{formula} AS METRIC_VALUE"])
    where_parts = ["1 = 1"]
    parameters: dict[str, object] = {}
    if "admin" not in principal.roles and principal.department:
        where_parts.append("DEPARTMENT_SCOPE = :department_scope")
        parameters["department_scope"] = principal.department
    raw_entity_filters = plan_payload.get("entity_filters", {}) if plan_payload else {}
    if isinstance(raw_entity_filters, dict):
        for col, val in raw_entity_filters.items():
            if val and _IDENTIFIER_RE.fullmatch(str(col)):
                param_key = f"{col.lower()}_ef"
                where_parts.append(f"{col} = :{param_key}")
                parameters[param_key] = str(val).upper()
    period_filter = _period_filter(query, plan_payload)
    if period_filter is not None:
        where_parts.append(period_filter)

    sql = f"SELECT {select_sql} FROM {table_name} WHERE {' AND '.join(where_parts)}"
    if group_by:
        sql += f" GROUP BY {', '.join(group_by)}"
    governed = QueryGovernor.apply(sql)
    guard = SqlGuardrails.validate(governed)
    if not guard.allowed:
        raise ValueError(f"generated semantic SQL blocked: {guard.code} {guard.reason}")
    return SemanticSqlPlan(
        sql=governed,
        parameters=parameters,
        data_source=str(source.get("data_source") or table_name),
        metric_term=str(metric.get("term") or "semantic metric"),
        qualified_table=table_name or "",
    )


# ── Execution ─────────────────────────────────────────────────────────────────

def execute_semantic_sql(plan: SemanticSqlPlan | None) -> SemanticSqlExecution:
    if plan is None:
        return SemanticSqlExecution(plan=None, rows=[])
    username = os.getenv("AIAL_ORACLE_USERNAME", "").strip()
    password = os.getenv("AIAL_ORACLE_PASSWORD", "").strip()
    dsn = os.getenv("AIAL_ORACLE_DSN", "").strip()
    if not username or not password or not dsn:
        return SemanticSqlExecution(
            plan=plan,
            rows=[],
            warning="Oracle chưa được cấu hình, chỉ sinh SQL từ semantic.",
        )
    try:
        import oracledb

        with oracledb.connect(user=username, password=password, dsn=dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(plan.sql, plan.parameters)
                columns = [str(col[0]) for col in cursor.description or []]
                rows = [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

            max_available_date: str | None = None
            if (not rows or not _has_meaningful_values(rows)) and _has_time_filter(plan.sql) and plan.qualified_table:
                max_available_date = _query_max_available_date(connection, plan)

        return SemanticSqlExecution(plan=plan, rows=rows, max_available_date=max_available_date)
    except Exception as exc:
        return SemanticSqlExecution(
            plan=plan,
            rows=[],
            warning=f"Không thực thi được SQL trên Oracle thật: {exc}",
        )


def build_and_execute_semantic_sql(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    principal: JWTClaims,
) -> SemanticSqlExecution:
    return execute_semantic_sql(
        build_semantic_sql_plan(query=query, semantic_context=semantic_context, principal=principal)
    )


# ── Shared helpers ────────────────────────────────────────────────────────────

def _has_time_filter(sql: str) -> bool:
    return "PERIOD_DATE" in sql and ("DATE '" in sql or ">=" in sql)


def _has_meaningful_values(rows: list[dict[str, object]]) -> bool:
    for row in rows:
        for value in row.values():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return True
    return False


def _query_max_available_date(connection: Any, plan: SemanticSqlPlan) -> str | None:
    try:
        keep_params = {
            k: v for k, v in plan.parameters.items()
            if k not in ("date_start", "date_end")
        }
        where_clauses: list[str] = ["1 = 1"]
        if "DEPARTMENT_SCOPE = :department_scope" in plan.sql:
            where_clauses.append("DEPARTMENT_SCOPE = :department_scope")
        import re as _re
        for match in _re.finditer(r"(\w+_CODE)\s*(=|IN)\s*[:(\w]", plan.sql):
            col = match.group(1)
            for pk, pv in keep_params.items():
                if col.lower() in pk:
                    where_clauses.append(f"{col} = :{pk}")
                    break
        meta_sql = (
            f"SELECT MAX(PERIOD_DATE) AS MAX_DATE, MIN(PERIOD_DATE) AS MIN_DATE "
            f"FROM {plan.qualified_table} WHERE {' AND '.join(where_clauses)}"
        )
        with connection.cursor() as cur:
            cur.execute(meta_sql, keep_params)
            row = cur.fetchone()
        if row and row[0] is not None:
            max_d = str(row[0])[:10]
            min_d = str(row[1])[:10] if row[1] else None
            return f"{min_d} đến {max_d}" if min_d else max_d
    except Exception:
        pass
    return None


def _qualified_table(source: dict[str, object]) -> str | None:
    table = str(source.get("table") or "").strip()
    schema = str(source.get("schema") or "").strip()
    if not table or not _IDENTIFIER_RE.fullmatch(table):
        return None
    if schema:
        if not _IDENTIFIER_RE.fullmatch(schema):
            return None
        return f"{schema}.{table}"
    return table


def _dimension_selectors(query: str, semantic_plan: dict[str, Any] | None = None) -> tuple[list[str], list[str]]:
    normalized = _match_text(query)
    selectors: list[tuple[str, str]] = []
    planned_dimensions = set(semantic_plan.get("dimensions", [])) if semantic_plan else set()
    if "REGION_CODE" in planned_dimensions and not any(select == "REGION_CODE" for select, _ in selectors):
        selectors.append(("REGION_CODE", "REGION_CODE"))
    if "CHANNEL_CODE" in planned_dimensions and not any(select == "CHANNEL_CODE" for select, _ in selectors):
        selectors.append(("CHANNEL_CODE", "CHANNEL_CODE"))
    if "PRODUCT_CODE" in planned_dimensions and not any(select == "PRODUCT_CODE" for select, _ in selectors):
        selectors.append(("PRODUCT_CODE", "PRODUCT_CODE"))
    if "CATEGORY_NAME" in planned_dimensions and not any(select == "CATEGORY_NAME" for select, _ in selectors):
        selectors.append(("CATEGORY_NAME", "CATEGORY_NAME"))
    if any(token in normalized for token in ("khu vực", "khu vuc", "vùng", "vung", "region", "tỉnh", "thành phố")):
        selectors.append(("REGION_CODE", "REGION_CODE"))
    if any(token in normalized for token in ("kênh", "kenh", "channel")):
        selectors.append(("CHANNEL_CODE", "CHANNEL_CODE"))
    if any(token in normalized for token in ("sản phẩm", "san pham", "product")):
        selectors.append(("PRODUCT_CODE", "PRODUCT_CODE"))
    if any(token in normalized for token in ("ngành hàng", "danh mục", "category")):
        selectors.append(("CATEGORY_NAME", "CATEGORY_NAME"))
    if any(token in normalized for token in ("tháng", "month")):
        selectors.append(("TRUNC(PERIOD_DATE, 'MM') AS PERIOD_MONTH", "TRUNC(PERIOD_DATE, 'MM')"))
    elif any(token in normalized for token in ("ngày", "daily", "date")):
        selectors.append(("PERIOD_DATE", "PERIOD_DATE"))
    return [select for select, _ in selectors], [group for _, group in selectors]


def _period_filter(query: str, semantic_plan: dict[str, Any] | None = None) -> str | None:
    planned_time = semantic_plan.get("time_filter") if semantic_plan else None
    if isinstance(planned_time, dict):
        kind = planned_time.get("kind", "")
        if kind == "latest_record":
            return None
        start = planned_time.get("start")
        end = planned_time.get("end")
        if start and end:
            return f"PERIOD_DATE >= DATE '{start}' AND PERIOD_DATE < DATE '{end}'"
    parsed = parse_time_expression(query)
    return parsed.to_sql_clause()


def _is_latest_date_query(query: str) -> bool:
    return parse_time_expression(query).kind == "latest_record"


def _match_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    without_marks = without_marks.replace("đ", "d")
    return " ".join(without_marks.replace("đ", "d").split())


