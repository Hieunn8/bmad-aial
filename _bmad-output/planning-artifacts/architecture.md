---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-24'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/research/technical-ai-chatbot-noi-bo-doanh-nghiep-research-2026-04-22.md
  - _bmad-output/planning-artifacts/research/enterprise-ai-chatbot-decision-memo-2026-04-22.md
  - _bmad-output/planning-artifacts/research/enterprise-ai-chatbot-working-checklist-2026-04-22.md
workflowType: 'architecture'
project_name: 'Enterprise AI Data Assistant (AIAL)'
user_name: 'BOSS'
date: '2026-04-24'
oracleVersion: 'flexible/version-agnostic'
ldapTopology: 'flexible/version-agnostic'
---

# Architecture Decision Document
# Enterprise AI Data Assistant (AIAL)

_Tài liệu này được xây dựng theo từng bước qua collaborative discovery. Các sections được append dần qua mỗi bước._

---

## Starter Template Evaluation

### Primary Technology Domain

**Full-Stack AI/ML Enterprise Platform** — multi-service architecture với 14+ specialized components. Không phải web app hay API monolith thông thường. Không có single starter template nào cover được LangGraph + LlamaIndex + Weaviate + Cerbos + Cube.dev + Kong + Keycloak + Nixtla trong cùng một template.

### Starter Options Considered

| Starter | Verdict | Lý do |
|---------|---------|-------|
| `fastapi/full-stack-fastapi-template` | Reference pattern only | FastAPI + React + PostgreSQL + Docker đúng, nhưng single-service, thiếu toàn bộ AI stack |
| `vintasoftware/nextjs-fastapi-template` | ❌ Không phù hợp | Next.js SSR không phù hợp enterprise admin SPA |
| `enterprise-fastapi-template` | ❌ Không phù hợp | MongoDB stack, thiếu AI/LLM components |
| **Custom Monorepo** | ✅ Selected | Full control; multi-service từ đầu; align hoàn toàn với stack |

> **Note (John/PM):** Single-service monolith với module boundaries là valid alternative cho Phase 1 MVP nếu team size < 6. Quyết định extract ra multi-service nên dựa trên evidence (bottleneck thực tế), không phải upfront assumption. Track team size trước khi commit toàn bộ 5-service structure.

### Selected Approach: Custom Monorepo

**Reference:** `github.com/fastapi/full-stack-fastapi-template` cho API structure và CI/CD patterns (không clone toàn bộ).

**Monorepo Structure (Enhanced):**

```
aial/
├── services/
│   ├── orchestration/        # FastAPI + LangGraph + LiteLLM (main chat API)
│   ├── rag/                  # FastAPI + LlamaIndex + Weaviate client
│   │   └── migrations/       # Weaviate schema versions (không có Alembic equivalent)
│   ├── data-connector/       # cx_Oracle/oracledb + connection pool + query sanitization
│   ├── semantic-layer/       # Cube.dev client + caching + query translation
│   │   # NOTE: oracle-connector tách thành 2 modules này (V1: internal boundary, V2: separate service)
│   ├── forecast/             # FastAPI + Nixtla (async job service)
│   └── admin-api/            # FastAPI admin (users, roles, data sources)
├── frontend/
│   └── web/                  # React 18 + Vite + TypeScript + shadcn/ui
├── shared/
│   ├── pyproject.toml        # name = "aial-shared", hatchling build
│   └── src/
│       └── aial_shared/
│           ├── models/       # Pydantic v2 DTOs (request/response only — NO business logic)
│           ├── auth/         # Keycloak JWT validation helpers
│           └── constants/    # Shared enums, constants
│   # KHÔNG có: business logic, ORM schemas, service-specific transformations
├── infra/
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── k8s/                  # Helm charts
│   ├── kong/
│   │   ├── kong.yml          # Declarative config (DB-less mode, GitOps-compatible)
│   │   ├── plugins/          # Rate limiting, auth, logging configs
│   │   └── routes/           # Service routing definitions
│   ├── keycloak/
│   │   └── realm-export.json # COMMITTED — reproducible setup
│   ├── cerbos/
│   │   └── policies/
│   │       └── tests/        # yaml test fixtures
│   └── observability/        # MANDATORY — add trước khi code service đầu tiên
│       ├── otel-collector/   # OpenTelemetry Collector config
│       ├── grafana/          # Dashboards
│       └── tempo/            # Distributed tracing backend
├── docs/
│   └── adr/                  # Architecture Decision Records (5 ADRs cần lock)
├── pyproject.toml            # uv workspace root
├── .python-version           # "3.12"
├── .pre-commit-config.yaml   # ruff + pre-commit-hooks
├── Makefile                  # make install / dev / test / lint / format
└── commitlint.config.js      # Conventional commits enforcement
```

### Architectural Decisions từ Starter

**Language & Runtime:**
- Python **3.12** (3.11+ per PRD; 3.12 recommended 2026 — better stdlib, faster runtime)
- `.python-version` file ở root — pin cho toàn bộ workspace

**Package Manager — `uv` (workspace mode):**

`/pyproject.toml` (root):
```toml
[tool.uv.workspace]
members = ["services/*", "shared"]

[tool.uv]
dev-dependencies = ["pytest>=8.0", "ruff>=0.6", "pre-commit>=3.8"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["services", "shared"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Key commands:
```bash
uv sync                                              # Install toàn bộ workspace
uv run --package services-orchestration pytest       # Test 1 service
uv add fastapi --package services-rag                # Add dep cho service cụ thể
uv add --package services-orchestration ./shared     # Add local shared package
uv lock                                              # Lock toàn bộ workspace
```

> **Security note:** Một số enterprise security scanners chưa biết `uv.lock` format. Verify với security/compliance team nếu có SOC2/ISO27001 requirement.

**Shared Package — `src` layout + hatchling:**
```toml
# shared/pyproject.toml
[project]
name = "aial-shared"
version = "0.1.0"
dependencies = ["pydantic>=2.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/aial_shared"]
```

Import pattern: `from aial_shared.models.query import QueryRequest`

> **Versioning strategy:** Từ V2, shared/models cần versioned contracts — bump version khi thay đổi, deprecate cũ. Implicit coupling khi `shared/` thay đổi có thể break nhiều services cùng lúc.

**Frontend Build:** Vite 6+ + React 18 + TypeScript + shadcn/ui

**Testing Stack:**

| Layer | Tool | Gate |
|-------|------|------|
| Unit | pytest + hypothesis | 80% coverage |
| Async | pytest-asyncio + httpx | All async routes |
| Contract | Schemathesis | All FastAPI endpoints |
| Policy | `cerbos compile ./policies` + yaml fixtures | 100% policy files |
| Integration | testcontainers-python | Critical paths |
| E2E | Playwright | P0 flows only |
| Frontend | Vitest | 80% coverage |

**Linting & Formatting:** Ruff (Python), ESLint + Prettier (TypeScript)

**CI/CD — Affected-Only Strategy:**

```yaml
# .github/workflows/ci.yml — dorny/paths-filter
detect-changes:
  outputs:
    orchestration: ${{ steps.filter.outputs.orchestration }}
    shared: ${{ steps.filter.outputs.shared }}
  # shared/** thay đổi → trigger test TẤT CẢ dependent services
```

**Pre-commit:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: ruff-pre-commit        # lint + format Python
  - repo: pre-commit-hooks       # detect-private-key, check-merge-conflict, check-added-large-files
```

**Developer Experience:**
```makefile
# Makefile
install:  uv sync && cd frontend/web && npm ci && uv run pre-commit install
dev:      docker compose -f infra/docker-compose.dev.yml up -d && [services] && npm run dev
test:     uv run pytest && cd frontend/web && npx vitest run
lint:     uv run ruff check && npx eslint src/
format:   uv run ruff format && npx prettier --write src/
```

**Note:** Project scaffold là Story đầu tiên trong Sprint 1 Implementation.

### Documentation Scaffolding (Paige)

> Engineer mới join không có "bản đồ" → lost từ ngày 1. 1-2 ngày đầu tư, ROI cực cao.

**Missing files — thêm ngay vào structure:**
```
aial/
├── docs/
│   ├── index.md                    ← "Bắt đầu từ đây" — entry point duy nhất
│   ├── getting-started.md          ← Setup từ zero (prerequisites → make install → make dev)
│   ├── architecture/
│   │   ├── overview.md             ← C4 Level 1+2 diagram
│   │   ├── decisions.md            ← Index link đến ADRs
│   │   └── data-flow.md            ← 3 critical paths: query / ingestion / policy
│   ├── adr/
│   │   ├── README.md               ← ADR index table
│   │   ├── template.md             ← MADR format (bên dưới)
│   │   └── ADR-00{1-5}-*.md
│   ├── api/
│   │   ├── README.md               ← OpenAPI strategy
│   │   └── specs/public-api.yaml   ← Merged spec (CI-generated)
│   ├── runbooks/                   ← Ops knowledge (sau launch)
│   └── contributing/
│       ├── development.md
│       ├── testing.md
│       └── style-guide.md
├── CONTRIBUTING.md                 ← Blocker cho collaboration
└── .github/
    └── PULL_REQUEST_TEMPLATE.md
```

**ADR Template (MADR format) — `docs/adr/template.md`:**
```markdown
# ADR-{NNN}: {Tên quyết định — imperative form}

**Date:** YYYY-MM-DD
**Status:** `Draft` | `Accepted` | `Deprecated` | `Superseded by ADR-NNN`
**Deciders:** {Tên người/team}
**Tags:** `infrastructure` | `security` | `api` | `data` | `frontend`

## Context and Problem Statement
> Vấn đề gì? Tại sao cần quyết định này? (2-3 câu)

## Decision Drivers
- Driver 1: {Yếu tố quan trọng nhất}
- Driver 2: {Business constraint hoặc technical requirement}

## Considered Options
| Option | Pros | Cons |
|--------|------|------|
| Option A | + Pro 1 | - Con 1 |
| Option B | + Pro 1 | - Con 1 |

## Decision Outcome
**Chosen:** Option X — vì {lý do chính một câu}.

### Positive Consequences
### Negative Consequences / Trade-offs

## Links
- [Related ADR-NNN](./ADR-NNN-*.md)
- [RFC/Issue/PR](https://github.com/...)
```

**Service README Template — `services/*/README.md`:**
```markdown
# {Service Name}
> {Một câu mô tả bounded context}

## Responsibility
{2-3 câu: làm gì, không làm gì}

## API
- **REST:** `http://localhost:{PORT}` — [OpenAPI Spec](./docs/openapi.yaml)
- **Events consumed / produced:** {topic names}

## Local Development
```bash
uv run --directory services/{name} fastapi dev src/{module}/main.py
docker compose -f infra/docker-compose.dev.yaml up {deps-only}
```

## Configuration
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection |

## Testing
```bash
uv run pytest services/{name}/tests/
```

## Ownership
**Team:** {team} | **On-call runbook:** {link}
```

**OpenAPI Strategy — Spec-First, Code-Adjacent:**
```
FastAPI auto-generates /openapi.json
→ CI export → services/{svc}/docs/openapi.yaml
→ CI validate với Spectral (.spectral.yaml)
→ CI merge → docs/api/specs/public-api.yaml
→ CI render → Redoc HTML (developer portal)
```

Event-driven services dùng **AsyncAPI** thay OpenAPI. Makefile thêm: `docs-api-export`, `docs-api-validate`, `docs-api-merge`, `docs-api-serve`.

### Frontend Architecture (Sally)

**Hai app entries, không phải một SPA:**

Chat UI và Admin Portal có cognitive model khác nhau hoàn toàn (Hoa/HR cần simple và reassuring; Lan/IT Admin cần information density cao). Không thể merge thành 1 SPA mà không có cognitive mismatch.

```
frontend/
├── apps/
│   ├── chat/          # User-facing: streaming, tables, charts — mobile-first
│   └── admin/         # IT/Data Owner: dense info, filters, config — desktop-first
└── packages/
    ├── ui/            # Shared shadcn/ui components
    └── types/         # Shared TypeScript interfaces
