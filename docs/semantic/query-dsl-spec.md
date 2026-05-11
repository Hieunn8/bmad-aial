# AIAL Query DSL Spec — Phase 1

**Status**: Draft for review
**Owner**: Semantic Layer
**Last updated**: 2026-05-08
**Phase**: 1 of 3 (Spec → Implement → Migrate)

---

## 1. Mục tiêu & tại sao đổi kiến trúc

### 1.1 Vấn đề hiện tại

`SemanticPlannerOutput` (xem `services/orchestration/semantic/resolver.py:24-50`) thiết kế quanh một enum cứng:

```
intent ∈ {"metric_value", "metric_breakdown", "definition", "latest_date"}
entity_filters: dict[str, str]   # ⚠ chỉ 1 giá trị / dimension
```

Hệ quả:

| Câu hỏi | Hệ thống hiện tại | Đúng phải là |
|---|---|---|
| "so sánh doanh thu HCM và HN tháng 1" | trả 1 con số HCM | bảng 2 dòng |
| "top 5 sản phẩm doanh thu cao nhất" | không hiểu được | bảng top-5 |
| "doanh thu tháng này so với tháng trước" | chỉ trả tháng này | bảng / text so sánh |
| "tỷ trọng kênh online trong tổng doanh thu" | chỉ trả số online | tỷ lệ % |
| "doanh thu và lợi nhuận theo tháng" | phải hỏi tách 2 lần | 1 bảng 2 cột |

Cứ thêm intent mới → phải sửa code, viết test, deploy. Không scale.

### 1.2 Giải pháp: thay enum bằng **typed DSL**

LLM sinh trực tiếp một query plan có cấu trúc, validator kiểm tra cứng theo catalog, executor map sang Cube REST hoặc Oracle SQL, renderer LLM trình bày kết quả theo định dạng người dùng yêu cầu.

```
User question
    │
    ▼
[Planner LLM] ──► QueryPlan (DSL JSON)
    │
    ▼
[Validator] ──► reject metric/column ngoài catalog, kiểm role/sensitivity
    │
    ▼
[Executor] ──► Cube REST (preferred) | Oracle SQL (fallback)
    │
    ▼
[Renderer LLM] ──► answer (number | table | report | chart_hint)
```

---

## 2. DSL schema (Pydantic v2)

