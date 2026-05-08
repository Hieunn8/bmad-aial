"""Generate Cube Core data models from the governed semantic catalog."""

from __future__ import annotations

import os
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SUM_RE = re.compile(r"^\s*SUM\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*$", re.IGNORECASE)
_COUNT_RE = re.compile(r"^\s*COUNT\s*\(\s*([A-Za-z_][A-Za-z0-9_]*|\*)\s*\)\s*$", re.IGNORECASE)
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class CubeModelGenerationResult:
    model_dir: str
    files: list[str]
    metric_count: int
    errors: list[str]
    generated_at: str

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "model_dir": self.model_dir,
            "files": list(self.files),
            "metric_count": self.metric_count,
            "errors": list(self.errors),
            "generated_at": self.generated_at,
            "ok": self.ok,
        }


def cube_model_dir_from_env() -> Path:
    return Path(os.getenv("AIAL_CUBE_MODEL_DIR", "infra/cube/model"))


def infer_cube_name(metric: dict[str, Any]) -> str:
    explicit = str(metric.get("cube_name") or "").strip()
    if explicit:
        return _safe_name(explicit)
    source = metric.get("source") if isinstance(metric.get("source"), dict) else {}
    table = str(source.get("table") or "semantic_metrics")
    name = table
    if name.startswith("AIAL_"):
        name = name[5:]
    if name.endswith("_V"):
        name = name[:-2]
    return _safe_name(name)


def infer_measure_name(metric: dict[str, Any]) -> str:
    explicit = str(metric.get("measure_name") or "").strip()
    if explicit:
        return _safe_name(explicit)
    formula = str(metric.get("formula") or "")
    parsed = _parse_measure_formula(formula)
    if parsed is not None:
        _, column = parsed
        if column != "*":
            return _safe_name(column)
    return _safe_name(str(metric.get("term") or "metric"))


def infer_time_dimension(metric: dict[str, Any]) -> str | None:
    explicit = str(metric.get("time_dimension") or "").strip()
    if explicit:
        return explicit
    dimensions = [str(item) for item in metric.get("dimensions", []) if str(item).strip()]
    for dimension in dimensions:
        if "DATE" in dimension.upper() or "TIME" in dimension.upper():
            return dimension
    return "PERIOD_DATE" if "PERIOD_DATE" in dimensions else None


def infer_cube_dimension_name(column: str) -> str:
    return _safe_name(column)


def generate_cube_model_files(
    metrics: list[dict[str, Any]],
    *,
    model_dir: Path | None = None,
) -> CubeModelGenerationResult:
    target_dir = model_dir or cube_model_dir_from_env()
    target_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for metric in metrics:
        source = metric.get("source") if isinstance(metric.get("source"), dict) else None
        if not source:
            errors.append(f"{metric.get('term', '<unknown>')}: missing source")
            continue
        schema = str(source.get("schema") or "").strip()
        table = str(source.get("table") or "").strip()
        if not table or not _IDENTIFIER_RE.fullmatch(table):
            errors.append(f"{metric.get('term', '<unknown>')}: invalid source table")
            continue
        if schema and not _IDENTIFIER_RE.fullmatch(schema):
            errors.append(f"{metric.get('term', '<unknown>')}: invalid source schema")
            continue
        grouped[(infer_cube_name(metric), schema, table)].append(metric)

    written: list[str] = []
    for (cube_name, schema, table), cube_metrics in sorted(grouped.items()):
        content, cube_errors = _render_cube_yaml(
            cube_name=cube_name,
            schema=schema,
            table=table,
            metrics=cube_metrics,
        )
        errors.extend(cube_errors)
        path = target_dir / f"{cube_name}.yml"
        path.write_text(content, encoding="utf-8")
        written.append(str(path))

    return CubeModelGenerationResult(
        model_dir=str(target_dir),
        files=written,
        metric_count=sum(len(items) for items in grouped.values()),
        errors=errors,
        generated_at=datetime.now(UTC).isoformat(),
    )