```

**SSE Streaming Components — PHẢI thiết kế trước khi code (không thể retrofix):**

| Component | Critical States | Lý do không thể để sau |
|-----------|----------------|------------------------|
| `<StreamingMessage />` | idle → thinking → streaming → rendering → complete → error | "Thinking" state = Minh quyết định có trust system không |
| `<ProgressiveDataTable />` | stream từng row, lock headers | Layout shift khi streaming = UX broken |
| `<StreamAbortButton />` | visible rõ, không ẩn trong menu | Minh cần stop ngay trong meeting |
| `<ConnectionStatusBanner />` | SSE drop → user thấy ngay | Không có = user nghĩ app lỗi sau 30s |
| `<ChartReveal />` | JSON stream complete → fade-in chart | JSON parse race condition nếu render sớm |

**Chart Library Strategy:**

| Library | Bundle | Dùng khi nào |
|---------|--------|--------------|
| **Recharts** (default) | ~200KB | 80% use cases: bar, line, area, pie — Chat UI |
| **Plotly React** (lazy) | ~3MB | Admin edge cases: heatmap, correlation charts |
| **Observable Plot** (evaluate) | ~70KB | Worth evaluating — nhẹ hơn Plotly, expressive hơn Recharts |

Recharts + shadcn/ui theming: seamless. Plotly: `lazy(() => import('react-plotly.js'))` — không bao giờ load trong Chat UI (Minh cần < 30s, 3MB bundle = deal-breaker).

**Performance Budget:**
- Chat UI first paint: < 2 giây
- Chat UI interactive: < 4 giây
- Admin Portal: desktop-first, looser budget acceptable

**5 UX Risks — Phát hiện muộn = Refactor đau:**

| Risk | Impact | Phải design khi nào |
|------|--------|---------------------|
| **Data masking visual treatment** | Hoa không phân biệt `***-1234` là masked hay actual → cần lock icon + tooltip "masked for privacy" + interaction khi hover | Sprint 1 — nếu để sau = refactor toàn bộ DataTable |
| **Streaming + chart JSON race condition** | Stream chưa complete → JSON parse fail → chart crash | Sprint 1 — "chart placeholder skeleton" pattern |
| **Chat UI mobile responsiveness** | Minh check số liệu bằng điện thoại trong meeting → phải mobile-first | Sprint 1 — Vite + shadcn không responsive mặc định |
| **Empty states per scenario** | "No data found" generic → user nghĩ lỗi hệ thống | Sprint 2 — mỗi permission deny / no data / disconnected cần empty state riêng |
| **ARIA & keyboard navigation** | shadcn/ui tốt nhưng custom streaming components cần ARIA manual | Sprint 2 — retrofit sau = tốn kém |

### Business Alignment (Mary)

**FR → Service Traceability — Cần Requirements Traceability Matrix:**

2/6 services cần re-framing:
- `admin-api/` — không có FR chủ; cross-cutting concern, không phải standalone service. Cân nhắc merge CRUD admin logic vào từng service owner tương ứng.
- `semantic-layer/` — Cube.dev client ≠ semantic layer *ownership*. Ai owns business term definitions? Data Owner (Nam) phải là business owner, không phải technical service.

**RTM template (`docs/requirements-traceability.md`):**
```
FR-ID | FR Description        | Service Owner    | API Endpoint  | Test Case
FR-S1 | Semantic layer query  | semantic-layer   | POST /query   | TC-S1-001
FR-A1 | LDAP/SSO auth         | admin-api/keycloak | POST /auth/token | TC-A1-001
```
Nếu FR không có Service Owner rõ → signal để tái cơ cấu hoặc làm rõ scope.

**ADR Readiness — BOSS chỉ có đủ thông tin cho 1/5 ADRs ngay bây giờ:**

| ADR | Sẵn sàng? | Cần elicitation gì |
|-----|-----------|-------------------|
| Multi-tenancy model | ❌ | Số tenants dự kiến? Data residency per tenant? Compliance level? |
| Consistency contract | ❌ | Business chịu được eventual consistency đến đâu? Financial transactions cần strong consistency? |
| Embedding model lock | ⚠️ | Confirm: tiếng Việt chủ yếu hay tiếng Anh? On-premise constraint cho embedding? |
| Async retry policy | ❌ | SLA từ stakeholders? Max acceptable end-to-end latency? |
| Local dev strategy | ✅ | Purely technical — quyết định được ngay |

**3 lớp phòng thủ business-technical alignment:**
1. **Business Event Storming (4h trước Walking Skeleton)** — map business events trước, services emerge sau từ event boundaries
2. **Definition of Done với business acceptance criteria** — "Finance Manager xem dự báo trong < 5 giây", không phải "service handle Y req/s"
3. **Bi-weekly alignment check** — "Nếu demo ngay hôm nay, điều gì quan trọng nhất?"

---

## Architecture Validation Results

> **Thực hiện:** 2026-04-24 — sau khi hoàn thành Steps 1-6

### Coherence Validation

**Decision Compatibility: ✅ All compatible**

| Technology Pair | Compatibility | Note |
|-----------------|--------------|------|
| LangGraph 1.1.8 + LiteLLM + LlamaIndex | ✅ | Standard AI stack combination |
| Keycloak JWT + Cerbos ABAC + Kong JWT plugin | ✅ | Auth chain flows correctly |
| TanStack Query 5.99.2 + Router 1.168.23 | ✅ | Native integration, documented |
| FastAPI 0.115+ + Pydantic v2 + uv workspace | ✅ | Standard 2026 Python stack |
| bge-m3 (1024 dims) + Weaviate | ✅ | Vector dimensions compatible |
| Celery 5.x + Redis Streams | ✅ | Native task queue + DLQ support |
| **pydantic v1 (langchain-core) + pydantic v2 (FastAPI)** | ⚠️ **P0 conflict** | Documented — resolve Sprint 1 |

**Pattern Consistency: ✅**
- Naming: snake_case (Python) / camelCase (TS) / kebab-case (API) — consistent với `alias_generator=to_camel` bridge
- Error format: RFC 9457 — consistent across all 6 services
- Celery naming: `{service}.{domain}.{action}_{entity}` — bounded verbs defined
- Redis keys: `aial:{service}:{entity}:{id}:{field}` — TTL policy defined
- LangGraph nodes: `{verb}_{noun}` pure functions — contract defined

**Structure Alignment: ✅**
- All 6 services follow identical layout (routes/services/repositories/adapters/tasks/core/)
- Frontend apps follow identical layout
- `shared/` scope clearly bounded (DTOs + auth + clients + telemetry only)

---

### Requirements Coverage Validation

**Functional Requirements — 37 FRs:**

| Module | Coverage | Gap |
|--------|---------|-----|
| FR-O1-O5 (Agent Orchestration) | ✅ 5/5 | `graph/nodes/` cover all 5 |
| FR-S1-S6 (Text-to-SQL & Semantic) | ✅ 6/6 | semantic-layer/ + data-connector/ |
| FR-R1-R5 (RAG) | ✅ 5/5 | rag/services/ cover all |
| FR-A1-A8 (Security) | ⚠️ 7/8 | FR-A5 (PII masking) — gap addressed below |
| FR-M1-M7 (Session Memory) | ✅ 7/7 | orchestration/memory_service.py |
| FR-F1-F6 (Forecasting) | ✅ 6/6 | forecast/services/ cover all |
| FR-E1-E4 (Export/Reporting) | ⚠️ 3/4 | FR-E2 (Scheduled reports) — gap addressed below |
| FR-AD1-AD5 (Administration) | ✅ 5/5 | admin-api/ + apps/admin/ |

**Total: 35/37 FRs fully covered — 2 gaps identified and addressed:**

**Gap 1 — FR-A5 (PII Masking/Presidio):**
```
services/orchestration/middleware/
├── audit.py        # already defined
└── pii_filter.py   # ← ADD: Microsoft Presidio scan BEFORE response returned to user
```
Also add to `shared/aial_shared/pii/presidio_scanner.py` for reuse by forecast + export services.

**Gap 2 — FR-E2 (Scheduled Reports/Celery Beat):**
```
services/orchestration/tasks/
├── query_task.py
├── export_task.py
└── scheduled_tasks.py   # ← ADD: Celery Beat periodic schedules (daily/weekly/monthly reports)
```
Add Celery Beat service to `infra/docker-compose.dev.yml`.

**Non-Functional Requirements: ✅ All 7 categories covered**

| NFR Category | Architectural Support |
|-------------|----------------------|
| Performance SLOs | Semantic cache + Oracle read-optimized layer + Celery async |
| Security | Keycloak + Cerbos + Oracle VPD + AES-256 + TLS 1.3 |
| HA/DR (99.5%, RTO 4h, RPO 1h) | Multi-instance + PostgreSQL WAL + Redis AOF + Weaviate backup |
| Scalability | Kubernetes + horizontal scaling + workload pools |
| Observability | OpenTelemetry + Prometheus/Grafana + Langfuse |
| Cost Management | LiteLLM cost tracking + rate limiting (100/day per user) |
| Maintainability | Modular LLM + semantic layer versioning + API versioning |

---

### Implementation Readiness Validation

**Decision Completeness: ✅**
- Technology versions verified (April 2026): LangGraph 1.1.8, TanStack Query 5.99.2, TanStack Router 1.168.23
- Phase 1 Minimal vs Full pattern tiers defined — developers know exactly what to implement first
- 5 ADRs documented with template and content outlines
- FR → Service mapping complete with file-level specificity
- Walking skeleton sequence defined with explicit gates

**Structure Completeness: ✅**
- Complete directory tree defined (all services, all key files)
- Component boundaries documented (what each service owns/does NOT own)
- Integration points: Internal HTTP with OpenTelemetry propagation
- Test structure: conftest.py fixtures per service + unit/integration split

**Pattern Completeness: ✅**
- 8 naming convention categories with cross-layer mapping table
- Quick Reference Index for AI agents (< 30 second lookup)
- Decision trees for naming, response format, sync vs async
- 14 cross-cutting concerns documented
- 12 architectural risks classified (P0/P1/P2) with mitigations
- 7 Phase 1 mandatory rules (non-negotiable)

**Pending actions (non-blocking for implementation start):**
| Action | Owner | When |
|--------|-------|------|
| ADR-001 governance sign-off | Lan/IT Admin + Compliance | Before Phase 1 deploy |
| ADR-003 accuracy benchmark (50-100 queries) | Engineering | Sprint 1 |
| Pydantic v1/v2 conflict resolution | Engineering | Sprint 1, before any service code |

---

### Architecture Completeness Checklist

**✅ Requirements Analysis (Step 2)**
- [x] 37 FRs analyzed across 8 modules
- [x] 7 NFR categories assessed
- [x] 10 cross-cutting concerns identified
- [x] 12 architectural risks classified P0/P1/P2
- [x] 5 governance blockers identified (ADR-001, ADR-003, etc.)

**✅ Starter Template (Step 3)**
- [x] Custom Monorepo selected — evaluated 3 alternatives
- [x] Python 3.12 + uv workspace + Ruff + pytest configured
- [x] Frontend: React 18 + Vite 6 + shadcn/ui + Turborepo
- [x] Documentation scaffolding: ADR template, service README template, OpenAPI strategy

**✅ Architectural Decisions (Step 4)**
- [x] ADR-001: Shared schema + Oracle VPD + Cerbos `principal.attr` freeze before Epic 4 extension
- [x] ADR-002: Consistency contract per domain
- [x] ADR-003: bge-m3 embedding, 1024 dims, self-hosted
- [x] ADR-004: Exponential backoff retry + DLQ Redis Streams
- [x] Inter-service: REST HTTP + Celery async (not gRPC/Kafka)
- [x] Frontend: TanStack Query + Zustand (3-layer state) + TanStack Router
- [x] K8s: Per-environment namespaces + ResourceQuota + NetworkPolicy

**✅ Implementation Patterns (Step 5)**
- [x] Naming conventions: 5 categories + cross-layer mapping table
- [x] File structure patterns: backend (§ST-1) + frontend (§ST-2)
- [x] API response formats: success / RFC 9457 error / SSE events
- [x] Communication: Celery naming + Redis keys + LangGraph nodes + Zustand immutability
- [x] Process: error handling + logging (no PII) + loading states + validation timing
- [x] Security: no hardcoded secrets, PII protection, Cerbos policy enforcement
- [x] Phase 1 Minimal vs Full pattern tiers

**✅ Project Structure (Step 6)**
- [x] Complete directory tree: 6 services + 2 frontend apps + shared + infra + docs
- [x] LangGraph nodes: 9 defined (including 3 added from party review)
- [x] FR → file-level mapping complete
- [x] Walking skeleton: Infrastructure → Observability → Skeleton → Features
- [x] Documentation: learning path, glossary, AI agent guide, CODEOWNERS

---

### Architecture Readiness Assessment

**Overall Status: READY FOR IMPLEMENTATION** ✅

**Confidence Level: High** — based on:
- Comprehensive party reviews (6 rounds across 7 steps)
- All critical gaps identified and addressed
- Phase 1 scope clearly bounded
- Walking skeleton sequence defined
- Technology versions verified

**Key Strengths:**
1. Defense-in-depth security (6 layers: Kong → Keycloak → Cerbos → App → VPD → Column-level)
2. AI Safety threat model complete (14 vectors) — rare in enterprise PRDs
3. Phase 1 Minimal Patterns tier — prevents over-engineering in MVP
4. Walking skeleton gates — validate integration before feature build-out
5. Oracle version-agnostic design (capability-based adapter)
6. Sovereign AI path (Local LLM via config swap, no code change)

**Areas for Future Enhancement (Post-Phase 3):**
- Real-time streaming data (Kafka/CDC) — currently out of scope
- Voice interface — noted as Phase 4+ option
- Multi-region Oracle topology — option when data residency required
- Bulk ML forecasting (Spark/Dask/Ray cluster) — Phase 4 option

---

### Implementation Handoff

**AI Agent Guidelines:**
1. Read `docs/index.md` learning path table FIRST — know which docs to read for your role
2. Follow all naming conventions per §NM-1 through §NM-5
3. Check Phase 1 Mandatory patterns before writing any code
4. Use Quick Reference Index (§) for pattern lookup — target < 30 seconds
5. Never bypass Cerbos policy check (Phase 2 mandatory, hardcode simple check Phase 1)
6. Every service starts with `setup_tracing(service_name)` as first line in `main()`
7. Commit `validate_sql.py` LangGraph node before `execute_query.py` — security gate P0

**First Implementation Steps:**
```bash
# Step 1: Infrastructure
docker-compose -f infra/docker-compose.dev.yml up -d
bash infra/scripts/seed-keycloak.sh
bash infra/scripts/seed-cerbos.sh
bash infra/scripts/wait-for-services.sh