```python
# services/orchestration/semantic/dsl.py
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


# ── Filters ───────────────────────────────────────────────────────────
class Filter(BaseModel):
    """One predicate against a dimension column.
    Multi-value via op='in' / 'not_in'. Range via op='between'."""
    model_config = ConfigDict(frozen=True)
    column: str                                # must be in metric.dimensions
    op: Literal["eq", "ne", "in", "not_in", "between", "like", "is_null", "not_null"]
    values: list[str | int | float] = Field(default_factory=list)
    # for 'between': values=[low, high]
    # for 'is_null'/'not_null': values=[]


# ── Time ──────────────────────────────────────────────────────────────
TimeGrain = Literal["day", "week", "month", "quarter", "year"]
ComparePeriod = Literal[
    "previous_period",      # tháng này → tháng trước
    "previous_year",        # tháng 5/2026 → tháng 5/2025
    "year_to_date_prev",    # YTD năm nay → YTD năm trước
    "custom",
]

class TimeRange(BaseModel):
    """Time window for the query."""
    model_config = ConfigDict(frozen=True)
    column: str = "PERIOD_DATE"            # metric's time_dimension
    start: str | None = None               # ISO date YYYY-MM-DD; None = unbounded
    end: str | None = None                 # ISO date YYYY-MM-DD, EXCLUSIVE
    grain: TimeGrain | None = None         # for time-series; None = aggregate
    compare_to: ComparePeriod | None = None
    compare_start: str | None = None       # required when compare_to='custom'
    compare_end: str | None = None


# ── Metrics ───────────────────────────────────────────────────────────
class MetricRef(BaseModel):
    """Reference to a governed metric in the catalog."""
    model_config = ConfigDict(frozen=True)
    term: str                              # exact registry term, e.g. "doanh thu thuần"
    alias: str | None = None               # output column name; default = term


# ── Derived calculations ──────────────────────────────────────────────
DerivedExpr = Literal[
    "ratio",          # numerator / denominator * 100  (tỷ trọng %)
    "diff",           # current - previous
    "pct_change",     # (current - previous) / previous * 100
    "yoy",            # current - same_period_last_year
    "share_of_total", # value / SUM(value) over partition * 100
]

class DerivedMetric(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str                              # output column name
    expr: DerivedExpr
    inputs: list[str]                      # references to MetricRef.alias or .term
    partition_by: list[str] = Field(default_factory=list)  # for share_of_total


# ── Sort & limit ──────────────────────────────────────────────────────
class Sort(BaseModel):
    model_config = ConfigDict(frozen=True)
    column: str                            # metric alias OR dimension column
    direction: Literal["asc", "desc"] = "desc"


# ── Output ────────────────────────────────────────────────────────────
OutputFormat = Literal[
    "number",      # 1 row, 1 metric → "Doanh thu HCM tháng 1: 37.69 triệu VND"
    "table",       # markdown table (default for >1 row OR breakdown)
    "report",      # text dài + insight + so sánh + suggestion
    "chart_hint",  # JSON {chart_type, x, y, series} — frontend renders
]

class OutputSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    format: OutputFormat = "number"
    chart_type: Literal["line", "bar", "pie", "stacked_bar"] | None = None
    show_total: bool = False               # add "Tổng cộng" row to table
    locale: Literal["vi", "en"] = "vi"


# ── Top-level plan ────────────────────────────────────────────────────
class QueryPlan(BaseModel):
    """LLM-generated plan, validated against semantic catalog before execution."""
    model_config = ConfigDict(frozen=True)
    metrics: list[MetricRef]               # ≥1
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)     # dim column names
    time: TimeRange | None = None
    derived: list[DerivedMetric] = Field(default_factory=list)
    sort: list[Sort] = Field(default_factory=list)
    limit: int | None = None
    output: OutputSpec = Field(default_factory=OutputSpec)
    # ── meta (set by planner LLM) ──
    confidence: float = 1.0                # 0..1
    needs_clarification: bool = False
    clarification_question: str | None = None
    rationale: str = ""
```

**Invariants** (enforced by validator):
- `metrics` ≥ 1, mỗi term ∈ governed catalog
- `filters[].column` ∈ union(metrics[].dimensions)
- `group_by[]` ∈ union(metrics[].dimensions)
- `time.column` = metric's time dimension (default `PERIOD_DATE`)
- `derived[].inputs` resolve được trong `metrics[].alias|term` hoặc `derived[].name`
- `sort[].column` ∈ metric aliases ∪ group_by ∪ derived names
- `limit > 0` khi có `sort`

---

## 3. Validator rules

```python
# services/orchestration/semantic/dsl_validator.py
class ValidationError(BaseModel):
    code: str        # "unknown_metric" | "column_not_in_metric" | ...
    field: str       # dotted path: "metrics[0].term"
    message: str

def validate_plan(plan: QueryPlan, *, principal: JWTClaims, catalog: list[dict]) -> list[ValidationError]:
    """Return [] on success, list of errors otherwise."""
```

**Hard rules** (any violation → reject, không chạy SQL):

| Code | Khi nào | Ví dụ |
|---|---|---|
| `unknown_metric` | term không tồn tại trong catalog | LLM hallucinate "doanh thu net" |
| `metric_not_in_role` | term không nằm trong `metric_allowlist` của role | sales_analyst hỏi "lợi nhuận ròng" |
| `clearance_too_low` | `metric.security.sensitivity_tier > principal.clearance` | tier-3 metric với clearance=2 |
| `column_not_in_metric` | filter/group_by column không có trong dimensions metric | `region_code` của bảng HR vào doanh thu |
| `mixed_grain_metrics` | 2 metric có `grain` khác nhau gộp vào 1 plan | "doanh thu" (daily) + "headcount" (monthly) |
| `time_required_for_series` | `time.grain` set nhưng không có `time.start/end` | trend không có khoảng |
| `derived_input_unresolved` | `derived[].inputs` ref tới metric không có | `ratio` thiếu denominator |
| `compare_without_time` | `time.compare_to` set nhưng `time` null | yoy không có period |
| `sort_unknown_column` | `sort[].column` không phải metric alias / group_by / derived | sort theo cột không có |
| `limit_without_sort` | `limit` set nhưng `sort` rỗng | top-N không xác định | (warning) |

