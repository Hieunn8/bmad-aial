"""Build and optionally execute governed SQL from semantic metadata."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from aial_shared.auth.keycloak import JWTClaims
from orchestration.semantic.time_parser import parse_time_expression
from orchestration.sql_governor.guardrails import QueryGovernor, SqlGuardrails

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class SemanticSqlPlan:
    sql: str
    parameters: dict[str, object]
    data_source: str
    metric_term: str
    qualified_table: str = ""  # e.g. "SYSTEM.AIAL_SALES_DAILY_V", used for meta-queries


@dataclass(frozen=True)
class SemanticSqlExecution:
    plan: SemanticSqlPlan | None
    rows: list[dict[str, object]]
    warning: str | None = None
    max_available_date: str | None = None  # set when rows empty due to time filter


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
    # Entity filters: specific dimension values (e.g. REGION_CODE = 'HCM')
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
            if not rows and _has_time_filter(plan.sql) and plan.qualified_table:
                max_available_date = _query_max_available_date(connection, plan)

        return SemanticSqlExecution(plan=plan, rows=rows, max_available_date=max_available_date)
    except Exception as exc:
        return SemanticSqlExecution(
            plan=plan,
            rows=[],
            warning=f"Không thực thi được SQL trên Oracle thật: {exc}",
        )


def _has_time_filter(sql: str) -> bool:
    return "PERIOD_DATE" in sql and ("DATE '" in sql or ">=" in sql)


def _query_max_available_date(connection: Any, plan: SemanticSqlPlan) -> str | None:
    """Run SELECT MAX/MIN(PERIOD_DATE) with only entity+dept filters (no time filter)."""
    try:
        # Build a minimal param dict: keep dept_scope and entity filters, drop time-bound params
        keep_params = {
            k: v for k, v in plan.parameters.items()
            if k not in ("date_start", "date_end")
        }
        # Reconstruct a lightweight WHERE from the original — strip PERIOD_DATE conditions
        where_clauses: list[str] = ["1 = 1"]
        if "DEPARTMENT_SCOPE = :department_scope" in plan.sql:
            where_clauses.append("DEPARTMENT_SCOPE = :department_scope")
        import re as _re
        for match in _re.finditer(r"(\w+_CODE)\s*=\s*:(\w+)", plan.sql):
            col, param = match.group(1), match.group(2)
            if param in keep_params:
                where_clauses.append(f"{col} = :{param}")
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


def build_and_execute_semantic_sql(
    *,
    query: str,
    semantic_context: list[dict[str, Any]] | None,
    principal: JWTClaims,
) -> SemanticSqlExecution:
    return execute_semantic_sql(
        build_semantic_sql_plan(query=query, semantic_context=semantic_context, principal=principal)
    )


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
    """Build WHERE clause for PERIOD_DATE.

    Uses pre-resolved start/end from the semantic plan when available (set by
    SemanticPlanner → parse_time_expression), otherwise calls parse_time_expression
    directly so ad-hoc SQL callers also get the LLM-enhanced parsing.
    """
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