# Step 2: Observability (before any service code)
# Deploy infra/observability/ stack
# Verify traces in Grafana Tempo

# Step 3: shared/ package (all services depend on this)
cd shared && uv sync && uv run pytest
# Must pass 100% before proceeding

# Step 4: Resolve Pydantic v1/v2 conflict
# See requirements/constraints.txt strategy

# Step 5: Walking skeleton
# services/orchestration/ → services/rag/ → services/data-connector/ stubs
# Gate: end-to-end trace thông suốt với mock data
```

---

## Project Structure & Boundaries

> **Nguồn:** Steps 2-5 + Party Review (Winston + Amelia + Paige)

### Complete Monorepo Directory Tree

```
aial/
├── apps/
│   ├── chat/                              # FR: User-facing journeys — Minh, Tuấn, Hoa
│   │   ├── src/
│   │   │   ├── routes/
│   │   │   │   └── _authenticated/
│   │   │   │       ├── index.lazy.tsx          # Chat main screen
│   │   │   │       └── history.lazy.tsx         # Conversation history
│   │   │   ├── components/
│   │   │   │   ├── streaming/
│   │   │   │   │   ├── StreamingMessage.tsx     # 6 states: idle→thinking→streaming→done→error
│   │   │   │   │   ├── ProgressiveDataTable.tsx # Stream rows, lock headers
│   │   │   │   │   ├── StreamAbortButton.tsx    # Visible, not in menu
│   │   │   │   │   ├── ConnectionStatusBanner.tsx
│   │   │   │   │   └── ChartReveal.tsx          # Fade-in when JSON stream complete
│   │   │   │   └── ui/                          # shadcn/ui overrides only
│   │   │   ├── hooks/
│   │   │   │   ├── useSSEStream.ts              # SINGLE SOURCE OF TRUTH for SSE
│   │   │   │   └── useQueryResult.ts
│   │   │   ├── stores/
│   │   │   │   ├── streamStore.ts               # Active stream state (Zustand)
│   │   │   │   └── uiStore.ts                   # Sidebar, modal, theme
│   │   │   ├── services/
│   │   │   │   └── queryService.ts              # API call wrappers
│   │   │   ├── types/
│   │   │   │   └── api.ts
│   │   │   └── utils/
│   │   │       └── errorMessages.ts             # RFC 9457 type → user-friendly message
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── package.json
│   └── admin/                             # FR-AD1-AD5 — Lan, Nam, Hùng
│       ├── src/
│       │   ├── routes/
│       │   │   └── _authenticated/
│       │   │       └── admin/
│       │   │           ├── users/
│       │   │           │   ├── index.lazy.tsx
│       │   │           │   └── $userId/edit.lazy.tsx
│       │   │           ├── roles/index.lazy.tsx
│       │   │           ├── data-sources/index.lazy.tsx
│       │   │           ├── semantic-layer/
│       │   │           │   └── kpi/$domainId/edit.tsx    # Nam: KPI management
│       │   │           ├── approvals/
│       │   │           │   ├── index.lazy.tsx             # Hùng: approval queue
│       │   │           │   └── $requestId/review.lazy.tsx # Hùng: review screen
│       │   │           ├── audit-logs/index.lazy.tsx      # Lan: audit monitoring
│       │   │           └── system-health/index.lazy.tsx   # Lan: system health
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── stores/
│       │   ├── services/
│       │   ├── types/
│       │   └── utils/
│       │       └── errorMessages.ts
│       ├── index.html
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── package.json
├── packages/                              # Shared frontend packages (Turborepo)
│   ├── ui/                               # Shared shadcn/ui components
│   │   ├── src/components/
│   │   └── package.json
│   └── types/                            # Shared TypeScript types
│       ├── src/
│       │   ├── api.ts                    # Shared API types
│       │   └── queryKeys.ts             # TanStack Query key factory
│       └── package.json
├── services/
│   ├── orchestration/                    # FR-O1-O5 (core routing/planning ONLY)
│   │   │                                 # FR-M1-M7 (session memory via Redis)
│   │   │                                 # FR-E1-E4 (audit as middleware, not service)
│   │   ├── src/
│   │   │   └── orchestration/
│   │   │       ├── main.py               # FastAPI app + OpenTelemetry setup
│   │   │       ├── routes/
│   │   │       │   ├── query.py          # POST /v1/chat/query, GET /v1/chat/stream/{id}
│   │   │       │   ├── sessions.py       # GET /v1/sessions, history search
│   │   │       │   └── health.py
│   │   │       ├── services/
│   │   │       │   ├── query_service.py
│   │   │       │   ├── memory_service.py # FR-M1-M7: short/medium/long-term memory
│   │   │       │   └── intent_service.py # FR-O1: intent classification
│   │   │       ├── repositories/
│   │   │       │   ├── session_repo.py
│   │   │       │   └── memory_repo.py
│   │   │       ├── models/
│   │   │       │   ├── requests.py
│   │   │       │   └── responses.py
│   │   │       ├── adapters/
│   │   │       │   └── llm/
│   │   │       │       ├── base.py       # Abstract LLMProvider interface
│   │   │       │       └── litellm_adapter.py
│   │   │       ├── clients/              # Internal HTTP clients (not shared library)
│   │   │       │   ├── rag_client.py     # HTTP → services/rag with OTel propagation
│   │   │       │   ├── connector_client.py
│   │   │       │   ├── semantic_client.py
│   │   │       │   ├── forecast_client.py
│   │   │       │   └── cerbos_client.py
│   │   │       ├── graph/                # LangGraph agent graph
│   │   │       │   ├── state.py          # AIALGraphState TypedDict — shared contract
│   │   │       │   ├── graph.py          # Graph assembly + RedisSaver checkpointer
│   │   │       │   └── nodes/
│   │   │       │       ├── classify_intent.py      # FR-O1
│   │   │       │       ├── validate_permissions.py # Cerbos check
│   │   │       │       ├── retrieve_context.py     # RAG path
│   │   │       │       ├── generate_sql.py         # Text-to-SQL
│   │   │       │       ├── validate_sql.py         # ← P0: AST check BEFORE execute
│   │   │       │       ├── execute_query.py        # Oracle via data-connector
│   │   │       │       ├── format_output.py        # chart/table/export branching
│   │   │       │       ├── compose_response.py     # Final response assembly
│   │   │       │       ├── audit_log.py            # Compliance: every query logged
│   │   │       │       └── handle_error.py
│   │   │       ├── middleware/
│   │   │       │   └── audit.py          # FR-E1-E4: audit as decorator/middleware
│   │   │       ├── tasks/
│   │   │       │   ├── query_task.py     # orchestration.query.process_request
│   │   │       │   └── export_task.py    # orchestration.export.generate_report
│   │   │       └── core/
│   │   │           ├── config.py
│   │   │           ├── deps.py
│   │   │           ├── middleware.py
│   │   │           └── exceptions.py
│   │   ├── tests/
│   │   │   ├── conftest.py               # base_state fixture, mock_llm, fake_clients
│   │   │   ├── unit/
│   │   │   │   └── nodes/
│   │   │   │       ├── test_classify_intent.py
│   │   │   │       ├── test_validate_sql.py     # P0 test
│   │   │   │       └── test_generate_sql.py
│   │   │   └── integration/
│   │   │       └── test_graph_flow.py    # LangGraph E2E with mocked nodes
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   ├── .env.example
│   │   └── README.md                     # With routing decision tree + failure modes
│   ├── rag/                              # FR-R1-R5
│   │   ├── src/
│   │   │   └── rag/
│   │   │       ├── main.py
│   │   │       ├── routes/
│   │   │       │   ├── documents.py      # POST /upload, GET /list (FR-R5)
│   │   │       │   └── retrieval.py      # POST /retrieve (FR-R2, FR-R3)
│   │   │       ├── services/
│   │   │       │   ├── ingestion_service.py    # FR-R1: parse→chunk→embed→index
│   │   │       │   ├── retrieval_service.py    # FR-R2: policy pre-filter + search
│   │   │       │   └── document_service.py     # FR-R4, FR-R5: access control
│   │   │       ├── repositories/
│   │   │       │   └── vector_repo.py          # Weaviate client wrapper
│   │   │       ├── adapters/
│   │   │       │   └── embedding/
│   │   │       │       ├── base.py              # Abstract EmbeddingAdapter
│   │   │       │       └── bge_m3_adapter.py    # ADR-003: bge-m3 (1024 dims)
│   │   │       ├── tasks/
│   │   │       │   └── ingestion_task.py        # rag.document.sync_index
│   │   │       ├── migrations/
│   │   │       │   └── v001_initial_schema.py   # Weaviate collection schema
│   │   │       └── core/
│   │   ├── tests/
│   │   │   ├── conftest.py               # mock_weaviate, sample_documents
│   │   │   ├── unit/
│   │   │   │   └── test_bge_m3_adapter.py
│   │   │   └── integration/
│   │   │       └── test_ingestion_pipeline.py
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── .env.example
│   ├── data-connector/                   # FR-S3 (AST validation), FR-S4 (governor)
│   │   │                                 # Oracle VPD + DataSourceRegistry
│   │   ├── src/
│   │   │   └── data_connector/
│   │   │       ├── main.py
│   │   │       ├── routes/
│   │   │       │   └── query.py          # POST /v1/sql/execute (internal only)
│   │   │       ├── services/
│   │   │       │   ├── sql_validator.py  # FR-S3: AST parsing + whitelist
│   │   │       │   └── query_service.py  # FR-S4: query governor (timeout, row limit)
│   │   │       ├── repositories/
│   │   │       │   └── oracle_repo.py    # cx_Oracle + VPD context management
│   │   │       ├── adapters/
│   │   │       │   └── oracle/
│   │   │       │       ├── capability_detector.py  # Probe features at connect-time
│   │   │       │       ├── connector.py            # SessionPool + user_proxy mode
│   │   │       │       └── registry.py             # DataSourceRegistry
│   │   │       └── core/
│   │   ├── tests/
│   │   │   ├── conftest.py               # oracle_test_container (testcontainers)
│   │   │   ├── unit/
│   │   │   │   └── test_capability_detector.py
│   │   │   └── integration/
│   │   │       └── test_oracle_vpd.py    # ← P0: VPD context isolation test
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── .env.example
│   ├── semantic-layer/                   # FR-S1 (semantic abstraction), FR-S2 (catalog)
│   │   ├── src/
│   │   │   └── semantic_layer/
│   │   │       ├── main.py
│   │   │       ├── routes/
│   │   │       │   ├── metrics.py        # GET /v1/metrics (Cube.dev proxy)
│   │   │       │   └── glossary.py       # GET/PUT /v1/glossary (business terms)
│   │   │       ├── services/
│   │   │       │   ├── cube_client.py    # Cube.dev headless API
│   │   │       │   └── glossary_service.py
│   │   │       ├── repositories/
│   │   │       │   └── metric_repo.py    # PostgreSQL metric definitions + versions
│   │   │       └── core/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   ├── forecast/                         # FR-F1-F6 (Phase 2)
│   │   ├── src/
│   │   │   └── forecast/
│   │   │       ├── main.py
│   │   │       ├── routes/
│   │   │       │   └── forecast.py       # POST /v1/forecast/run
│   │   │       ├── services/
│   │   │       │   ├── timeseries_service.py   # FR-F1: Nixtla TimeGPT
│   │   │       │   ├── anomaly_service.py       # FR-F2: Isolation Forest + LLM explain
│   │   │       │   └── explainer_service.py     # FR-F5: SHAP + natural language
│   │   │       ├── adapters/
│   │   │       │   └── forecasting/
│   │   │       │       ├── base.py               # Abstract ForecastingAdapter
│   │   │       │       └── nixtla_adapter.py     # + MockNixtlaClient for CI
│   │   │       ├── tasks/
│   │   │       │   └── forecast_task.py          # forecast.time_series.generate_report
│   │   │       └── core/
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   └── admin-api/                        # FR-AD1-AD5
│       ├── src/
│       │   └── admin_api/
│       │       ├── main.py
│       │       ├── routes/
│       │       │   ├── users.py          # FR-AD2: CRUD + LDAP sync
│       │       │   ├── data_sources.py   # FR-AD3: Oracle connection config
│       │       │   ├── audit_logs.py     # FR-AD4: Audit log search/filter
│       │       │   └── health.py         # FR-AD5: System health metrics
│       │       ├── services/
│       │       ├── repositories/
│       │       └── core/
│       ├── pyproject.toml
│       └── Dockerfile
├── shared/                               # Python aial-shared package
│   ├── pyproject.toml                    # name="aial-shared", hatchling build
│   ├── README.md                         # Public API surface + versioning policy
│   └── src/
│       └── aial_shared/
│           ├── __init__.py
│           ├── models/                   # Pydantic DTOs ONLY (no business logic)
│           │   ├── query.py              # QueryRequest, QueryResponse
│           │   ├── user.py               # UserContext, UserPermissions
│           │   └── audit.py              # AuditEvent
│           ├── auth/
│           │   └── keycloak.py           # JWT validation helpers
│           ├── clients/                  # Shared connection singletons
│           │   ├── redis_client.py       # Singleton — services don't re-init
│           │   ├── weaviate_client.py    # Shared connection pool
│           │   └── oracle_client.py      # Base conn — data-connector extends
│           ├── telemetry/
│           │   ├── tracer.py             # setup_tracing(service_name) — called in main()
│           │   └── metrics.py
│           ├── schemas/
│           │   ├── query_request.py      # Shared between orchestration + API
│           │   └── audit_event.py
│           ├── utils/
│           │   ├── retry.py              # tenacity wrapper — standard retry policy
│           │   └── pagination.py
│           ├── constants/
│           │   └── redis_keys.py         # Redis key patterns + TTL constants
│           └── exceptions/
│               └── base.py               # BaseAIALException hierarchy
├── infra/
│   ├── docker-compose.dev.yml            # 7 services for local dev
│   ├── docker-compose.prod.yml
│   ├── kong/
│   │   ├── kong.yml                      # Declarative (DB-less) — GitOps
│   │   ├── plugins/rate-limiting.yml
│   │   └── routes/services.yml
│   ├── keycloak/
│   │   ├── realm-export.json             # COMMITTED — reproducible
│   │   └── themes/
│   ├── cerbos/
│   │   └── policies/
│   │       ├── query.yaml
│   │       ├── document.yaml
│   │       ├── export.yaml
│   │       ├── approval.yaml
│   │       └── tests/
│   │           ├── query_test.yaml
│   │           └── export_test.yaml
│   ├── observability/                    # MUST exist BEFORE first service code
│   │   ├── otel-collector/config.yaml
│   │   ├── grafana/dashboards/
│   │   │   ├── aial-overview.json
│   │   │   └── llm-observability.json
│   │   └── tempo/config.yaml
│   ├── k8s/
│   │   ├── base/                         # Kustomize base manifests
│   │   │   ├── namespace.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── kustomization.yaml
│   │   ├── overlays/
│   │   │   ├── dev/                      # Local kind/minikube
│   │   │   ├── staging/                  # Lower resources, mock external
│   │   │   └── prod/                     # Full replicas, PDB, HPA
│   │   └── components/
│   │       ├── kong/
│   │       ├── keycloak/
│   │       ├── cerbos/
│   │       ├── weaviate/                 # StatefulSet + PVC
│   │       └── observability/
│   ├── terraform/                        # Cloud infra provisioning
│   │   ├── modules/gke/ (or EKS/AKS)
│   │   └── environments/
│   │       ├── dev.tfvars
│   │       └── prod.tfvars
│   ├── scripts/
│   │   ├── seed-keycloak.sh              # Realm + client bootstrap (automated)
│   │   ├── seed-cerbos.sh                # Initial policies
│   │   ├── init-weaviate-schema.py       # Schema BEFORE RAG service starts
│   │   ├── wait-for-services.sh          # Health check — prevent race conditions
│   │   └── test-weaviate-restore.sh      # Monthly restore test (CI)
│   └── README.md                         # Deploy order + component dependencies
├── docs/
│   ├── index.md                          # "Start here" + LEARNING PATH TABLE
│   ├── glossary.md                       # RAG, Semantic Layer, Orchestration, etc.
│   ├── getting-started.md
│   ├── requirements-traceability.md      # FR-ID | Source | ADR | Service | Test | Status
│   ├── architecture/
│   │   ├── overview.md                   # C4 Level 1+2 diagrams
│   │   ├── data-flow.md                  # Request flow: user → Kong → services → response
│   │   └── decisions.md                  # ADR quick-reference index
│   ├── adr/
│   │   ├── README.md                     # ADR index table
│   │   ├── template.md
│   │   ├── ADR-001-multi-tenancy-model.md
│   │   ├── ADR-002-consistency-contract.md
│   │   ├── ADR-003-embedding-model-lock.md
│   │   ├── ADR-004-async-retry-policy.md
│   │   └── ADR-005-local-dev-strategy.md
│   ├── api/
│   │   ├── README.md                     # OpenAPI strategy document
│   │   └── specs/public-api.yaml         # CI-merged spec
│   ├── runbooks/
│   │   ├── incident-response.md
│   │   ├── deployment.md
│   │   └── weaviate-restore.md
│   └── contributing/
│       ├── development.md
│       ├── testing.md
│       ├── style-guide.md
│       └── ai-agent-guide.md             # Story schema, ADR references, naming conventions
├── tests/
│   └── e2e/                              # Playwright P0 flows only
│       ├── chat-query.spec.ts            # Minh: Sales query → result (30s window)
│       ├── approval-workflow.spec.ts     # Hùng: Submit → approve → execute
│       └── admin-user-mgmt.spec.ts       # Lan: Create user + assign role
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                        # Affected-only (dorny/paths-filter)
│   │   └── cd.yml
│   └── PULL_REQUEST_TEMPLATE.md
├── CODEOWNERS                            # Who owns which services/packages
├── CONTRIBUTING.md
├── pyproject.toml                        # uv workspace root
├── .python-version                       # 3.12
├── .env.example                          # ← ALL required vars documented
├── .pre-commit-config.yaml
├── .spectral.yaml                        # OpenAPI linting rules
├── turbo.json                            # Frontend monorepo (Turborepo)
├── Makefile                              # make install | dev | test | lint | build
└── commitlint.config.js
```

---

### FR → Service Mapping

| FR Module | Service | Phase |
|-----------|---------|-------|
| FR-O1-O5 (Agent Orchestration) | `services/orchestration/graph/nodes/` | 1 |
| FR-S1 (Semantic abstraction) | `services/semantic-layer/` | 1 |
| FR-S2 (Metadata catalog) | `services/semantic-layer/` | 1 |
| FR-S3 (SQL AST validation) | `services/data-connector/services/sql_validator.py` | 1 |
| FR-S4 (Query governor) | `services/data-connector/services/query_service.py` | 1 |
| FR-S5 (Cross-domain decomposition) | `services/orchestration/graph/nodes/execute_query.py` | 1 |
| FR-S6 (Result cache) | `services/orchestration/` + Redis | 1 |
| FR-R1-R5 (RAG) | `services/rag/` | 1 |
| FR-A1-A8 (Security) | `infra/keycloak/` + `infra/cerbos/` + `shared/auth/` | 1 |
| FR-M1-M7 (Memory) | `services/orchestration/services/memory_service.py` | 1 |
| FR-F1-F6 (Forecasting) | `services/forecast/` | 2 |
| FR-E1-E4 (Export/Audit) | `services/orchestration/middleware/audit.py` + tasks | 1/2 |
| FR-AD1-AD5 (Administration) | `services/admin-api/` + `apps/admin/` | 1 |

---

### Architectural Boundaries

**Inter-service Communication: Internal HTTP (not shared library)**

```python
# services/orchestration/src/clients/rag_client.py
# Pattern: all service clients follow this template
import httpx
from opentelemetry.propagate import inject