def sync_active_semantics_to_cube_model() -> CubeModelGenerationResult:
    from orchestration.semantic.management import get_semantic_layer_service

    return generate_cube_model_files(get_semantic_layer_service().list_metrics())


def _render_cube_yaml(
    *,
    cube_name: str,
    schema: str,
    table: str,
    metrics: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    errors: list[str] = []
    table_name = f"{schema}.{table}" if schema else table
    dimension_columns = _collect_dimensions(metrics)
    primary_key_columns = _collect_primary_key(metrics, dimension_columns)
    lines = [
        "cubes:",
        f"  - name: {cube_name}",
        f"    sql_table: {table_name}",
        "",
        "    measures:",
    ]
    for metric in metrics:
        parsed = _parse_measure_formula(str(metric.get("formula") or ""))
        if parsed is None:
            errors.append(f"{metric.get('term', '<unknown>')}: unsupported formula {metric.get('formula')!r}")
            continue
        measure_type, column = parsed
        measure_name = infer_measure_name(metric)
        lines.extend(
            [
                f"      - name: {measure_name}",
                f"        type: {measure_type}",
            ]
        )
        if column != "*":
            lines.append(f"        sql: {column}")
        if metric.get("term"):
            lines.append(f"        title: {_quote_yaml(str(metric['term']))}")
        if metric.get("definition"):
            lines.append(f"        description: {_quote_yaml(str(metric['definition']))}")
    lines.extend(["", "    dimensions:"])
    if primary_key_columns:
        lines.extend(
            [
                "      - name: row_key",
                f"        sql: {_quote_yaml(_primary_key_sql(primary_key_columns))}",
                "        type: string",
                "        primary_key: true",
            ]
        )
    for column in dimension_columns:
        dimension_type = "time" if column == infer_time_dimension({"dimensions": [column]}) else "string"
        lines.extend(
            [
                f"      - name: {infer_cube_dimension_name(column)}",
                f"        sql: {column}",
                f"        type: {dimension_type}",
            ]
        )
    lines.append("")
    return "\n".join(lines), errors


def _collect_dimensions(metrics: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    for metric in metrics:
        configured = metric.get("cube_dimensions") or metric.get("dimensions") or []
        for item in configured:
            column = str(item).strip()
            if column and _IDENTIFIER_RE.fullmatch(column) and column not in columns:
                columns.append(column)
        time_dimension = infer_time_dimension(metric)
        if time_dimension and _IDENTIFIER_RE.fullmatch(time_dimension) and time_dimension not in columns:
            columns.insert(0, time_dimension)
    return columns


def _collect_primary_key(metrics: list[dict[str, Any]], dimensions: list[str]) -> list[str]:
    for metric in metrics:
        keys = [str(item).strip() for item in metric.get("primary_key", []) if str(item).strip()]
        if keys:
            return [key for key in keys if _IDENTIFIER_RE.fullmatch(key)]
    defaults = ["PERIOD_DATE", "REGION_CODE", "CHANNEL_CODE", "PRODUCT_CODE", "CATEGORY_NAME"]
    selected = [column for column in defaults if column in dimensions]
    return selected or dimensions[:1]


def _parse_measure_formula(formula: str) -> tuple[str, str] | None:
    sum_match = _SUM_RE.fullmatch(formula)
    if sum_match:
        return "sum", sum_match.group(1).upper()
    count_match = _COUNT_RE.fullmatch(formula)
    if count_match:
        column = count_match.group(1)
        return "count", column.upper() if column != "*" else "*"
    return None


def _primary_key_sql(columns: list[str]) -> str:
    parts = []
    for column in columns:
        if "DATE" in column.upper() or "TIME" in column.upper():
            parts.append(f"TO_CHAR({column}, 'YYYY-MM-DD')")
        else:
            parts.append(column)
    return " || '-' || ".join(parts)


def _safe_name(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    cleaned = re.sub(r"[^a-z0-9]+", "_", without_marks).strip("_")
    if not cleaned:
        return "metric"
    if cleaned[0].isdigit():
        return f"m_{cleaned}"
    return cleaned


def _quote_yaml(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