**Soft rules** (warning, vẫn chạy):

- `output.format="number"` nhưng kết quả >1 row → tự upgrade lên `"table"`
- `group_by` rỗng nhưng filter có `op="in"` ≥2 values → gợi ý thêm column vào group_by

---

## 4. 17 ví dụ: câu hỏi → QueryPlan

**Catalog tham chiếu** (từ `docs/sql/oracle-free-semantic-catalog.json`):
- Metrics: `doanh thu thuần` (NET_REVENUE), `lợi nhuận gộp` (GROSS_MARGIN), `số đơn hàng` (ORDER_COUNT), `doanh thu ngân sách` (BUDGET_AMOUNT) — đều grain `daily_product_region_channel`
- Dimensions: `PERIOD_DATE`, `REGION_CODE`, `CHANNEL_CODE`, `PRODUCT_CODE`, `CATEGORY_NAME`

### 4.1 Số đơn (case đơn giản nhất)

> "doanh thu HCM tháng 1"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "filters": [{"column": "REGION_CODE", "op": "eq", "values": ["HCM"]}],
  "time": {"start": "2026-01-01", "end": "2026-02-01"},
  "output": {"format": "number"}
}
```

### 4.2 So sánh nhiều giá trị cùng dimension (case bug hiện tại)

> "so sánh doanh thu HCM và Hà Nội tháng 1"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "filters": [{"column": "REGION_CODE", "op": "in", "values": ["HCM", "HN"]}],
  "group_by": ["REGION_CODE"],
  "time": {"start": "2026-01-01", "end": "2026-02-01"},
  "output": {"format": "table"}
}
```

### 4.3 Breakdown toàn bộ chiều

> "doanh thu theo khu vực tháng này"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "group_by": ["REGION_CODE"],
  "time": {"start": "2026-05-01", "end": "2026-06-01"},
  "sort": [{"column": "doanh thu thuần", "direction": "desc"}],
  "output": {"format": "table", "show_total": true}
}
```

### 4.4 Top-N

> "top 5 sản phẩm doanh thu cao nhất quý 1 2026"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "group_by": ["PRODUCT_CODE"],
  "time": {"start": "2026-01-01", "end": "2026-04-01"},
  "sort": [{"column": "doanh thu thuần", "direction": "desc"}],
  "limit": 5,
  "output": {"format": "table"}
}
```

### 4.5 Bottom-N

> "5 kênh có doanh thu thấp nhất tháng này"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "group_by": ["CHANNEL_CODE"],
  "time": {"start": "2026-05-01", "end": "2026-06-01"},
  "sort": [{"column": "doanh thu thuần", "direction": "asc"}],
  "limit": 5,
  "output": {"format": "table"}
}
```

### 4.6 Time-series (trend)

> "doanh thu 6 tháng gần đây theo tuần"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "time": {"start": "2025-11-08", "end": "2026-05-08", "grain": "week"},
  "output": {"format": "chart_hint", "chart_type": "line"}
}
```

### 4.7 So sánh kỳ (Month-over-Month)

> "doanh thu tháng này so với tháng trước"

```json
{
  "metrics": [{"term": "doanh thu thuần", "alias": "current"}],
  "time": {
    "start": "2026-05-01", "end": "2026-06-01",
    "compare_to": "previous_period"
  },
  "derived": [
    {"name": "diff", "expr": "diff", "inputs": ["current", "current_compare"]},
    {"name": "pct", "expr": "pct_change", "inputs": ["current", "current_compare"]}
  ],
  "output": {"format": "report"}
}
```
*(executor tự sinh column `current_compare` cho time-shifted metric)*

