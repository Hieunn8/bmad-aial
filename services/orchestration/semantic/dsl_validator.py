"""Validate a QueryPlan against the semantic catalog and principal claims.

Hard errors → reject (do not execute SQL).
Soft warnings → log but still execute.

See: docs/semantic/query-dsl-spec.md §3
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from orchestration.semantic.dsl import QueryPlan

logger = logging.getLogger(__name__)

_VALID_DIMS = {"REGION_CODE", "CHANNEL_CODE", "PRODUCT_CODE", "CATEGORY_NAME"}


class ValidationError(BaseModel):
    code: str
    field: str
    message: str


class ValidationResult(BaseModel):
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


def validate_plan(
    plan: QueryPlan,
    *,
    catalog: list[dict[str, Any]],
    principal: Any | None = None,   # JWTClaims — optional for unit tests
) -> ValidationResult:
    """Return ValidationResult. Check .valid before executing."""
    result = ValidationResult()
    _check_special_rationale(plan, result)
    if plan.rationale in ("definition_only", "latest_date", "inventory"):
        return result

    catalog_by_term = _catalog_index(catalog)
    resolved_metrics = _check_metrics(plan, catalog_by_term, principal, result)
    allowed_columns = _union_dimensions(resolved_metrics, catalog_by_term)
    _check_filters(plan, allowed_columns, result)
    _check_group_by(plan, allowed_columns, result)
    _check_time(plan, result)
    _check_derived(plan, result)
    _check_sort(plan, result)
    _check_limit(plan, result)
    _check_mixed_grain(resolved_metrics, catalog_by_term, result)
    _soft_checks(plan, result)
    return result


# ── Hard rule checkers ────────────────────────────────────────────────────────

def _check_special_rationale(plan: QueryPlan, result: ValidationResult) -> None:
    if plan.needs_clarification:
        return  # planner requests clarification — no further validation needed
    if not plan.metrics and plan.rationale not in ("definition_only", "latest_date", "inventory"):
        result.errors.append(ValidationError(
            code="no_metrics",
            field="metrics",
            message="Ít nhất 1 metric phải được chỉ định, trừ rationale=inventory/definition_only/latest_date.",
        ))


def _check_metrics(
    plan: QueryPlan,
    catalog_by_term: dict[str, dict[str, Any]],
    principal: Any | None,
    result: ValidationResult,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    seen_aliases: set[str] = set()
    for i, mref in enumerate(plan.metrics):
        field = f"metrics[{i}].term"
        if mref.term not in catalog_by_term:
            result.errors.append(ValidationError(
                code="unknown_metric",
                field=field,
                message=f"Metric '{mref.term}' không tồn tại trong catalog.",
            ))
            continue
        metric = catalog_by_term[mref.term]
        resolved.append(metric)

        if principal is not None:
            security = metric.get("security") or {}
            allowed_roles: set[str] = {str(r).strip() for r in security.get("allowed_roles", []) if str(r).strip()}
            principal_roles: set[str] = set(getattr(principal, "roles", []))
            if allowed_roles and not allowed_roles.intersection(principal_roles):
                result.errors.append(ValidationError(
                    code="metric_not_in_role",
                    field=field,
                    message=f"Metric '{mref.term}' không thuộc quyền của role hiện tại.",
                ))
            clearance = security.get("sensitivity_tier")
            principal_clearance = getattr(principal, "clearance", 999)
            if clearance is not None and int(clearance) > principal_clearance:
                result.errors.append(ValidationError(
                    code="clearance_too_low",
                    field=field,
                    message=f"Metric '{mref.term}' yêu cầu clearance {clearance}, bạn có {principal_clearance}.",
                ))

        alias = mref.alias or mref.term
        if alias in seen_aliases:
            result.errors.append(ValidationError(
                code="duplicate_alias",
                field=f"metrics[{i}].alias",
                message=f"Alias '{alias}' bị trùng lặp trong plan.",
            ))
        seen_aliases.add(alias)
    return resolved


def _check_filters(
    plan: QueryPlan,
    allowed_columns: set[str],
    result: ValidationResult,
) -> None:
    for i, f in enumerate(plan.filters):
        field = f"filters[{i}].column"
        if f.column not in allowed_columns:
            result.errors.append(ValidationError(
                code="column_not_in_metric",
                field=field,
                message=f"Cột '{f.column}' không nằm trong dimensions của các metric được chọn.",
            ))
        if f.op == "between" and len(f.values) != 2:
            result.errors.append(ValidationError(
                code="between_requires_two_values",
                field=f"filters[{i}].values",
                message=f"op='between' cần đúng 2 giá trị [lo, hi], nhận được {len(f.values)}.",
            ))
        if f.op in ("is_null", "not_null") and f.values:
            result.errors.append(ValidationError(
                code="null_check_has_values",
                field=f"filters[{i}].values",
                message=f"op='{f.op}' không nhận values.",
            ))


def _check_group_by(
    plan: QueryPlan,
    allowed_columns: set[str],
    result: ValidationResult,
) -> None:
    for i, col in enumerate(plan.group_by):
        if col not in allowed_columns:
            result.errors.append(ValidationError(
                code="column_not_in_metric",
                field=f"group_by[{i}]",
                message=f"Cột group_by '{col}' không nằm trong dimensions của metric.",
            ))


def _check_time(plan: QueryPlan, result: ValidationResult) -> None:
    if plan.time is None:
        if any(d.expr in ("diff", "pct_change", "yoy") for d in plan.derived):
            result.errors.append(ValidationError(
                code="compare_without_time",
                field="time",
                message="derived có expr so sánh kỳ nhưng time=null.",
            ))
        return
    t = plan.time
    if t.grain is not None and (t.start is None or t.end is None):
        result.errors.append(ValidationError(
            code="time_required_for_series",
            field="time.grain",
            message="time.grain được set nhưng thiếu time.start hoặc time.end.",
        ))
    if t.compare_to == "custom" and (t.compare_start is None or t.compare_end is None):
        result.errors.append(ValidationError(
            code="custom_compare_missing_range",
            field="time.compare_start",
            message="compare_to='custom' cần compare_start và compare_end.",
        ))


def _check_derived(plan: QueryPlan, result: ValidationResult) -> None:
    resolvable: set[str] = {(m.alias or m.term) for m in plan.metrics}
    # compare columns auto-generated by executor
    compare_cols = {f"{alias}_compare" for alias in resolvable}
    resolvable |= compare_cols
    for i, d in enumerate(plan.derived):
        for j, inp in enumerate(d.inputs):
            if inp not in resolvable:
                result.errors.append(ValidationError(
                    code="derived_input_unresolved",
                    field=f"derived[{i}].inputs[{j}]",
                    message=f"Input '{inp}' không resolve được từ metrics hoặc derived trước đó.",
                ))
        resolvable.add(d.name)  # subsequent derived can reference this


def _check_sort(plan: QueryPlan, result: ValidationResult) -> None:
    valid_cols = plan.all_output_columns()
    for i, s in enumerate(plan.sort):
        if s.column not in valid_cols:
            result.errors.append(ValidationError(
                code="sort_unknown_column",
                field=f"sort[{i}].column",
                message=f"Cột sort '{s.column}' không phải metric alias, group_by hay derived.",
            ))


def _check_limit(plan: QueryPlan, result: ValidationResult) -> None:
    if plan.limit is not None and plan.limit <= 0:
        result.errors.append(ValidationError(
            code="invalid_limit",
            field="limit",
            message=f"limit phải > 0, nhận được {plan.limit}.",
        ))


def _check_mixed_grain(
    resolved_metrics: list[dict[str, Any]],
    catalog_by_term: dict[str, dict[str, Any]],
    result: ValidationResult,
) -> None:
    grains: set[str] = set()
    for m in resolved_metrics:
        grain = str(m.get("grain") or m.get("time_grain") or "daily")
        grains.add(grain)
    if len(grains) > 1:
        result.errors.append(ValidationError(
            code="mixed_grain_metrics",
            field="metrics",
            message=f"Các metric có grain khác nhau ({grains}) không thể gộp vào 1 plan.",
        ))


# ── Soft rule checkers ────────────────────────────────────────────────────────

def _soft_checks(plan: QueryPlan, result: ValidationResult) -> None:
    if plan.limit is not None and not plan.sort:
        result.warnings.append(ValidationError(
            code="limit_without_sort",
            field="limit",
            message="limit được set nhưng sort rỗng — top-N không xác định thứ tự.",
        ))
    in_filters_multi = [f for f in plan.filters if f.op == "in" and len(f.values) >= 2]
    if in_filters_multi and not plan.group_by:
        cols = [f.column for f in in_filters_multi]
        result.warnings.append(ValidationError(
            code="in_filter_without_group_by",
            field="group_by",
            message=f"filter op='in' với ≥2 values trên {cols} nhưng group_by rỗng — nên thêm vào group_by.",
        ))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _catalog_index(catalog: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(m.get("term", "")): m for m in catalog if m.get("term")}


def _union_dimensions(
    resolved_metrics: list[dict[str, Any]],
    catalog_by_term: dict[str, dict[str, Any]],
) -> set[str]:
    dims: set[str] = set()
    for m in resolved_metrics:
        for d in m.get("dimensions", []):
            dims.add(str(d))
    dims.update(_VALID_DIMS)  # always allow standard dims for flexibility
    return dims