class RAGClient:
    def __init__(self, base_url: str):
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def retrieve(self, query: str, policy_context: dict) -> RetrievalResult:
        headers = {}
        inject(headers)  # OpenTelemetry trace propagation — mandatory
        response = await self._client.post("/v1/retrieve",
            json={"query": query, "policy": policy_context}, headers=headers)
        response.raise_for_status()
        return RetrievalResult(**response.json())
```

**`shared/` package scope:** DTOs + auth helpers + connection singletons + telemetry setup + constants. **NOT** business logic, **NOT** service bridge, **NOT** cross-service state.

---

### Walking Skeleton — Build Order (Mandatory Sequence)

```
Day 1-2: Infrastructure backbone
  → docker-compose.dev.yml: Kong + Keycloak + Cerbos + Weaviate + Redis + PostgreSQL
  → infra/scripts/seed-keycloak.sh (automated realm bootstrap)
  → Gate: docker-compose up → all services healthy

Day 3: Observability BEFORE first service code
  → infra/observability/: otel-collector + Tempo + Grafana
  → shared/aial_shared/telemetry/tracer.py (setup_tracing() called in every service main())
  → Gate: traces visible in Grafana Tempo

Day 4-7: Walking skeleton (mock data only)
  → infra/kong/routes/services.yml (route /v1/chat/query → orchestration)
  → services/orchestration/ stub: POST /v1/query endpoint (return mock)
  → services/rag/ stub: POST /v1/retrieve (return mock chunks)
  → services/data-connector/ stub: DataSourceRegistry
  → Gate: Postman → Kong (JWT check) → Orchestration → Cerbos → RAG (mock) → Response
           with traces appearing in Grafana Tempo (end-to-end distributed trace)

Sprint 1+: Real implementation per service, following FR mapping above
```

---

### Documentation Silos Prevention

**`docs/index.md` Learning Path Table (mandatory):**

| Nếu bạn là... | Đọc theo thứ tự |
|---------------|----------------|
| Engineer mới onboard | getting-started → architecture/overview → contributing/ |
| AI coding agent | architecture/overview → adr/ → services/\*/README.md → ai-agent-guide |
| DevOps / Infra | getting-started → infra/README.md → runbooks/ |
| Product / Stakeholder | architecture/overview → docs/api/ |

**Service README "Responsibility Boundary" section (mandatory):**
```markdown
## Responsibility Boundary
**Owns:** [list what this service is responsible for]
**Does NOT own:** [list what it deliberately delegates to other services]
```

**`services/orchestration/README.md` additional sections:**
```markdown
## Agent Routing Decision Tree
User Query
├── Structured data → semantic-layer → data-connector → Oracle
├── Document/unstructured → rag → Weaviate
├── Forecast request → forecast service (async)
└── Admin action → admin-api

## State Management
- Short-term (session): Redis TTL 1h
- Medium-term (30 sessions): PostgreSQL summaries
- Long-term (preferences): PostgreSQL vector search

## Failure Modes
| Scenario | Behavior | Recovery |
|----------|----------|----------|
| RAG service down | Fallback to cached results | Auto-retry 3x |
| LLM timeout > 30s | Return partial + suggest retry | Alert runbook |
| Oracle VPD context leak | Detected by integration test | Block deploy |
```

---

## Implementation Patterns & Consistency Rules

> **Mục đích:** Đảm bảo mọi AI agent implement code tương thích — không conflict về naming, structure, format, hoặc communication patterns.
> **Nguồn:** Steps 2-4 + Party Review (Amelia + Paige + John)

---

### Quick Reference Index

> AI agent đang implement feature → tìm pattern liên quan trong < 30 giây:

| Đang implement... | Xem section |
|-------------------|-------------|
| DB table / column | §NM-1 Database Naming |
| REST API endpoint | §NM-2 API Naming + §FMT-1 Response Format |
| Python service / class | §NM-3 Python Naming |
| TypeScript component / hook | §NM-4 TypeScript Naming |
| Cross-layer (DB → API → Python → TS) | §NM-5 Cross-Layer Mapping |
| Celery background task | §CM-1 Celery Tasks |
| Redis cache / session key | §CM-2 Redis Keys |
| LangGraph agent node | §CM-3 LangGraph Patterns |
| Frontend server state | §CM-4 TanStack Query |
| Frontend UI / stream state | §CM-5 Zustand Patterns |
| API success / error response | §FMT-1 Response Format |
| SSE streaming event | §FMT-2 SSE Event Format |
| Error handling (backend) | §PR-1 Error Handling Backend |
| Error handling (frontend) | §PR-2 Error Handling Frontend |
| Logging | §PR-3 Logging |

---

### Phase 1 Minimal Patterns vs Full Patterns

> **John (PM):** Developer không được đọc 20+ trang trước khi viết dòng code đầu tiên. Tách rõ 2 tiers.

**🔴 Phase 1 Mandatory — Non-negotiable ngay từ Sprint 1:**
1. Tất cả naming conventions (§NM-1 đến §NM-5) — zero runtime cost, rất đắt nếu refactor sau
2. Celery `acks_late=True` + `reject_on_worker_lost=True` — data loss không chấp nhận được
3. Embedding dimension via config — migration cost quá cao nếu hardcode
4. `AIALException` base class (1 class đơn giản, không cần full hierarchy)
5. Basic file structure patterns (§ST-1, §ST-2)
6. `AIALGraphState` TypedDict contract (nếu dùng LangGraph)
7. Celery idempotency key convention

**🟠 Phase 1 Optional — Implement khi có time:**
- `StreamErrorBoundary` — chỉ khi streaming features đã ship
- `useSSEStream` custom hook — same
- `structlog` — `logging.basicConfig()` chấp nhận được ban đầu; adopt khi cần trace production issues

**Phase 1 mandatory security lock**
- Cerbos policy engine integration → KHÔNG defer; Phase 1 phải deploy Cerbos cùng Kong/Keycloak. Baseline `principal.attr` schema lock sớm với `department` và `clearance`; Epic sau chỉ extend, không được backfill JWT mapping

**🟡 Defer to Phase 2:**
- RFC 9457 full compliance → dùng simple `{success, data, error}` envelope Phase 1
- Full `AIALException` hierarchy → đừng design failure modes trước khi biết mình sẽ fail ở đâu

---

### §NM-1 Database Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Table names | `snake_case`, **plural** | `audit_logs`, `conversation_memories`, `kpi_definitions` |
| Column names | `snake_case` | `user_id`, `created_at`, `department_id` |
| Primary key | luôn là `id` (UUID) | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| Foreign keys | `{singular_table}_id` | `session_id`, `user_id`, `kpi_definition_id` |
| Indexes | `idx_{table}_{column(s)}` | `idx_audit_logs_user_id`, `idx_sessions_created_at` |
| Timestamps | `created_at`, `updated_at` — auto-managed, `TIMESTAMPTZ` | required on all tables |
| Weaviate collections | `PascalCase`, **singular** | `Document`, `ConversationChunk`, `KpiDefinition` |
| Weaviate properties | `camelCase` | `userId`, `departmentId`, `contentText`, `modelVersion` |

---

### §NM-2 API Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Resource names | `kebab-case`, **plural** | `/v1/chat-sessions`, `/v1/audit-logs`, `/v1/kpi-definitions` |
| Path parameters | `snake_case` | `/v1/chat-sessions/{session_id}` |
| Query parameters | `snake_case` | `?start_date=2026-01-01&department_id=sales&page_size=20` |
| Custom HTTP headers | `X-{PascalCase}` | `X-Trace-Id`, `X-Department-Id`, `X-Request-Id` |
| Trailing slash | **KHÔNG bao giờ** | `/v1/users` ✅ — `/v1/users/` ❌ |
| HTTP verbs | semantic | `GET` list, `POST` create, `PATCH` partial update, `DELETE` remove |

---

### §NM-3 Python Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Variables, functions | `snake_case` | `user_id`, `get_query_result()`, `session_identifier` |
| Classes | `PascalCase` | `QueryOrchestrator`, `LLMAdapter`, `OracleConnector` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT = 3`, `DEFAULT_TIMEOUT_MS = 30000` |
| Private members | `_underscore_prefix` | `_internal_validate()`, `_cached_result` |
| Modules / files | `snake_case` | `query_service.py`, `litellm_adapter.py`, `oracle_connector.py` |
| Pydantic models | `PascalCase` + layer suffix | `QueryRequest`, `QueryResponse`, `QueryDB` |
| **No abbreviations** | Full words | `session_identifier` không phải `sess_id`; `user_id` không phải `uid` |