### 4.8 So sánh year-over-year theo khu vực

> "doanh thu tháng 1 năm nay so với năm ngoái theo khu vực"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "group_by": ["REGION_CODE"],
  "time": {
    "start": "2026-01-01", "end": "2026-02-01",
    "compare_to": "previous_year"
  },
  "derived": [
    {"name": "yoy_pct", "expr": "pct_change",
     "inputs": ["doanh thu thuần", "doanh thu thuần_compare"]}
  ],
  "output": {"format": "table"}
}
```

### 4.9 Tỷ trọng (share of total)

> "tỷ trọng doanh thu HCM trong tổng doanh thu tháng này"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "group_by": ["REGION_CODE"],
  "time": {"start": "2026-05-01", "end": "2026-06-01"},
  "derived": [
    {"name": "share_pct", "expr": "share_of_total",
     "inputs": ["doanh thu thuần"]}
  ],
  "output": {"format": "table"}
}
```
*(renderer highlight dòng REGION_CODE=HCM)*

### 4.10 Multi-metric (nhiều metric cùng plan)

> "doanh thu và lợi nhuận theo tháng từ đầu năm"

```json
{
  "metrics": [
    {"term": "doanh thu thuần"},
    {"term": "lợi nhuận gộp"}
  ],
  "time": {"start": "2026-01-01", "end": "2026-05-08", "grain": "month"},
  "output": {"format": "table"}
}
```

### 4.11 Derived ratio giữa 2 metric

> "biên lợi nhuận (margin %) theo khu vực tháng này"

```json
{
  "metrics": [
    {"term": "lợi nhuận gộp", "alias": "gp"},
    {"term": "doanh thu thuần", "alias": "rev"}
  ],
  "group_by": ["REGION_CODE"],
  "time": {"start": "2026-05-01", "end": "2026-06-01"},
  "derived": [
    {"name": "margin_pct", "expr": "ratio", "inputs": ["gp", "rev"]}
  ],
  "output": {"format": "table"}
}
```

### 4.12 Exclusion (NOT IN)

> "doanh thu các kênh ngoài online tháng này"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "filters": [{"column": "CHANNEL_CODE", "op": "not_in", "values": ["ONLINE"]}],
  "group_by": ["CHANNEL_CODE"],
  "time": {"start": "2026-05-01", "end": "2026-06-01"},
  "output": {"format": "table"}
}
```

### 4.13 Range filter

> "doanh thu các sản phẩm có giá trị từ 1 tỷ đến 5 tỷ tháng này"

> ❌ **Out-of-scope của catalog hiện tại** (không có dimension price). Validator phải reject với gợi ý: "tôi không có cột giá trị đơn vị để lọc; bạn có thể hỏi theo khu vực/kênh/sản phẩm/danh mục."

### 4.14 Definition (no data)

> "doanh thu thuần là gì?"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "output": {"format": "report"},
  "rationale": "definition_only"
}
```
*(executor skip SQL khi `rationale == "definition_only"`, renderer chỉ dùng `metric.definition` + `formula` + `freshness_rule`)*

### 4.15 Latest available date

> "doanh thu có dữ liệu gần nhất ngày nào"

```json
{
  "metrics": [{"term": "doanh thu thuần"}],
  "rationale": "latest_date",
  "output": {"format": "number"}
}
```
*(executor sinh `SELECT MAX(PERIOD_DATE) FROM ...`)*

### 4.16 Data inventory (no metric ref)

> "có những loại dữ liệu gì để hỏi?"

```json
{
  "metrics": [],
  "rationale": "inventory",
  "output": {"format": "report"}
}
```
*(executor skip SQL, renderer dùng `catalog.list_metrics(role)`)*

### 4.17 Ambiguous → clarification

> "tình hình tháng này"

```json
{
  "metrics": [],
  "needs_clarification": true,
  "clarification_question": "Bạn muốn xem dữ liệu gì: `doanh thu thuần`, `lợi nhuận gộp`, hay `số đơn hàng`?",
  "confidence": 0.4
}
```
*(planner stops here, không gọi executor)*

---

## 5. DSL → Cube REST mapping

Cube REST schema: <https://cube.dev/docs/query-format>. Mọi feature DSL có mapping 1-1 với Cube khi runtime = `cube`.

| DSL | Cube REST |
|---|---|
| `metrics[].term="doanh thu thuần"` | `measures: ["sales_daily.net_revenue"]` (lookup từ `cube_model.infer_measure_name`) |
| `group_by: ["REGION_CODE"]` | `dimensions: ["sales_daily.region_code"]` |
| `filter{col, op:eq, values:[v]}` | `filters: [{member: "...", operator: "equals", values: [v]}]` |
| `filter{col, op:in, values:[v1,v2]}` | `filters: [{member, operator: "equals", values: [v1, v2]}]` *(Cube `equals` đã hỗ trợ multi-values)* |
| `filter{col, op:not_in, values:[v]}` | `filters: [{member, operator: "notEquals", values: [v]}]` |
| `filter{col, op:between, values:[a,b]}` | `filters: [{member, operator: "gte", values:[a]}, {member, operator: "lte", values:[b]}]` |
| `filter{col, op:like, values:[v]}` | `filters: [{member, operator: "contains", values: [v]}]` |
| `filter{col, op:is_null}` | `filters: [{member, operator: "notSet"}]` |
| `time{start, end}` | `timeDimensions: [{dimension, dateRange: [start, end]}]` |
| `time{grain}` | `timeDimensions: [{..., granularity: grain}]` |
| `time{compare_to:previous_year}` | `timeDimensions: [{..., compareDateRange: [...]}]` (Cube ≥ 0.30) |
| `sort: [{col, dir}]` | `order: {<member>: dir}` |
| `limit` | `limit: N` |
| `derived` | KHÔNG có native Cube → executor compute hậu kỳ trong Python |

---

## 6. DSL → Oracle SQL mapping (fallback path)

Khi `AIAL_SEMANTIC_RUNTIME != "cube"`, DSL → SQL parameterized:

```python
# Ví dụ 4.2 (so sánh HCM vs HN)
SELECT REGION_CODE, SUM(NET_REVENUE) AS METRIC_VALUE
FROM   SYSTEM.AIAL_SALES_DAILY_V
WHERE  REGION_CODE IN (:reg_0, :reg_1)
  AND  PERIOD_DATE >= DATE '2026-01-01'
  AND  PERIOD_DATE <  DATE '2026-02-01'
GROUP BY REGION_CODE
ORDER BY METRIC_VALUE DESC
-- params: {"reg_0": "HCM", "reg_1": "HN"}
```

**Mapping rules**:

| DSL op | SQL fragment |
|---|---|
| `eq` | `<col> = :p_n` |
| `in` (≥1 value) | `<col> IN (:p_0, :p_1, ...)` |
| `not_in` | `<col> NOT IN (:p_0, ...)` |
| `between` | `<col> BETWEEN :lo AND :hi` |
| `like` | `<col> LIKE :p` (renderer adds `%`) |
| `is_null` | `<col> IS NULL` |
| `not_null` | `<col> IS NOT NULL` |
| `time.grain=day` | thêm `PERIOD_DATE` vào SELECT + GROUP BY |
| `time.grain=month` | `TRUNC(PERIOD_DATE, 'MM') AS PERIOD_MONTH` |
| `time.grain=week` | `TRUNC(PERIOD_DATE, 'IW') AS PERIOD_WEEK` |
| `time.grain=quarter` | `TRUNC(PERIOD_DATE, 'Q') AS PERIOD_QUARTER` |
| `time.grain=year` | `EXTRACT(YEAR FROM PERIOD_DATE) AS PERIOD_YEAR` |
| `time.compare_to=previous_year` | UNION ALL với `PERIOD_DATE` shift -1 năm + cột tag `period_label` |
| `derived.expr=ratio` | sub-query / lateral, hoặc post-process Python |
| `derived.expr=share_of_total` | window function `SUM(...) OVER (PARTITION BY ...)` |
| `sort` | `ORDER BY <col> <dir>` |
| `limit` | append `FETCH FIRST :n ROWS ONLY` |