---

### §NM-4 TypeScript Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Variables, functions | `camelCase` | `userId`, `getQueryResult()`, `handleStreamChunk()` |
| React components | `PascalCase` | `StreamingMessage`, `DataTable`, `ApprovalModal` |
| Component files | `PascalCase.tsx` | `StreamingMessage.tsx`, `DataTable.tsx` |
| Non-component files | `camelCase.ts` | `useSSEStream.ts`, `queryService.ts`, `errorMessages.ts` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_STREAM_TIMEOUT_MS = 30000` |
| Types / Interfaces | `PascalCase`, no `I` prefix | `QueryResult`, `StreamStatus`, `UserPermission` |
| Zustand stores | `use{Name}Store` | `useStreamStore`, `useSessionStore`, `useUiStore` |
| Custom hooks | `use{PascalCase}` | `useSSEStream`, `useQueryResult`, `usePermissions` |
| Enum values | `PascalCase` | `StreamStatus.Streaming`, `IntentType.SQL` |

---

### §NM-5 Cross-Layer Naming Mapping

> AI agents thường làm việc trên một entity qua nhiều layers. Bảng này là source of truth.

| Concept | DB Table | API URL | JSON field | Python Class | TS Type |
|---------|----------|---------|------------|--------------|---------|
| Chat session | `chat_sessions` | `/v1/chat-sessions` | `chatSession` | `ChatSession` | `ChatSession` |
| Audit log | `audit_logs` | `/v1/audit-logs` | `auditLog` | `AuditLog` | `AuditLog` |
| KPI definition | `kpi_definitions` | `/v1/kpi-definitions` | `kpiDefinition` | `KpiDefinition` | `KpiDefinition` |
| Conversation memory | `conversation_memories` | `/v1/conversations/{id}/memories` | `conversationMemory` | `ConversationMemory` | `ConversationMemory` |
| Approval request | `approval_requests` | `/v1/approval-requests` | `approvalRequest` | `ApprovalRequest` | `ApprovalRequest` |

**Rule:** Python Pydantic models dùng `alias_generator=to_camel` để auto-convert snake_case → camelCase trong JSON output. Không manually alias từng field.

```python
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

class QueryResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    session_id: str          # serializes as "sessionId"
    created_at: datetime     # serializes as "createdAt"
```

---

### §ST-1 Backend Service File Structure

> Mọi FastAPI service tuân theo structure này — không tự sáng tạo:

```
services/{service-name}/
├── src/
│   └── {service_module}/
│       ├── main.py              # FastAPI app, startup/shutdown, middleware registration
│       ├── routes/              # Thin route handlers — delegate to services, no business logic
│       │   ├── __init__.py
│       │   └── {domain}.py
│       ├── services/            # Business logic orchestration
│       │   └── {domain}_service.py
│       ├── repositories/        # Data access (DB, cache, vector store) — no business logic
│       │   └── {domain}_repo.py
│       ├── models/
│       │   ├── requests.py      # Pydantic input models
│       │   ├── responses.py     # Pydantic output models
│       │   └── db.py            # DB-specific models (SQLAlchemy/ORM)
│       ├── adapters/            # External service adapters (LLM, Oracle, etc.)
│       │   └── llm/
│       │       ├── base.py      # Abstract interface (ABC)
│       │       └── litellm.py   # Concrete LiteLLM implementation
│       ├── tasks/               # Celery tasks — thin wrappers, delegate to services
│       │   └── {domain}_task.py
│       ├── graph/               # LangGraph graphs (orchestration service only)
│       │   ├── state.py         # AIALGraphState TypedDict
│       │   ├── nodes/           # Individual node functions
│       │   └── graph.py         # Graph assembly
│       └── core/
│           ├── config.py        # Pydantic Settings
│           ├── deps.py          # FastAPI dependencies (DI)
│           ├── middleware.py    # Auth, tracing, logging
│           └── exceptions.py   # AIALException + subclasses
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml
└── README.md
```

---

### §ST-2 Frontend App File Structure

```
apps/{app-name}/src/
├── routes/                  # TanStack Router file-based routes
│   └── _authenticated/      # All auth-gated routes live here
├── components/
│   ├── streaming/           # 5 streaming components (useSSEStream consumers)
│   └── ui/                  # shadcn/ui overrides only
├── hooks/
│   └── useSSEStream.ts      # SINGLE SOURCE OF TRUTH — shared SSE hook
├── stores/
│   ├── streamStore.ts       # Active stream state (Zustand slice)
│   └── uiStore.ts           # Sidebar, modal, theme
├── services/                # API call functions — wrap TanStack Query
├── types/                   # TypeScript types — no business logic
└── utils/
    └── errorMessages.ts     # error.type → user-friendly message mapping
```

---

### §FMT-1 API Response Format

**Success — single resource:**
```json
{"data": {"id": "uuid", "sessionId": "..."}, "meta": {"generatedAt": "2026-04-24T10:30:00Z"}}
```

**Success — list/paginated:**
```json
{"data": [...], "meta": {"total": 100, "page": 1, "limit": 20, "generatedAt": "2026-04-24T10:30:00Z"}}
```

**Error — RFC 9457 (Phase 2 full compliance; Phase 1: simple envelope acceptable):**
```json
{
  "type": "https://aial.internal/errors/permission-denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "User does not have access to FINANCE schema",
  "instance": "/v1/chat/query",
  "trace_id": "abc-123-def"
}
```

**Phase 1 simple envelope (acceptable until Phase 2):**
```json
{"success": false, "error": "Permission denied", "trace_id": "abc-123"}
```

**FastAPI exception pattern:**
```python
# core/exceptions.py
class AIALException(HTTPException):
    def __init__(self, error_type: str, title: str, status: int, detail: str, trace_id: str = ""):
        super().__init__(status_code=status, detail={
            "type": f"https://aial.internal/errors/{error_type}",
            "title": title, "status": status, "detail": detail, "trace_id": trace_id
        })

# ĐÚNG — route handler
@router.get("/data")
async def get_data(user: User = Depends(get_current_user)):
    raise AIALException("permission-denied", "Permission Denied", 403, "No access to schema")

# SAI — raw HTTPException
raise HTTPException(status_code=403, detail="Permission denied")  ❌
```

---

### §FMT-2 SSE Event Format

> Data field schemas phải exact — AI agents implement streaming differently if not specified:

```
# Chunk event — streaming text token
data: {"type": "chunk", "content": "string token", "index": 0, "trace_id": "abc"}

# Tool call event — SQL being generated
data: {"type": "tool_call", "tool": "sql_generator", "status": "running", "trace_id": "abc"}

# Done event — stream complete
data: {"type": "done", "query_id": "xyz", "sources": [{"doc_id": "...", "title": "...", "page": 1}], "generated_at": "2026-04-24T10:30:00Z", "trace_id": "abc"}

# Error event — stream failed
data: {"type": "error", "error_code": "timeout|permission-denied|llm-unavailable", "message": "user-friendly string", "trace_id": "abc"}
```

---

### §CM-1 Celery Task Patterns

**Naming — `{service}.{domain}.{action}_{entity}` with bounded verbs:**

| Verb | Use when |
|------|---------|
| `process` | transform/analyze data |
| `generate` | create new artifacts |
| `fetch` | retrieve from external source |
| `notify` | send notifications/webhooks |
| `sync` | reconcile state between systems |
| `export` | produce downloadable output |

```python
# ĐÚNG — namespaced + bounded verb
@celery_app.task(name="orchestration.query.process_request",
                 acks_late=True, reject_on_worker_lost=True)
@celery_app.task(name="forecast.time_series.generate_report")
@celery_app.task(name="export.excel.generate_report")
@celery_app.task(name="rag.document.sync_index")

# SAI — no namespace or unbounded verb
@celery_app.task(name="run_query")  ❌
@celery_app.task  ❌  # auto-name từ module path
```

**Idempotency key (bắt buộc — tránh retry storms):**
```python
task.apply_async(
    args=[payload],
    task_id=f"{trace_id}-{task_name}",  # deterministic, idempotent
    countdown=0
)
```

**Thin task pattern (fat tasks là anti-pattern):**
```python
# ĐÚNG — thin task, delegate to service
@celery_app.task(name="export.excel.generate_report", acks_late=True, reject_on_worker_lost=True)
def generate_excel_report(payload: dict) -> dict:
    service = ExportService()
    return service.generate_excel(ExportRequest(**payload))

# SAI — fat task với 200 lines business logic ❌
```

**Celery → SSE error bridge (khi task fail → user thấy error trong stream):**
```python
@celery_app.task(bind=True, max_retries=3, name="orchestration.query.process_request")
def process_query(self, payload: dict):
    try:
        ...
    except AIALException as e:
        redis_client.xadd(
            f"aial:stream:{payload['trace_id']}",
            {"type": "error", "error_code": e.error_type, "message": e.detail,
             "trace_id": payload["trace_id"]}
        )
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
```

**Celery production config (set tại celery app init):**
```python
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
)
```

**Retry policy:**
```python
@celery_app.task(max_retries=3, default_retry_delay=2,
                 autoretry_for=(TransientError,), retry_backoff=True)
```

---

### §CM-2 Redis Key Patterns

**Format: `aial:{service}:{entity}:{id}:{field}`**

```python
# Examples
f"aial:session:{session_id}:context"              # Session memory
f"aial:cache:query:{intent_hash}:result"          # Semantic result cache
f"aial:rate:{user_id}:daily_count"                # Rate limit counter
f"aial:dlq:forecast:time_series"                  # Dead letter queue
f"aial:schema_version:oracle:{source_id}"         # Schema version
f"aial:lock:export:{job_id}"                      # Distributed lock
f"aial:stream:{trace_id}"                         # SSE event stream (Redis Streams)
```

**TTL policy (bắt buộc — không dùng TTL mặc định):**
```python
REDIS_TTL = {
    "session":       3600,    # 1 hour — short-term conversation memory
    "cache:query":   300,     # 5 minutes — semantic result cache
    "cache:metadata":3600,   # 1 hour — schema/glossary cache
    "rate":          86400,   # 24 hours — daily rate limit counter
    "lock":          30,      # 30 seconds — distributed locks
    "stream:status": 86400,   # 24 hours — SSE stream status
}
```

**Environment prefix nếu cần isolate:** `aial:{env}:{...}` với `env` = `dev`, `staging`, `prod`.

---

### §CM-3 LangGraph Node Patterns

**Shared State Contract — định nghĩa trong `services/orchestration/src/orchestration/graph/state.py`:**
```python
from typing import TypedDict
from langchain_core.messages import BaseMessage

class AIALGraphState(TypedDict, total=False):
    # Core — required on every node
    trace_id: str
    session_id: str
    user_id: str
    department_id: str
    # Conversation
    messages: list[BaseMessage]
    # Routing
    intent_type: str          # "sql" | "rag" | "hybrid" | "forecast" | "fallback"
    current_node: str
    # Results
    sql_result: dict | None
    rag_result: dict | None
    final_response: str | None
    # Control
    error: dict | None
    should_abort: bool
```

**Node pattern — pure function returning partial dict:**
```python
# ĐÚNG — partial state update, no mutation, no side effects
async def classify_intent_node(state: AIALGraphState) -> dict:
    async with asyncio.timeout(10):  # node-level timeout
        intent = await intent_classifier.classify(state["messages"][-1].content)
    return {"intent_type": intent.value, "current_node": "classify_intent"}
    # LangGraph tự merge partial dict vào full state

# SAI — mutation
def classify_intent_node(state: AIALGraphState) -> AIALGraphState:
    state["intent_type"] = "sql"  ❌ mutation
    return state