**Security pass-through** (giữ nguyên hành vi `sql_execution.py:67-68`):
- Nếu role không phải `admin` và `principal.department` set: thêm `AND DEPARTMENT_SCOPE = :department_scope`
- Sau khi sinh xong → `QueryGovernor.apply` + `SqlGuardrails.validate` (an toàn cứng cuối cùng).

---

## 7. Planner LLM prompt (Pass 1)

```text
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

OUTPUT: JSON only, schema:
{queryplan_json_schema}

RULES:
1. metrics[].term must match catalog EXACTLY. If unsure → metrics: [], needs_clarification: true.
2. time.end is EXCLUSIVE (last_included_day + 1).
3. If user mentions ≥2 specific values for a dimension → use op="in" AND add column to group_by.
4. If user uses "so sánh" / "compare" / "vs" → ALWAYS group_by the comparison axis.
5. If user asks "top N" / "N cao nhất" / "lớn nhất" → set sort desc + limit=N + group_by the noun.
6. If user asks "thấp nhất" / "ít nhất" / "tệ nhất" → sort asc + limit + group_by.
7. If user asks "tỷ trọng" / "share" / "%" → derived: share_of_total + group_by + format=table.
8. If user asks "biên" / "margin" / "tỷ lệ X/Y" → derived: ratio over 2 metrics.
9. If user asks "xu hướng" / "trend" / "theo tuần/tháng" → set time.grain + format=chart_hint.
10. If user asks "so với tháng trước/năm trước" → set compare_to + format=report or table.
11. If question is a definition ("X là gì") → rationale="definition_only", no SQL needed.
12. If question asks "dữ liệu gần nhất ngày nào" → rationale="latest_date".
13. If question is too vague → metrics:[], needs_clarification:true with concrete option list.
14. NEVER invent column names not in the dimensions list.
15. confidence ∈ [0,1]. If <0.55 → needs_clarification:true.

Dimension value normalization (Vietnamese):
- "Hồ Chí Minh" / "HCM" / "Sài Gòn" → "HCM"
- "Hà Nội" / "HN" / "thủ đô" → "HN"
- "Đà Nẵng" / "miền Trung" → "DANANG"
- "online" / "trực tuyến" → "ONLINE"
- "retail" / "bán lẻ" → "RETAIL"
- "B2B" → "B2B"
```

**Cấu hình runtime**:
- `AIAL_QUERY_PLANNER_PROVIDER` ∈ `{anthropic, openai}` (đổi tên từ `AIAL_QUERY_ANALYZER_PROVIDER` để khớp ngữ nghĩa mới)
- `AIAL_QUERY_PLANNER_MODEL` (default: `claude-haiku-4-5-20251001` / `gpt-4.1-mini`)

---

## 8. Renderer LLM prompt (Pass 2)

```text
You are AIAL's analytics result formatter. Locale: vi.

You receive:
- ORIGINAL QUESTION: {question}
- QUERY PLAN: {plan_json}
- ROWS: {rows_json}        (≤200 rows; if more, summarised)
- METADATA: {metric_definitions, units, data_source, freshness_rule}

OUTPUT: render the answer in plan.output.format:

format=number:
  Single sentence with the value, unit, scope (filters + time).
  Example: "Doanh thu HCM tháng 1/2026: **37.69 triệu VND**."

format=table:
  Markdown table with header row labels in Vietnamese.
  Group_by columns first, then metric columns. Sort = plan.sort.
  Numbers formatted by unit (VND → tỷ/triệu, orders → số nguyên).
  If plan.output.show_total → append a "**Tổng cộng**" row.
  After the table, 1-2 sentences highlighting key insight (largest/smallest/notable diff).

format=report:
  Structured Vietnamese text with sections:
    1. **Tóm tắt** (1-2 câu chính)
    2. **Chi tiết** (bullet points, numbers in context)
    3. **So sánh / xu hướng** (nếu có compare_to / grain)
    4. **Lưu ý** (data freshness, caveats)
  Length: 150-400 words.

format=chart_hint:
  JSON only:
    {"chart_type": ..., "x": <dim>, "y": [<metrics>], "series": <dim?>, "labels": {...}}

ALWAYS at the end (any format), append:
  > Nguồn: {data_source}, cập nhật {freshness_rule}.

NEVER invent numbers not in ROWS. NEVER reference filters/columns not in PLAN.
If ROWS empty → say so, suggest reasons (filter quá hẹp, kỳ chưa có dữ liệu) — DO NOT fabricate.
```