```

**Node naming convention:** `{verb}_{noun}` in snake_case
```python
def classify_intent(state): ...      # classify + intent
def retrieve_context(state): ...     # retrieve + context
def generate_response(state): ...    # generate + response
def validate_permissions(state): ... # validate + permissions
```

**Edge (condition) naming:** `route_by_{criterion}`
```python
graph.add_conditional_edges("classify_intent", route_by_intent_type, {
    "sql": "validate_permissions",
    "rag": "retrieve_context",
    "fallback": "generate_fallback_response",
})
```

**Checkpointer (bắt buộc cho production):**
```python
from langgraph.checkpoint.redis import RedisSaver

checkpointer = RedisSaver(redis_client)
graph = workflow.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": session_id}}  # thread_id = session_id
result = await graph.ainvoke(initial_state, config=config)
```

**Anti-patterns trong LangGraph nodes:**
```python
# ❌ Node gọi trực tiếp infra
def query_node(state):
    db = get_db_session()  # side effect

# ✅ Inject dependency qua closure
def make_query_node(repo: QueryRepository):
    async def query_node(state: AIALGraphState) -> dict:
        result = await repo.find(state["session_id"])
        return {"sql_result": result}
    return query_node
```

---

### §CM-4 TanStack Query Patterns

**Query key factory (bắt buộc — ngăn cache invalidation bugs):**
```typescript
// types/queryKeys.ts
export const queryKeys = {
  chatSessions: {
    all:    () => ['chat-sessions'] as const,
    lists:  () => [...queryKeys.chatSessions.all(), 'list'] as const,
    detail: (id: string) => [...queryKeys.chatSessions.all(), 'detail', id] as const,
  },
  auditLogs: {
    all:    () => ['audit-logs'] as const,
    filtered: (f: AuditLogFilters) => [...queryKeys.auditLogs.all(), f] as const,
  },
  kpiDefinitions: {
    all:    () => ['kpi-definitions'] as const,
    byDomain: (domainId: string) => [...queryKeys.kpiDefinitions.all(), domainId] as const,
  },
}

// Usage
const { data } = useQuery({ queryKey: queryKeys.chatSessions.detail(sessionId), queryFn: ... })
queryClient.invalidateQueries({ queryKey: queryKeys.chatSessions.lists() })
```

**SAI — string keys:**
```typescript
useQuery({ queryKey: 'chat-sessions' })       ❌
useQuery({ queryKey: 'chat-sessions-list' })  ❌
```

---

### §CM-5 Zustand State Patterns

**3-layer state architecture:**
```typescript
// stores/streamStore.ts — Active stream state
interface StreamState {
  queryId: string | null
  status: 'idle' | 'connecting' | 'thinking' | 'streaming' | 'complete' | 'error'
  chunks: string[]
  error: string | null
  abortController: AbortController | null
}

// stores/uiStore.ts — Ephemeral UI state
interface UiState {
  sidebarOpen: boolean
  activeModal: string | null
  theme: 'light' | 'dark'
}

// TanStack Query — Server state (settled query results, no Zustand)
```

**Immutable updates (bắt buộc):**
```typescript
// ĐÚNG
set((state) => ({
  ...state,
  chunks: [...state.chunks, newChunk],
  status: 'streaming',
}))

// SAI — mutation
set((state) => { state.chunks.push(newChunk) })  ❌
set((state) => { state.status = 'streaming' })   ❌
```

**On stream complete → commit to TanStack Query:**
```typescript
// streamStore.ts
const commitToQueryCache = (queryId: string, finalResult: QueryResult) => {
  queryClient.setQueryData(queryKeys.chatSessions.detail(queryId), finalResult)
  set({ status: 'complete', chunks: [] })
}
```

---

### §PR-1 Error Handling — Backend

```python
# ĐÚNG — custom exception + RFC 9457
class PermissionDeniedError(AIALException):
    def __init__(self, resource: str, trace_id: str):
        super().__init__("permission-denied", "Permission Denied", 403,
                         f"Access to {resource} denied", trace_id)

# ĐÚNG — không swallow exceptions
async def get_data(user: User):
    try:
        return await service.get(user.id)
    except PermissionDeniedError:
        raise  # re-raise, không swallow
    except Exception as e:
        logger.error("unexpected_error", error=str(e), trace_id=ctx.trace_id)
        raise AIALException("internal-error", "Internal Error", 500, "Unexpected error")

# SAI
except Exception:
    return None  ❌  # swallow silently
```

---

### §PR-2 Error Handling — Frontend

```typescript
// components/errors/boundaries.tsx
// StreamErrorBoundary — wrap every streaming component
// PageErrorBoundary — wrap every route page
// AppErrorBoundary — root level

// utils/errorMessages.ts — RFC 9457 type → user-friendly
export const ERROR_MESSAGES: Record<string, { message: string; action: string }> = {
  'permission-denied': {
    message: 'Bạn không có quyền xem dữ liệu này.',
    action: 'Liên hệ IT Admin để được cấp quyền.',
  },
  'query-timeout': {
    message: 'Truy vấn mất quá nhiều thời gian.',
    action: 'Thử thu hẹp phạm vi thời gian.',
  },
  'llm-unavailable': {
    message: 'Hệ thống AI tạm thời không khả dụng.',
    action: 'Thử lại sau vài phút.',
  },
}
// Users KHÔNG BAO GIỜ thấy raw error JSON hoặc stack trace
```

---

### §PR-3 Logging

```python
# ĐÚNG — structlog JSON, no PII, no raw data
import structlog
log = structlog.get_logger()

log.info("query_executed",
    trace_id=trace_id, user_id=user_id,
    department_id=dept_id, intent_type=intent.value,
    latency_ms=elapsed, rows_returned=row_count, cache_hit=from_cache
)

# SAI — KHÔNG BAO GIỜ log
log.info("query", query_text=user_query)   ❌  # user input
log.info("result", data=query_result)      ❌  # raw Oracle data
log.info("user", name=user.full_name)      ❌  # PII
print(f"Debug: {user_query}")              ❌  # production code
```

**Blocking I/O trong async routes (anti-pattern):**
```python
# SAI — blocks event loop
@router.get("/data")
async def get_data():
    result = requests.get(external_url)  ❌

# ĐÚNG
async def get_data():
    async with httpx.AsyncClient() as client:
        result = await client.get(external_url)  ✅
```

---

### §PR-4 Decision Trees

**Which naming convention?**
```
Đang đặt tên cho...
├── DB object → snake_case (table: plural, column: singular concept)
├── API URL path → kebab-case, plural (/chat-sessions)
├── API JSON field → camelCase (chatSession)
├── Python → snake_case vars/functions, PascalCase classes
└── TypeScript → camelCase vars/functions, PascalCase components
```

**Which response format?**
```
API result?
├── Success, single → {data: {...}, meta: {...}}
├── Success, list → {data: [...], meta: {total, page, limit}}
├── Success, no content (DELETE) → 204 No Content
├── Client error 4xx → RFC 9457 Problem Details (Phase 2) / {success:false, error} (Phase 1)
└── Streaming → SSE events per §FMT-2
```

**Sync vs async task?**
```
Operation duration?
├── < 1 second → Synchronous API response
├── 1-30 seconds → Async với polling endpoint
└── > 30 seconds hoặc retry logic → Celery task (§CM-1)
    └── Task type verb?
        ├── Transform/analyze → process_{entity}
        ├── Create artifact → generate_{entity}
        ├── Retrieve external → fetch_{entity}
        ├── Send notification → notify_{entity}
        ├── Reconcile state → sync_{entity}
        └── Produce download → export_{entity}
```

---

### §ENFORCE — All AI Agents MUST

**Phase 1 Non-negotiable:**
1. Follow naming conventions §NM-1 đến §NM-5 — mọi file, class, function
2. `acks_late=True` + `reject_on_worker_lost=True` cho mọi Celery task
3. Embedding dimension via `EMBEDDING_DIM` env var — không hardcode `1024`
4. Sử dụng `AIALGraphState` TypedDict từ `graph/state.py` — không tự define state
5. Celery idempotency key: `task_id=f"{trace_id}-{task_name}"`
6. File structure theo §ST-1 (backend) và §ST-2 (frontend)
7. Thin Celery tasks — delegate sang service layer

**Anti-patterns (tuyệt đối tránh):**
```
❌ Hardcode embedding dimension (1024)
❌ Raw HTTPException thay vì AIALException
❌ Blocking requests.get() trong async route
❌ LangGraph node mutate state thay vì return partial dict
❌ Fat Celery tasks với business logic
❌ SSE connection per component (dùng useSSEStream)
❌ Mutation trong Zustand set()
❌ String TanStack Query keys (dùng queryKeys factory)
❌ Log user query text, SQL results, hoặc PII
❌ Hardcode Redis key strings (dùng constants)
❌ Skip Cerbos policy check (Phase 2 mandatory)
```

---

## Core Architectural Decisions

> **Nguồn:** PRD v2.1 + Steps 2-3 + Party Review (Winston + John + Sally)

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- ADR-001: Multi-tenancy model → cần governance sign-off trước khi lock
- ADR-003: Embedding model lock → cần accuracy benchmark trước Phase 1 launch
- Error Boundary hierarchy → phải design trước khi code streaming components
- Oracle VPD context isolation → phải có integration test trước staging deploy

**Important Decisions (Shape Architecture):**
- ADR-002: Consistency contract → giữ 5 phút, thêm data timestamp UI
- ADR-004: Async retry policy → locked
- Stream state management → Zustand slice riêng cho active streams
- K8s namespace strategy → per-environment với ResourceQuota + NetworkPolicy

**Deferred (Post-MVP):**
- i18n foundation: `react-i18next` — setup foundation nhưng không implement full i18n MVP
- Design token system — defer cho Phase 2 khi brand solidified
- gRPC, Kafka, Redis Pub/Sub — revisit khi services > 10 hoặc throughput > 10K events/s

---

### Data Architecture

**Technology Versions (verified April 2026):**
- PostgreSQL 16+, Redis 7+, Weaviate latest, LangGraph 1.1.8 (GA)

**ADR-001 — Multi-tenancy Model: Shared Schema + Row-Level Security**

> ⚠️ **Governance blocker:** Phải có sign-off từ IT Admin (Lan) và Compliance Officer về policy isolation requirements trước khi lock ADR này. Nếu có policy yêu cầu hard isolation giữa departments → phải dùng separate schema.

- Oracle VPD (Virtual Private Database) enforce RLS tại DB engine layer — predicate injected trực tiếp vào SQL, không thể bypass từ application
- Cerbos ABAC enforce tại application layer (defense-in-depth)
- PostgreSQL RLS cho metadata/audit/memory
- Weaviate: collection-per-department (isolation tại collection level)

**VPD Security Guardrails (bắt buộc — không optional):**

| Guardrail | Risk | Implementation |
|-----------|------|----------------|
| **Connection pool context reset** | Thread A set VPD context dept X, Thread B lấy connection chưa reset → data leak | `ALTER SESSION SET CONTEXT` trong cùng transaction scope; pool force context reset trước khi release connection; integration test explicit |
| **Zero DDL privileges** | CTAS (`INSERT INTO ... SELECT *`) hoặc materialized view tạo bởi user có DDL → bypass VPD | Service account chỉ có DML trên specific tables, zero DDL (`CREATE TABLE`, `CREATE MATERIALIZED VIEW`) |
| **K-anonymity aggregates** | `AVG(salary)` với group size = 1 → individual value exposed (de-anonymization) | Policy: suppress aggregates khi `COUNT(*) < 5`; return "Insufficient data" thay vì actual value |

**Integration test requirement:** Oracle VPD context isolation phải có automated test suite kiểm tra context không bị leak giữa concurrent requests.

---

**ADR-002 — Consistency Contract**

| Domain | Staleness Tolerance | Rationale |
|--------|-------------------|-----------|
| SQL query results | ≤ 5 phút | Sales/Finance data phải recent; Finance month-end có thể cần direct query bypass cache (Phase 2) |
| RAG document index | ≤ 60 phút | Documents ít thay đổi hơn |
| Permission/ABAC cache | ≤ 5 phút | Security critical |
| Semantic result cache | ≤ 30 phút | Per data freshness class |
| LLM response cache | ≤ 15 phút (semantic similarity) | Query-dependent |

> **UI requirement (từ ADR-002):** Mọi query result phải hiển thị timestamp rõ ràng: *"Dữ liệu tính đến: 09:00:23"*. Transparency giải quyết trust issue tốt hơn giảm staleness window. Frontend design requirement bắt buộc.

---

**ADR-003 — Embedding Model Lock: `bge-m3` (BAAI)**

> ⚠️ **Accuracy benchmark blocker:** Phải chạy benchmark với 50-100 sample queries từ actual company data (Minh/Tuấn/Hoa) trước Phase 1 launch. User trust threshold: < 85% correct = users abandon. Benchmark done trong Sprint 1.

- **Model:** `bge-m3` (BAAI) — multilingual, Vietnamese native support, self-hostable
- **Dimension:** 1024 — abstract như config value, không hardcode trong code
- **Lý do không chọn `text-embedding-3-large`:** OpenAI vendor lock-in + cost at scale + cloud dependency conflicts với Sovereign AI principle
- **Model version tracking:** Lưu `model_version` field cùng với vector trong Weaviate schema — bắt buộc cho future migration
- **Hardware:** ~4-8GB VRAM nếu GPU; CPU fallback ~200-500ms latency — benchmark trước production

```python
# ĐÚNG — abstract dimension
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# SAI — hardcode
vector = model.encode(text)  # assumes 1024 dims
```

---

**ADR-004 — Async Job Retry Policy**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Max retries | 3 | Sau 3 lần = lỗi hệ thống, không phải transient |
| Backoff | Exponential: 2s → 4s → 8s | Tránh thundering herd |
| Dead letter queue | Redis Streams `aial:dlq:{job_type}` | Forensics + manual replay |
| Forecast timeout | 300s | Heavy computation |
| Export timeout | 60s | File generation |
| Alert threshold | DLQ > 10 jobs → oncall alert | Operational visibility |

**Celery production config (bắt buộc — default config không safe):**
```python
CELERY_TASK_ACKS_LATE = True           # Ack sau khi task complete, không phải khi nhận
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject task nếu worker crash
CELERY_TASK_TRACK_STARTED = True       # Track in-progress tasks
```

---

**Data Migration Strategy:**
- PostgreSQL: Alembic (auto-generate migrations, version controlled)
- Weaviate: custom migration scripts (`services/rag/migrations/`) — không có Alembic equivalent
- `weaviate/schema.py` là single source of truth cho collection bootstrap; Epic 2A owns bootstrap contract, Epic 3 consumes, không fork schema ownership
- `services/embedding/client.py` là shared `bge-m3` client scaffold; Phase 1 phải tạo interface contract trước khi Epic 2A và Epic 3 chạy song song
- Trigger: schema change → CI run migration scripts → verify index health

---

### Authentication & Security

**Stack (locked):** Keycloak (IdP) + Cerbos ABAC (policy) + Oracle VPD (DB-level) + AES-256 at rest + TLS 1.3 in transit

**Oracle Connection Security:**
```
User request → Keycloak JWT → Orchestration → Cerbos policy check
  → Oracle Connector: SessionPool với user_proxy mode
  → Oracle VPD: enforce RLS với user identity context
  → Connection released: context PHẢI reset về neutral state