**Cost note**: Renderer dùng Haiku/gpt-4.1-mini là đủ (nhiệm vụ format, không reasoning). Không cần Opus.

---

## 9. Migration plan: từ `SemanticPlannerOutput` → `QueryPlan`

### 9.1 Files cần thay đổi

| File | Thay đổi |
|---|---|
| `services/orchestration/semantic/dsl.py` | **MỚI** — toàn bộ DSL Pydantic |
| `services/orchestration/semantic/dsl_validator.py` | **MỚI** — `validate_plan()` |
| `services/orchestration/semantic/query_analyzer.py` | đổi prompt + return `QueryPlan` thay vì `SemanticPlannerOutput` |
| `services/orchestration/semantic/resolver.py` | giữ retrieval (lexical + vector + rerank), chuyển planner→`analyze_query`→DSL; `SemanticResolveDecision.plan` thay vì `.planner_output` |
| `services/orchestration/semantic/cube_runtime.py` | `build_cube_query` nhận `QueryPlan` (không phải `_semantic_plan` dict); thêm support `op="in/not_in/between"`, `derived` post-process |
| `services/orchestration/semantic/sql_execution.py` | `build_semantic_sql_plan` nhận `QueryPlan`; refactor `_period_filter` / `_dimension_selectors` quanh DSL; thêm IN/NOT IN/BETWEEN/grain/compare |
| `services/orchestration/semantic/renderer.py` | **MỚI** — wrapper LLM gọi prompt section 8, fallback deterministic templates |
| `services/orchestration/routes/query.py` | `_build_structured_semantic_answer` thay bằng `renderer.render(plan, rows, ...)`; `_build_semantic_no_data_answer` đọc filter từ `plan` thay vì `_semantic_plan` |
| `services/orchestration/graph/nodes/stub_response.py` | giữ tương thích `_semantic_plan` cũ ngắn hạn (deprecation period) |

### 9.2 Backward-compat trong giai đoạn deploy

`metric["_semantic_plan"]` (dict cũ) vẫn được set, nhưng được **derive từ QueryPlan**:

```python
def queryplan_to_legacy_dict(plan: QueryPlan) -> dict:
    """Adapter for code that still reads metric['_semantic_plan']."""
    primary_filter = {f.column: f.values[0] for f in plan.filters
                      if f.op == "eq" and f.values}
    return {
        "selected_term": plan.metrics[0].term if plan.metrics else None,
        "intent": _derive_legacy_intent(plan),
        "time_filter": _legacy_time_filter(plan.time),
        "dimensions": list(plan.group_by),
        "entity_filters": primary_filter,  # ⚠ lossy: không cover op="in"
        "confidence": plan.confidence,
        "needs_clarification": plan.needs_clarification,
        "clarification_question": plan.clarification_question,
        "rationale": plan.rationale or "queryplan_v2",
    }
```

⚠ Adapter là **lossy** — chỉ đủ cho audit log cũ, không nên dùng trong code path mới.

### 9.3 Test strategy

**Unit tests** (pytest):
- `test_dsl_models.py` — Pydantic validation, frozen, JSON round-trip
- `test_dsl_validator.py` — toàn bộ rule trong section 3
- `test_dsl_to_cube.py` — mapping section 5 (mọi op)
- `test_dsl_to_sql.py` — mapping section 6 + Oracle dialect
- `test_planner_llm.py` — refactor `test_query_analyzer.py`, mock LLM trả 17 ví dụ section 4
- `test_renderer.py` — 4 output formats × 17 ví dụ (snapshot tests)