```
Không dùng shared DBA account. `cx_Oracle.SessionPool` với `homogeneous=False` (heterogeneous pool) để support per-user proxy.

**Cerbos principal contract (Phase 1 lock):**
- Baseline `principal.attr` schema: `department`, `clearance`
- JWT mapping cho 2 attrs này phải được lock trong Epic 2A trước khi Epic 4 mở rộng ABAC
- ADR bắt buộc: `Cerbos principal.attr schema frozen at Epic 2A`

**Secret Management:**
| Environment | Strategy |
|-------------|---------|
| Local dev | HashiCorp Vault dev mode + Pydantic Settings injection pattern (không hardcode, không commit) |
| Staging | K8s ConfigMap + Vault Agent Sidecar |
| Production | HashiCorp Vault (dynamic secrets Oracle, LLM API keys) + K8s Secrets |

Pattern: `pydantic_settings.BaseSettings` với `env_file` auto-detection theo environment.

---

### API & Communication Patterns

**Inter-service Communication:**

| Pattern | When | Technology |
|---------|------|-----------|
| Sync REST | orchestration → rag, → data-connector, → semantic-layer | FastAPI internal HTTP |
| Async jobs | Export, bulk forecast, scheduled reports | Celery 5.x + Redis Streams |
| SSE streaming | LLM response → Chat UI | FastAPI `StreamingResponse` + SSE |
| Health/readiness | Kong → services | FastAPI `/health` + `/ready` |

> **Scale checkpoint:** Revisit gRPC khi services > 10; revisit Kafka khi event throughput > 10K/s. Không migrate sớm hơn khi chưa có evidence.

> **LLM call risk:** Mọi LLM calls phải đi qua Celery async — không có sync HTTP path cho LLM requests (30-60s response = connection pool exhaustion at scale). Audit trước staging.

**Error Handling Standard — RFC 9457 Problem Details:**
```json
{
  "type": "https://aial.internal/errors/permission-denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "User does not have access to FINANCE schema",
  "instance": "/v1/chat/query",
  "trace_id": "abc-123"
}
```

> **Frontend requirement (từ RFC 9457):** Users không bao giờ thấy raw error JSON. Frontend phải maintain **error message mapping table**: `error.type` → user-friendly message → suggested action. Ví dụ: `permission-denied` → *"Bạn không có quyền xem dữ liệu này. Liên hệ IT Admin để được cấp quyền."*

**API Versioning:** `/v1/` (Phase 1-2), `/v2/` (Phase 3+). Backward compatible. Kong routes handle version dispatch.

---

### Frontend Architecture

**Tech Stack (locked):**
- Framework: React 18 + Vite 6 + TypeScript
- UI: shadcn/ui (copy-paste components)
- Charts: Recharts (default) + lazy-loaded Plotly (admin edge cases)
- TanStack Query 5.99.2 (server state) + TanStack Router 1.168.23 (routing)
- Zustand (client UI state + active stream state)
- React Hook Form + Zod (forms)
- SSE: `eventsource-parser` npm (không dùng native EventSource — không support custom headers/JWT)

**State Management Architecture (3 layers):**

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: TanStack Query — Server State               │
│   Settled query results, paginated data, user prefs  │
├─────────────────────────────────────────────────────┤
│ Layer 2: Zustand — UI State + Active Stream State    │
│   Sidebar, modals, theme                             │
│   Stream slice: { chunks[], streamStatus,           │
│     abortController, queryId }                       │
│   On stream complete: commit to TanStack Query cache │
│   via queryClient.setQueryData()                     │
├─────────────────────────────────────────────────────┤
│ Layer 3: Local Component State — Derived/Ephemeral   │
│   Animation states, hover, focus, transient UI       │
└─────────────────────────────────────────────────────┘
```

**Shared SSE Hook — `useSSEStream` (bắt buộc):**

5 streaming components KHÔNG được tự manage SSE connection riêng. Phải dùng shared hook:
```typescript
// src/hooks/useSSEStream.ts
function useSSEStream<T>(url: string, options: SSEOptions) {
  // - Wrap eventsource-parser + fetch()
  // - JWT Bearer token injection tự động
  // - Reconnect logic với exponential backoff
  // - AbortController cleanup on unmount
  // - Returns: { chunks, status, error, abort }
}
```

**Error Boundary Hierarchy (bắt buộc trước khi code streaming components):**
```tsx
<AppErrorBoundary>          {/* Fatal errors — show error page */}
  <PageErrorBoundary>       {/* Page-level errors — show error within layout */}
    <StreamErrorBoundary>   {/* Stream-specific — show retry/fallback */}
      <ProgressiveDataTable />
      <StreamingMessage />
    </StreamErrorBoundary>
  </PageErrorBoundary>
</AppErrorBoundary>
```
Không có hierarchy này → stream error crash toàn bộ app.

**TanStack Router — Convention Document (lập trước khi implement):**
```
routes/
  _authenticated/              ← layout route (auth guard)
    chat/
      index.tsx                ← Chat UI main
      history.lazy.tsx         ← Conversation history
    admin/
      _layout.tsx              ← Admin layout
      approvals/
        index.lazy.tsx         ← Hùng's approval queue
        $requestId/
          review.lazy.tsx      ← Review screen
      kpi/
        $domainId/
          edit.tsx             ← Nam's KPI management
```
`.lazy.tsx` suffix bắt buộc cho tất cả non-critical routes (enforce qua ESLint rule).

**Optimistic UI Policy:**

| Action | Strategy | Lý do |
|--------|---------|-------|
| Approve/Reject query (Hùng) | Pessimistic (chờ server) | Business consequences — không thể rollback |
| Send chat message (Minh) | Optimistic (hiển thị ngay) | Low risk, UX benefits |
| Update KPI definition (Nam) | Pessimistic | Data integrity critical |
| Export request (Tuấn) | Optimistic → show job_id | Async anyway |

**Accessibility Requirements (bắt buộc — không defer):**
- ARIA live regions cho streaming content: `aria-live="polite"` trên `<StreamingMessage />`
- Keyboard navigation cho `<StreamAbortButton />`: `Escape` key binding
- Focus management khi approval modal opens/closes
- Screen reader support: streaming progress announcements

**i18n Foundation:**
- Library: `react-i18next` — setup ngay Sprint 1, chỉ Vietnamese locale
- Không hardcode Vietnamese strings trong components — tất cả qua i18n keys
- Cho phép expand sang English (Phase 3+) không cần refactor

---

### Infrastructure & Deployment

**Kubernetes Namespace Strategy: Per-Environment**
```
aial-dev/      ← Dev team: full access
aial-staging/  ← Dev team: read-only, CI/CD: write
aial-prod/     ← Zero human access; CI/CD pipeline only
```

**K8s Requirements (bắt buộc trước staging deploy):**

```yaml
# ResourceQuota per namespace (example: aial-dev)
apiVersion: v1
kind: ResourceQuota
spec:
  hard:
    memory: "16Gi"
    cpu: "8"
    pods: "50"
    requests.memory: "12Gi"
    limits.memory: "16Gi"
---
# NetworkPolicy — zero-trust giữa namespaces
# aial-dev không được talk sang aial-prod
kind: NetworkPolicy
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  # Chỉ allow: intra-namespace + Kong gateway
```

**K8s RBAC:**
- Dev team: `admin` ClusterRole trong `aial-dev`, `view` trong `aial-staging`, zero trong `aial-prod`
- CI/CD service account: `deploy` custom role với limited permissions per namespace

**HashiCorp Vault Path Structure:**
```
secret/aial-dev/oracle/credentials
secret/aial-dev/llm/anthropic-key
secret/aial-staging/...
secret/aial-prod/...
```
K8s ServiceAccount per namespace chỉ có Vault policy cho đúng path đó. External Secrets Operator với namespace-scoped SecretStore.

**LLM Provider Swap (Phase 1 → Phase 2):**
- Phase 1: `LITELLM_MODEL=claude-sonnet-4-6` (Anthropic API)
- Phase 2: `LITELLM_MODEL=ollama/llama3` (self-hosted) hoặc `LITELLM_MODEL=ollama/qwen2.5`
- Zero code changes — chỉ thay env var + Vault secret update

---

### Decision Impact Analysis

**Implementation Sequence (phải làm theo thứ tự này):**

1. **Governance:** ADR-001 sign-off từ Lan/Compliance Officer
2. **Infrastructure:** K8s namespaces + ResourceQuota + NetworkPolicy + Vault setup
3. **Security foundation:** Keycloak + Cerbos + Oracle VPD (với context reset integration test)
4. **Walking Skeleton:** Single end-to-end request: Kong → FastAPI → Cerbos → Oracle → Claude → Response
5. **Embedding benchmark:** 50-100 queries với actual data → confirm bge-m3 accuracy > 85%
6. **Frontend foundation:** Error Boundary hierarchy + useSSEStream hook + i18n setup
7. **Core features per phase:** Theo Phase 1/2/3 scope

**Cross-Component Dependencies:**
- Cerbos policies → phải exist trước Oracle Connector (connector cần policy decision)
- Embedding model lock (ADR-003) → phải confirm trước Weaviate collection creation
- useSSEStream hook → phải exist trước bất kỳ streaming component nào
- Error Boundary hierarchy → phải exist trước streaming components
- Data timestamp UI → phải design cùng lúc với query result components

---

## Project Context Analysis

> **Nguồn:** PRD v2.1 + Research Report + Expert Panel Review (Dr. Khánh — Security Architect & Anh Tuấn — Platform Engineer)

### Requirements Overview

**Functional Requirements — 37 FRs / 8 Modules:**

| Module | FRs | Trọng tâm kiến trúc |
|--------|-----|---------------------|
| Agent Orchestration | O1–O5 | Intent routing, multi-turn security, privilege escalation prevention |
| Text-to-SQL & Semantic Layer | S1–S6 | Semantic abstraction bắt buộc, SQL whitelist/AST, query governor, cross-domain decomposition |
| RAG & Document Management | R1–R5 | Policy-first retrieval, ingestion pipeline, classification-aware chunking, citation attribution |
| Security & Access Control | A1–A8 | 6-layer security stack, LDAP/SSO, RBAC+ABAC, Oracle VPD, column-level, PII masking, approval workflow, audit |
| Session Memory & Conversation | M1–M7 | 3-tier memory hierarchy, isolation boundaries, selective injection, no raw data |
| Forecasting & Advanced Analytics | F1–F6 | Async-first bắt buộc, time-series engine, anomaly detection, drill-down theo phân quyền |
| Export & Reporting | E1–E4 | Async job model, export authorization, audit trail đầy đủ |
| Administration | AD1–AD5 | Semantic Layer mgmt, RBAC admin, data source config, audit & health dashboards |

**Non-Functional Requirements — Quyết định kiến trúc:**

| NFR | Implication kiến trúc |
|-----|----------------------|
| P50 < 3s (SQL), P50 < 5s (Hybrid) | Semantic result cache + metadata cache + Oracle read-optimized layer bắt buộc |
| 100 concurrent users (P1) → 500 (P3) | Stateless API/Orchestration nodes; horizontal scale-out |
| 99.5% uptime; RTO < 4h; RPO < 1h | Multi-instance orchestration; PostgreSQL WAL streaming; Redis AOF; Weaviate backup automation |
| AES-256 at rest; TLS 1.3 in transit | Encryption tại mọi persistence layer; LangGraph agent state phải encrypt + HMAC |
| PDPA compliance | PII detection middleware; log sanitizer; memory isolation; data lineage tracking |
| Modular LLM switching via config | LLM Provider Interface/Adapter + Prompt Template Registry bắt buộc |
| 80% test coverage | Dependency injection, interface-based design; automated policy testing framework |