**Integration**:
- `test_e2e_dsl_pipeline.py` — query → plan → validate → execute (mock cube/oracle) → render
- 17 ví dụ section 4 đều phải pass end-to-end

**Coverage target**: 85%+ trên `services/orchestration/semantic/` (cao hơn baseline 80% vì là layer trung tâm).

### 9.4 Rollout

1. **Phase 2a**: implement DSL + validator + adapter, **không** đổi planner. Run tests song song.
2. **Phase 2b**: chuyển `query_analyzer` sang DSL, giữ `SemanticPlannerOutput` adapter. Feature flag `AIAL_SEMANTIC_DSL_V2=true`.
3. **Phase 2c**: chuyển executor (cube + sql) sang DSL.
4. **Phase 2d**: chuyển renderer sang DSL + LLM-rendered output.
5. **Phase 3**: bật flag default true, deprecate `SemanticPlannerOutput`, xóa adapter sau 2 sprint.

---

## 10. Edge cases & failure modes

| Tình huống | Hành vi |
|---|---|
| LLM trả JSON sai schema | Pydantic raise → fallback deterministic planner cũ (regex-based) → log warning |
| LLM hallucinate metric không có trong catalog | Validator reject → renderer trả clarification "metric không tồn tại; có sẵn: ..." |
| Filter values gồm cả unknown code (e.g. `"REGION_CODE": ["HCM", "XYZ"]`) | Validator soft-warn; SQL/Cube vẫn chạy với cả 2 values; row trống cho XYZ |
| Time range có dữ liệu trống | Executor query `MAX(PERIOD_DATE)` → renderer thông báo "khoảng này chưa có dữ liệu, gần nhất: ..." (giữ behavior `_query_max_available_date`) |
| Multi-metric với grain khác nhau | Validator reject `mixed_grain_metrics` |
| `derived.expr=ratio` chia cho 0 | Executor return `None`; renderer hiển thị "—" thay vì NaN |
| Question mixing semantics ("doanh thu và headcount") | Planner LLM chọn metric mạnh nhất + `needs_clarification` về metric thứ 2 |
| User upload PII trong filter values | PII masker (`pii_masker.py`) chạy trên ROWS sau executor như hiện tại |

---

## 11. Out-of-scope (Phase 1)

Không cover trong DSL v1, để Phase 2+:

- **Joins giữa nhiều cube**: hiện chỉ 1 cube `sales_daily`. Khi thêm `inventory` / `hr_headcount` → cần `join` syntax.
- **Pivot**: bảng wide với row=region, col=channel, cell=metric. Có thể achieve qua `group_by + chart_hint stacked_bar` nhưng không native.
- **Cohort / funnel**: không phù hợp metric-based catalog.
- **User-defined formula**: chỉ dùng formula trong catalog.
- **Streaming / real-time**: Cube/Oracle là batch.

---

## 12. Open questions cần bạn duyệt

1. **Tên env var**: đổi `AIAL_QUERY_ANALYZER_PROVIDER` → `AIAL_QUERY_PLANNER_PROVIDER` có ổn không, hay giữ tên cũ tránh đổi config? *(impact: docs + .env.local)*
2. **Renderer model**: dùng cùng provider/model với planner, hay tách riêng `AIAL_QUERY_RENDERER_PROVIDER`? *(tách → cost control tốt hơn)*
3. **Output format default**: nếu LLM không set → default `"number"` (như hiện tại) hay `"auto"` (table khi >1 row, number khi 1 row)? *(đề xuất: `"auto"` mới)*
4. **Backward-compat window**: bao lâu giữ adapter `queryplan_to_legacy_dict`? *(đề xuất: 2 sprint)*
5. **Cost cap**: Phase 2 sẽ gọi 2 LLM call / câu hỏi (planner + renderer). Có cần cache plan theo `query_digest` để giảm cost không? *(đề xuất: có, TTL 1h)*

---

**Sau khi bạn duyệt 12 open questions** → tôi switch sang **Sonnet 4.6** với prompt: "implement Phase 2a–2d theo `docs/semantic/query-dsl-spec.md`".