**Scale & Complexity:**
- Complexity level: **Enterprise (High)**
- Primary domain: AI/ML Platform + Enterprise Data Layer + Security Infrastructure
- Estimated architectural components: **15+ discrete services/layers**
- Regulatory: PDPA (Vietnam)
- Multi-tenancy model: Department-level isolation

---

### Technical Constraints & Dependencies

| Constraint | Approach |
|-----------|---------|
| **Oracle version-agnostic** | **Capability-based Adapter pattern** — probe database features at connect-time (FETCH_FIRST, NATIVE_JSON, VECTOR_TYPE, APPROX_COUNT_DISTINCT...), cache vào Redis. SQL generation layer query capability registry, không hardcode version. Officially support Oracle 19c+; 12c best-effort với documented limitations (12c EOL 2022). |
| **LDAP/AD topology flexible** | Keycloak làm universal IdP abstraction — support AD on-premise, Azure AD / Entra ID, OpenLDAP qua LDAP v3 / OIDC / SAML 2.0 |
| **LLM Provider modular** | LiteLLM làm adapter layer + custom LLMProvider interface. Cần: `generate()`, `stream()`, `embed()`, `count_tokens()`, `get_capabilities()`, `get_cost_estimate()`. **Prompt Template Registry** tách biệt với provider swap — Claude và local LLM cần prompt format khác nhau cho cùng task. |
| **Embedding dimension** | Embedding model phải versioned từ ngày đầu. Swap provider có thể đòi rebuild toàn bộ Weaviate index — cần migration plan trước khi swap. |
| **Deployment: self-hosted sensitive components** | Weaviate, Keycloak, PostgreSQL, Redis tự host. LLM cloud call chỉ Phase 1 (optional Phase 2+). |
| **Data residency** | Dữ liệu Oracle không rời hạ tầng nội bộ; LLM prompts không chứa raw data values |

---

### Cross-Cutting Concerns (Enhanced)

> **10 concerns** — 8 ban đầu + 2 bổ sung từ expert review:

| # | Concern | Phạm vi | Ghi chú quan trọng |
|---|---------|---------|-------------------|
| 1 | **Authorization/ABAC** | MỌI layer | Enforce tại: API Gateway, Orchestrator, Policy Engine, Connector, DB, Vector Store |
| 2 | **Audit Logging** | MỌI interaction | Immutable, append-only. **Bắt buộc async write path + dead-letter queue** — sync write = latency bottleneck; queue đầy = undefined behavior |
| 3 | **PII Detection & Masking** | Input + Output + Memory + Logs | Pipeline tại: input sanitization, query results, memory writes, log writes |
| 4 | **Rate Limiting** | Mọi entry point | 3 levels: system-wide (Kong), per-user (100 queries/day), per-department. **Phải account cho business peak events** (month-end close, quarter-end) |
| 5 | **Observability & Tracing** | End-to-end | trace_id xuyên suốt từ UI → Orchestrator → Policy → DB → Response |
| 6 | **LLM Abstraction** | Mọi AI call | LiteLLM adapter + capability negotiation + normalized error taxonomy + prompt template registry. **Semantic caching** dựa trên query similarity (không chỉ exact match) |
| 7 | **Circuit Breaking & Fallback** | Oracle, LLM, Vector Store, Cube.dev | **Failure Mode Matrix bắt buộc:** mỗi component fail → behavior rõ ràng (degrade/queue/reject/serve-stale). Graceful Degradation Hierarchy phải document trước code |
| 8 | **Async Job Model** | Export, Forecasting, Scheduled Reports | Tách khỏi chat execution path; job queue (Celery + Redis); dead-letter queue + alert threshold |
| 9 | **Data Lineage & Provenance Tracking** | Mọi response | PDPA requirement — ghi đủ: SQL query nào, document chunk nào, schema nào contribute vào response |
| 10 | **Schema Drift Detection & Invalidation** | Semantic Layer + Cache | Oracle schema thay đổi → trigger invalidation Cube.dev + cached SQL templates. **Cần define ownership: ai responsible trigger re-indexing?** |
| 11 | **Data Consistency Model** | PostgreSQL ↔ Redis ↔ Weaviate ↔ Cube.dev | **Consistency Contract per-domain bắt buộc:** explicit decision "domain X chấp nhận staleness tối đa Y phút". Chưa có → component build với assumptions khác nhau |
| 12 | **Multi-tenancy Isolation Model** | Infrastructure layer | Shared schema + RLS hay separate schema per department? Quyết định này ảnh hưởng Weaviate collection design, PostgreSQL RLS policy, Cube.dev data source config. **Phải lock trước implementation** |
| 13 | **Local Development Strategy** | Developer experience | Stack 7 services: docker-compose.dev.yml với lightweight stubs. Keycloak realm-export.json committed vào repo. Nixtla ForecastingAdapter với MockNixtlaClient cho CI. Thiếu → developer mới mất 45+ phút setup |
| 14 | **Automated Policy Testing** | Cerbos policies | `cerbos compile ./policies` phải chạy trong CI. `tests/cerbos/` với yaml fixtures bắt buộc — policy conflict chỉ phát hiện ở production nếu thiếu |

**Concerns cần strengthen thêm:**
- **Data Freshness Signaling:** Mọi response cần metadata "data freshness timestamp"
- **Prompt Injection Pipeline (layer riêng):** Dedicated input sanitization trước LangGraph
- **Pydantic v1/v2 Compatibility:** `langchain-core` + `litellm` dùng pydantic v1; FastAPI 0.100+ dùng pydantic v2 → conflict block toàn bộ model serialization. Cần `requirements/constraints.txt` + compatibility layer ngay Sprint 1
- **LangGraph Testability:** Cần `StateInjector` interface để inject mock state vào graph node — không có → test coverage stuck ~30%
- **Embedding Model Lock:** Embedding model, version, dimension phải pinned trước production indexing — swap sau = rebuild toàn bộ Weaviate index

---

### Architectural Risks Identified

> Tổng hợp từ expert panel — phân loại theo priority:

**🔴 P0 — Phải address trước go-live:**

| Risk | Mô tả | Mitigation |
|------|-------|-----------|
| **Cache TOCTOU** | Permission revoke sau khi response đã cached → user vẫn nhận data trong TTL window | Permission change event phải trigger cache invalidation, không chỉ rely TTL |
| **LangGraph state attack surface** | Agent state serialize vào Redis/PostgreSQL mà không encrypt → injection vector | Encrypt state at-rest + HMAC integrity check cho mọi state write/read |
| **Weaviate network exposure** | Weaviate không có enterprise-grade RBAC — nếu chỉ rely application-level, mọi internal service có thể query toàn bộ vector store | Network-level isolation: Weaviate chỉ accept connection từ specific service accounts ở infra layer |
| **Keycloak↔Cerbos policy drift** | 2 systems quản lý policy → drift theo thời gian là không tránh khỏi | Design single source of truth; clear protocol "who owns what"; automated sync verification |
| **Oracle Adapter silent failure** | Capability probe fail silently hoặc return incorrect capability set → toàn bộ Oracle integration behave incorrectly không có error | Circuit breaker + health check riêng cho capability probe; loud failure bắt buộc |
| **Oracle license cost** | Connection per-session/per-core licensing surprise có thể block deployment hoàn toàn | Procurement/legal sign-off **trước khi commit vào Oracle-specific features**; UCP design từ đầu |
| **Pydantic v1/v2 conflict** | `langchain-core` + `litellm` → pydantic v1; FastAPI 0.100+ → pydantic v2 → block toàn bộ model serialization | `requirements/constraints.txt`; compatibility layer; resolve trước Sprint 1 |
| **Change Management** | Enterprise users (Finance, HR) resist AI "black box" → adoption failure dù system technically sound | Change management plan; transparency features (show SQL + sources); gradual rollout per department |

**🟠 P1 — Sprint đầu tiên:**

| Risk | Mô tả | Mitigation |
|------|-------|-----------|
| **LangGraph state recovery** | Partial execution khi interrupt → corrupt state; `RedisSaver` không support optimistic locking out-of-the-box → cần custom WATCH/MULTI/EXEC (~2 sprints) | Explicit checkpoint strategy + idempotent node design từ đầu |
| **Embedding dimension mismatch** | Swap embedding model sau production indexing = rebuild toàn bộ Weaviate index | Lock embedding model version + dimension trước production indexing; migration strategy required |
| **Weaviate RPO** | Self-hosted backup/restore story kém; rebuild có thể mất "vài ngày" | Automated backup; `scripts/test-weaviate-restore.sh` chạy monthly trong CI; document rebuild SLA |
| **Data Ownership & RACI** | Khi AI tổng hợp cross-department data, ai là Data Owner? RACI matrix cho data governance chưa tồn tại | Data Stewardship Council per department trước go-live; RACI matrix approved bởi leadership |
| **Dynamic Access Reality** | Cerbos RBAC thuần túy quá rigid cho project-based access (3 tháng), emergency access, matrix org | Temporal/delegated permission workflow design; time-bounded access grants |

**🟡 P2 — Backlog ưu tiên cao:**

| Risk | Mô tả | Mitigation |
|------|-------|-----------|
| **RAG chunk boundary leakage** | Chunk span confidential + public content nếu chunking không respect data classification | Classification-aware chunking strategy |
| **Cube.dev query compilation blind spot** | Cube.dev compile SQL có thể bypass ABAC check nếu misconfigured | Audit log SQL *sau* Cube.dev compilation |
| **Cube.dev cold start** | Container restart → first queries slow → support tickets | Pre-warming strategy + health check distinguish "cold" vs "unhealthy" |
| **Forecast model ownership** | Nixtla forecast khác với Finance's traditional model → who is right? | Model governance: version control cho business models; approval workflow khi thay đổi parameters |
| **Team size vs stack complexity** | Stack 14+ components cần ≥8 engineers để vận hành an toàn | Phased rollout; core Text-to-SQL + basic ABAC trước |

---

### Architectural Recommendations (Pre-Design)

> Những quyết định và actions phải hoàn thành **trước khi bắt đầu detailed component design:**

**1. Lock 5 Architecture Decision Records (ADRs):**

| ADR | Decision cần lock |
|-----|------------------|
| ADR-001 | Multi-tenancy model: shared schema + RLS hay separate schema per department? |
| ADR-002 | Consistency contract: per-domain staleness tolerance (ví dụ: Sales data ≤ 5 phút, Financial data ≤ 1 giờ) |
| ADR-003 | Embedding model lock: model name, version, dimension — không thay đổi sau production indexing |
| ADR-004 | Async job retry policy: max retries, backoff strategy, dead letter queue destination |
| ADR-005 | Local dev strategy: docker-compose stubs hay full service stack? |

**2. Build Walking Skeleton trước mọi component design:**

End-to-end vertical slice: `Kong → FastAPI → LangGraph → Cerbos → Weaviate/Oracle → LiteLLM → Response`. Không cần feature hoàn chỉnh — chỉ cần prove integration stack works *together*. Đây là nơi integration issues (đặc biệt LangGraph ↔ LiteLLM ↔ Cerbos) sẽ được phát hiện sớm.

**3. Data Flow Diagrams cho 3 critical paths (trước API design):**
- Query path: user question → answer
- Ingestion path: new document/data → indexed + available
- Policy enforcement path: request → ABAC check → filtered response

**4. Quantify "Enterprise Scale" với concrete numbers:**

Cần định nghĩa rõ: concurrent users, queries/minute peak, documents in Weaviate, Oracle schemas/tables in scope, departments. Những con số này drive: Cube.dev caching TTL, Redis eviction policy, LangGraph parallelism, Kong rate limit thresholds.

**5. Business Architecture Workshop (song song với technical design):**

Output cần có trước go-live:
- Business Value Scorecard (Time saved/user/week, query accuracy, adoption rate by department)
- Business Glossary v1.0 — owned bởi business stakeholders, integrated với LlamaIndex indexing
- Stakeholder Concern Register — concerns và success criteria riêng của từng nhóm user
- Data Governance RACI Matrix
- Human-in-the-loop workflow tiered: low-stakes (AI answers directly) vs high-stakes (AI proposes + human approves)

**6. Sprint 1 Infrastructure Structure (Amelia's recommendation):**

```
infra/
  docker-compose.dev.yml          # 7 services + health checks
  keycloak/realm-export.json      # committed, reproducible setup
  cerbos/policies/tests/          # yaml test fixtures

src/adapters/
  llm/litellm_adapter.py          # LLMProvider interface + MockLLMClient
  forecasting/nixtla_adapter.py   # ForecastingAdapter + MockNixtlaClient
  vector/weaviate_adapter.py      # VectorStore interface + FakeVectorStore
  oracle/capability_detector.py   # CapabilityRegistry + integration test

src/graph/testing.py              # StateInjector interface cho LangGraph testability

requirements/
  base.txt / pydantic-v1.txt / pydantic-v2.txt / constraints.txt
```

CI pipeline gates: Unit (pytest 80%), Contract (Schemathesis), Policy (`cerbos compile`), Integration (testcontainers-python), E2E (P0 flows only), Weaviate restore (monthly).
