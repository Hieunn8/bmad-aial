---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-04-28'
totalEpics: 9
totalStories: 53
frCoverage: '46/46'
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
project_name: 'Enterprise AI Data Assistant (AIAL)'
date: '2026-04-27'
---

# Enterprise AI Data Assistant (AIAL) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for AIAL, decomposing the requirements from the PRD v2.1, UX Design Specification, and Architecture into implementable stories organized by user value.

---

## Requirements Inventory

### Functional Requirements (46 FRs)

**Module 1 — Agent Orchestration:**
- FR-O1: Intent Classification → sql/rag/hybrid/forecast/fallback; accuracy >95% trên test set 200 câu; fallback khi confidence < threshold
- FR-O2: Multi-turn Context → câu hỏi follow-up được hiểu đúng ngữ cảnh trong cùng session
- FR-O3: Contextual Security Guardrails → session memory giới hạn user_id + department_id; không inject context user khác
- FR-O4: Multi-turn Privilege Escalation Prevention → policy check độc lập mỗi turn; không tích lũy quyền
- FR-O5: Natural Language SQL Explanation → mọi câu trả lời SQL có thể expand xem SQL + logic giải thích

**Module 2 — Text-to-SQL & Semantic Layer:**
- FR-S1: Semantic Layer mandatory → LLM không thấy raw Oracle schema; chỉ thấy metric/dimension definitions
- FR-S2: Metadata Catalog & Business Glossary → catalog ánh xạ business terms → metric definition → technical columns
- FR-S3: SQL Whitelist & AST Validation → SELECT only; block DROP/INSERT/UPDATE/DDL/subquery vòng lặp/Cartesian joins
- FR-S4: Query Governor → max 50,000 rows; timeout 30s; cấm full table scan trên bảng >1M rows không có partition predicate
- FR-S5: Cross-domain Query Decomposition → multi-domain tách thành nhiều single-domain queries; merge tại application layer
- FR-S6: Query Result Cache → cache hit rate >40% cho câu hỏi phổ biến sau 2 tuần vận hành

**Module 3 — RAG & Document Management:**
- FR-R1: Document Ingestion Pipeline → PDF/DOCX/XLSX/TXT; upload xong <5 phút cho file <100 trang
- FR-R2: Pre-retrieval Policy Filtering → filter đúng department/classification TRƯỚC khi vector search
- FR-R3: Citation & Source Attribution → tên tài liệu, trang, đoạn cụ thể cho mọi câu trả lời RAG
- FR-R4: Document Access Control → mỗi document gán department/classification/effective_date/source_trust; không bỏ qua metadata tagging
- FR-R5: Admin Upload & Management → CRUD + audit log qua Admin Portal

**Module 4 — Security & Access Control (CRITICAL):**
- FR-A1: LDAP/AD Integration → SSO qua Keycloak + LDAP; JWT hợp lệ <1s
- FR-A2: RBAC + ABAC Policy Engine → enforce đúng role + attributes (department, region, clearance)
- FR-A3: Row-level Security (Oracle VPD) → LLM không thể bypass RLS dù SQL bị inject
- FR-A4: Column-level Security → cột nhạy cảm trả về `***` hoặc bị loại bỏ
- FR-A5: Data Masking & PII Redaction → Presidio scan kết quả trước khi trả về; CMND/họ tên/email không xuất hiện raw
- FR-A6: Identity Passthrough → Oracle query mang identity user thực; không dùng shared DBA account
- FR-A7: Query Approval Workflow → sensitivity_tier >= 2 cần approval; SLA approve <4h; workflow: submit → notify → approve/reject → execute/cancel
- FR-A8: Comprehensive Audit Log → 100% requests; immutable (append-only); retention ≥12 tháng; ghi đủ who/what/when/intent/SQL/sources/result/policy

**Module 5 — Session Memory & Conversation History:**
- FR-M1: Short-term Memory → Redis TTL 24h; câu hỏi follow-up "nó/cái đó" resolve đúng trong cùng session
- FR-M2: Medium-term Memory → 30 sessions PostgreSQL summaries; không lưu raw Oracle data
- FR-M3: Long-term Preference → top 3 KPI/báo cáo dùng nhiều nhất trong 30 ngày qua hiển thị khi mở session mới
- FR-M4: Memory Isolation → không shared memory path giữa users khác nhau
- FR-M5: Selective Context Injection → token usage tăng <20% sau 10 turns nhờ memory compaction
- FR-M6: Conversation History Search → search <2s theo keyword/time range/topic
- FR-M7: Memory không lưu raw dữ liệu → chỉ lưu business intent, không lưu giá trị số từ Oracle

**Module 6 — Forecasting & Advanced Analytics:**
- FR-F1: Time-series Forecasting → kết quả kèm confidence interval; MAPE <15% trên validation set
- FR-F2: Anomaly Detection → alert <1 giờ sau khi data cập nhật; false positive rate <10%
- FR-F3: Trend Analysis (YoY/MoM/QoQ) → giải thích không chứa thuật ngữ ML; validatable qua user acceptance test
- FR-F4: Drill-down Analytics → theo phòng ban/sản phẩm/khu vực/kênh bán; đúng theo phân quyền
- FR-F5: Result Explainability → top 3 yếu tố đóng góp; confidence bằng ngôn ngữ thông thường
- FR-F6: Async Forecast Jobs → trả job_id ngay; notify khi xong; không block chat UI

**Module 7 — Export & Reporting:**
- FR-E1: Export → Excel/PDF/CSV; không có dữ liệu ngoài phạm vi quyền trong file
- FR-E2: Scheduled Reports → daily/weekly/monthly; audit log mỗi lần gửi; xác nhận người nhận
- FR-E3: Export Authorization → sensitivity >= tier 2 cần approval gate; không thể bypass
- FR-E4: Export Audit → 100% export events có audit entry

**Module 8 — Administration:**
- FR-AD1: Semantic Layer Management → diff view giữa versions; rollback 1 click
- FR-AD2: User & Role Management → CRUD user/role với audit; sync với LDAP
- FR-AD3: Data Source Configuration → cấu hình Oracle connections/schema allowlist/timeout/row limits; không expose credentials
- FR-AD4: Audit Dashboard → search/filter log <3s; by user/time/action/data source/policy decision
- FR-AD5: System Health Dashboard → metrics cập nhật mỗi 30s; alert <2 phút sau khi threshold vi phạm

---

### Non-Functional Requirements

- NFR-P1: Performance — Intent classification P50<300ms/P95<700ms; Single SQL P50<3s/P95<8s; Hybrid P50<5s/P95<12s; Cross-domain P50<8s/P95<20s; Forecast P50<10s/P95<30s; Export async <5 phút
- NFR-P2: Concurrency — 100 concurrent users Phase 1; 500 users Phase 3
- NFR-S1: Encryption at rest — AES-256 cho PostgreSQL/Redis/Vector Store
- NFR-S2: Encryption in transit — TLS 1.3 bắt buộc; không accept TLS 1.2
- NFR-S3: Secret management — HashiCorp Vault hoặc Kubernetes Secrets; không hardcode
- NFR-S4: Session token — JWT expiry 8h; refresh token rotation
- NFR-S5: PDPA compliance — không lưu PII thô trong memory/log
- NFR-HA1: Uptime SLA — 99.5% (Production)
- NFR-HA2: RTO <4 giờ; RPO <1 giờ
- NFR-HA3: Backup — PostgreSQL WAL streaming; Redis AOF; Weaviate daily backup
- NFR-SC1: Horizontal scaling — Orchestration + API nodes scale-out stateless
- NFR-SC2: Workload isolation — 5 pools: chat-low-latency/sql-heavy/rag-ingestion/forecast-batch/export-jobs
- NFR-OB1: Distributed tracing — end-to-end trace mọi request (OpenTelemetry)
- NFR-OB2: LLM Observability — token usage/latency per model/hallucination signals (Langfuse)
- NFR-OB3: Alerting — P95 > SLO; cache hit <20%; error rate >1%; timeout >2%
- NFR-CM1: Token cost monitoring — per query/user/department
- NFR-CM2: Rate limiting — 100 queries/day per-user; configurable per-department
- NFR-MT1: Modular LLM — swap OpenAI ↔ Local LLM chỉ qua config
- NFR-MT2: Test coverage — >80% unit test; regression tests cho policy/SQL/RAG leakage
- NFR-AI: 14 AI Safety threat vectors (Prompt Injection, SQL Injection via LLM, Jailbreak, Data Exfiltration, Multi-turn Privilege Escalation, Tool Abuse, Hallucination, Schema Poisoning, Cross-dept Leakage, Heavy Query Abuse, PII Exposure, Wrong Export Recipient, Sensitive Data in Logs, Combined Source Inference)

---

### Additional Requirements (Architecture)

**Project Setup:**
- ARCH-1: Custom Monorepo scaffold — uv workspace root, pyproject.toml per service, docker-compose.dev.yml với 7 services, Makefile (install/dev/test/lint), pre-commit, .python-version (3.12)
- ARCH-2: Turborepo frontend — packages/ui (shared shadcn/ui), packages/types (shared TS + queryKeys factory)
- ARCH-3: Keycloak realm-export.json committed vào repo (reproducible setup)
- ARCH-4: Cerbos policies + tests/ directory (yaml test fixtures)

**Infrastructure (Walking Skeleton order):**
- ARCH-5: Infra backbone trước mọi service code — Kong + Keycloak + Cerbos + Weaviate + Redis + PostgreSQL (docker-compose)
- ARCH-6: Observability stack TRƯỚC service code — otel-collector + Tempo + Grafana
- ARCH-7: Weaviate schema initialization (`init-weaviate-schema.py`) trước khi RAG service chạy
- ARCH-8: `wait-for-services.sh` để tránh race conditions

**Critical Technical Constraints:**
- ARCH-9: Pydantic v1/v2 conflict resolution — Sprint 1 blocker; `requirements/constraints.txt`
- ARCH-10: AIALGraphState TypedDict shared contract — tất cả LangGraph nodes dùng cùng state schema
- ARCH-11: Celery `acks_late=True` + `reject_on_worker_lost=True` — bắt buộc cho mọi task
- ARCH-12: Embedding model lock — `bge-m3` (1024 dims) từ Phase 1; dimension abstract qua config; `model_version` field trong Weaviate schema
- ARCH-13: Oracle VPD context reset — integration test bắt buộc trước staging deploy
- ARCH-14: K8s ResourceQuota + NetworkPolicy zero-trust + RBAC per namespace

**API Contracts:**
- ARCH-15: REST endpoints: `POST /v1/chat/query`, `GET /v1/chat/stream/{id}`, `POST /v1/sql/preview`, `POST /v1/reports/export`, `POST /v1/forecast/run`
- ARCH-16: SSE event format: `{ type: "thinking|querying|streaming|done|error", ... }` per step
- ARCH-17: RFC 9457 Problem Details error format (Phase 2); simple envelope Phase 1

**Shared Package (`aial-shared`):**
- ARCH-18: `shared/aial_shared/` với: models/ (Pydantic DTOs), auth/keycloak.py, clients/ (Redis/Weaviate/Oracle singletons), telemetry/tracer.py, constants/redis_keys.py, exceptions/base.py

---

### UX Design Requirements

**Design System & Tokens:**
- UX-DR1: Design tokens implementation — Deep Teal `#0F7B6C` primary; warm gray neutral system; 8-color data viz palette; CSS custom properties (HSL format) trong `packages/ui/src/styles/tokens.css`
- UX-DR2: Typography setup — `'Inter', 'Noto Sans', 'Noto Sans Vietnamese', sans-serif`; Admin scale (14px base) + Chat scale (15px base); load từ Google Fonts
- UX-DR3: shadcn/ui component setup — Radix UI primitives; Tailwind config sharing giữa apps; density modes (Comfortable/Compact) qua CSS vars
- UX-DR4: Recharts theming — `useChartTheme()` hook; CSS vars at runtime; `isAnimationActive={false}` khi streaming; batch 150ms

**Streaming Components (Phase 1 Critical):**
- UX-DR5: `StreamingMessage` component — 7 states: idle/thinking/streaming/buffering/complete/copy_success/error; ARIA `role="log"` `aria-live="polite"`; thinking pulse 3 micro-phases; Progress Narration "Bước 2/4: Đang truy vấn..."
- UX-DR6: `ProgressiveDataTable` component — streaming rows với locked headers; batch 150ms; `isAnimationActive={false}`; scroll position preserved
- UX-DR7: `StreamAbortButton` — visible, không ẩn trong menu; Escape key binding
- UX-DR8: `ConnectionStatusBanner` — SSE drop detection; auto-retry với exponential backoff
- UX-DR9: `ChartReveal` — fade-in khi JSON stream complete; skeleton placeholder trước đó
- UX-DR9a: Loading skeleton pattern — global skeleton language for chat/table/chart loading states; define in Epic 1 before DR5/DR6 consumers
- UX-DR9b: Animation tokens — duration/easing curves for streaming transitions; define with DR1-4 in Epic 1 and reuse across DR5/DR9
- UX-DR9c: SSE error scenario validation — verify DR18/19/20/21 cover timeout, partial stream, reconnect, and server-abort behavior before Epic 2A implementation

**Trust & Transparency Components:**
- UX-DR10: `CitationBadge` — inline `[1][2]` parse từ streaming text; shadcn Tooltip; human-readable source (không raw SQL); build in Epic 2B, consume in Epic 3
- UX-DR11: `ProvenanceDrawer` — side panel; không navigate away; human-readable lineage + timestamp + confidence; SQL collapse by default; build in Epic 2B, consume in Epic 3
- UX-DR12: `ConfidenceBreakdownCard` — 5 states: low-confidence/partial-data/stale-data/permission-limited/cross-source-conflict; luôn offer 3 exits; build in Epic 4, consume in Epic 7

**Approval & Async Components:**
- UX-DR13: `ApprovalBriefingCard` — 5 elements: requester + business justification + data scope + risk signal + escalation; non-modal; keyboard accessible
- UX-DR14: `ExportJobStatus` — 4 states: queued/running/ready/failed; SSE job updates; non-blocking; toast notification khi done
- UX-DR15: `ExportConfirmationBar` — sticky bottom; không modal; auto-dismiss 30s; Human-in-the-Loop Signature; build in Epic 4, consume in Epic 6

**Error & Permission Components:**
- UX-DR16: `IntentConfirmationDialog` — state machine: idle → intent_ambiguous → confirmed; SSE event `{ type: 'intent_ambiguous', options: [...] }`; Vietnamese business terminology
- UX-DR17: `PermissionRequestState` — 5 states; không dead-end; luôn offer alternatives
- UX-DR18: Error boundary hierarchy — `AppErrorBoundary > PageErrorBoundary > StreamErrorBoundary`; mandatory trước streaming components

**State Management:**
- UX-DR19: TanStack Query key factory — `queryKeys` object; `[entity, id?, filters?]` array format; KHÔNG dùng string keys
- UX-DR20: Zustand stream state slice — `{ chunks[], streamStatus, abortController, queryId }`; commit to TanStack Query cache khi done via `queryClient.setQueryData()`
- UX-DR21: `useSSEStream` custom hook — SINGLE SOURCE OF TRUTH; JWT injection; reconnect với exponential backoff; cleanup on unmount

**Navigation & Routing:**
- UX-DR22: TanStack Router — file-based routes; `.lazy.tsx` suffix bắt buộc (non-critical routes); route convention document; `beforeLoad` guards cho permission-based visibility
- UX-DR23: Command Palette — `cmdk` library; `isPaletteOpen` Zustand; template queries + history

**Accessibility:**
- UX-DR24: WCAG 2.2 AA base compliance — Epic 1 owns ARIA landmark structure, contrast validation in design tokens, and `prefers-reduced-motion` baseline; axe-core accessibility audit is AC for every UI epic
- UX-DR25: Screen reader announcement strategy — Epic 2A owns streaming-specific behavior for `StreamingMessage`; use `aria-live="polite"`, sentence-boundary batching, and phase-change announcements; reused by later streaming surfaces

**Onboarding:**
- UX-DR26a: Onboarding flow structure — Role Recognition (10s) → step progression → First Query Scaffold; Epic 2A owns flow structure, navigation logic, and success path without curated demo data
- UX-DR26b: Onboarding demo experience — Live Demo (45s curated demo data) + "try it now" flows; Epic 5A/5B owns curated demo data integration if included in later phase

**Admin Portal:**
- UX-DR27: Admin Portal layout — desktop-only; Command Layout với sidebar 240px; 56px header; 12-column grid
- UX-DR28: Semantic Layer Admin UI — diff view giữa KPI versions; rollback 1-click; changelog visible

---

### NFR Classification (3 Groups)

**Group A — Epic 1 Acceptance Criteria (architectural baselines):**
- NFR-P1: Performance SLOs (P50/P95 per workload type) — must be validated in Epic 1 load test
- NFR-P2: Concurrency 100 users Phase 1 → verified via load test in Epic 1
- NFR-HA1/HA2/HA3: 99.5% uptime, RTO <4h, RPO <1h, backup strategy — infra decisions in Epic 1
- NFR-S1/S2/S3/S4: AES-256, TLS 1.3, Vault, JWT 8h — implemented in Epic 1

**Group B — Embedded per Feature (Acceptance Criteria of relevant stories):**
- NFR-S5 (PDPA): AC of every story touching memory/logs (Epics 2A, 5A, 5B)
- NFR-OB1/OB2/OB3: Distributed tracing + LLM observability + alerting — AC of each service story
- NFR-CM1/CM2: Token cost tracking + rate limiting — AC of Epic 2A/2B query stories
- NFR-MT2: Test coverage >80% — AC of every story in all epics
- NFR-AI: 14 AI Safety threats — distributed across Epics 2A, 2B, 4

**Group C — Dedicated Tech Validation (Epic 0 or Sprint 0):**
- NFR-SC1/SC2: Horizontal scaling + workload isolation — validated via load test Sprint before Phase 2
- NFR-MT1: Modular LLM swap validation — Epic 2B story (smoke test Local LLM switch)

---

### FR Coverage Map

| FR | Description | Epic | Phase |
|----|-------------|------|-------|
| FR-A1 | LDAP/AD Integration (SSO) | Epic 1 | 1 |
| FR-O1 | Intent Classification | Epic 2A | 1 |
| FR-O2 | Multi-turn Context | Epic 2A | 1 |
| FR-O3 | Contextual Security Guardrails | Epic 2A | 1 |
| FR-O4 | Multi-turn Privilege Escalation Prevention | Epic 2A | 1 |
| FR-O5 | Natural Language SQL Explanation | Epic 2B | 1 |
| FR-S1 | Semantic Layer mandatory | Epic 2A | 1 |
| FR-S2 | Metadata Catalog (bootstrap) / Management UI | Epic 2A (API) + Epic 5B (UI) | 1/2 |
| FR-S3 | SQL Whitelist & AST Validation | Epic 2A | 1 |
| FR-S4 | Query Governor | Epic 2A | 1 |
| FR-S5 | Cross-domain Query Decomposition | Epic 6 | 2 |
| FR-S6 | Query Result Cache | Epic 6 | 2 |
| FR-R1 | Document Ingestion Pipeline | Epic 3 | 2 |
| FR-R2 | Pre-retrieval Policy Filtering | Epic 3 | 2 |
| FR-R3 | Citation & Source Attribution | Epic 3 | 2 |
| FR-R4 | Document Access Control | Epic 3 | 2 |
| FR-R5 | Admin Upload & Management | Epic 3 | 2 |
| FR-A2 | RBAC + ABAC (baseline) / full ABAC attrs | Epic 2A (baseline) + Epic 4 (full) | 1/2 |
| FR-A3 | Oracle VPD Row-level Security | Epic 1 (infra/ARCH-13) + Epic 2A (enforce) | 1 |
| FR-A4 | Column-level Security | Epic 4 | 2 |
| FR-A5 | Data Masking & PII Redaction | Epic 4 | 2 |
| FR-A6 | Identity Passthrough | Epic 2A | 1 |
| FR-A7 | Query Approval Workflow | Epic 4 | 2 |
| FR-A8 | Comprehensive Audit Log | Epic 2B | 1 |
| FR-M1 | Short-term Memory (Redis) | Epic 2A | 1 |
| FR-M2 | Medium-term Memory (PostgreSQL summaries) | Epic 5B | 2 |
| FR-M3 | Long-term Preference | Epic 5B | 2 |
| FR-M4 | Memory Isolation | Epic 5B | 2 |
| FR-M5 | Selective Context Injection | Epic 5B | 2 |
| FR-M6 | Conversation History Search | Epic 5B | 2 |
| FR-M7 | Memory không lưu raw data | Epic 5B | 2 |
| FR-F1 | Time-series Forecasting | Epic 7 | 3 |
| FR-F2 | Anomaly Detection | Epic 7 | 3 |
| FR-F3 | Trend Analysis | Epic 7 | 3 |
| FR-F4 | Drill-down Analytics | Epic 7 | 3 |
| FR-F5 | Result Explainability | Epic 7 | 3 |
| FR-F6 | Async Forecast Jobs | Epic 7 | 3 |
| FR-E1 | Export (Excel/PDF/CSV) | Epic 6 | 2 |
| FR-E2 | Scheduled Reports | Epic 6 | 2 |
| FR-E3 | Export Authorization | Epic 6 | 2 |
| FR-E4 | Export Audit | Epic 6 | 2 |
| FR-AD1 | Semantic Layer Management | Epic 5B | 2 |
| FR-AD2 | User & Role Management | Epic 5A | 1.5 |
| FR-AD3 | Data Source Configuration | Epic 5A | 1.5 |
| FR-AD4 | Audit Dashboard | Epic 5A | 1.5 |
| FR-AD5 | System Health Dashboard | Epic 5A | 1.5 |

---

## Epic List

### Epic 1 — Governed Infrastructure & Walking Skeleton

**User outcome:** Engineering team có thể chạy hệ thống end-to-end với E2E distributed traces observable; bất kỳ user nào có thể đăng nhập bằng SSO doanh nghiệp.

**Done When:** Story 1.10 (E2E trace) passes — authenticated request flows Kong → FastAPI → LangGraph stub → response với trace visible in Grafana Tempo; Oracle VPD smoke test passes (Story 1.9).

**Explicitly Out of Scope:** Actual LLM calls, real Oracle data queries, RAG retrieval, user-facing UI beyond SSO login page.

**FRs covered:** FR-A1 (LDAP/SSO), FR-A3 infrastructure (ARCH-13 Oracle VPD integration test)
**ARCH items:** ARCH-1–14 (monorepo, infra stack, Keycloak, Kong, Cerbos, observability, constraints)
**UX items:**
- UX-DR1–4 (design tokens, typography, shadcn/ui setup)
- UX-DR18–21 (error boundaries, state management, useSSEStream hook)
- Loading skeleton pattern (global: used by DR5/DR6 in Epic 2A)
- Animation tokens (duration, easing curves for streaming — used by DR5/DR9)
- SSE error scenario validation (verify DR18/19/20 cover timeout, partial stream, server abort)
- UX-DR24 base (ARIA landmark structure, contrast validation in design tokens)

**Walking Skeleton Stories:**
- 1.1: Monorepo scaffold (uv workspaces, pyproject.toml per service, Dockerfiles multi-stage)
- 1.1b: Secrets baseline — HashiCorp Vault dev mode in Compose; secret injection pattern for Kong admin token, Keycloak client secret, and Oracle credentials
- 1.2: Compose infra stack (PostgreSQL, Redis, Weaviate, Keycloak, Kong, Cerbos) + wait-for-services.sh
- 1.3: Keycloak realm + OIDC → Cerbos PDP connected; SSO login flow works; realm-export.json committed
- 1.4: Kong gateway: OIDC plugin → Keycloak, Cerbos PDP deployment/authorization sidecar, route table skeleton, rate limiting baseline
- 1.5: FastAPI app skeleton: health/readiness endpoints, OpenTelemetry instrumentation, shared embedding client scaffold (`services/embedding/client.py`)
- 1.6: LangGraph stub graph + AIALGraphState TypedDict (ARCH-10 draft); Weaviate schema bootstrap (`weaviate/schema.py` — single source of truth for Epic 2A + Epic 3)
- 1.7: Observability stack: Tempo + Grafana + Prometheus scrape configs; Langfuse self-hosted
- 1.8: Frontend shell: React 18 + Vite 6 + TanStack Router skeleton; design token CSS vars loaded; Error Boundary hierarchy (AppErrorBoundary → PageErrorBoundary → StreamErrorBoundary); `useSSEStream` hook stub; shadcn/ui base components
- 1.9: **Oracle VPD Smoke Test** — `CREATE CONTEXT` + `DBMS_RLS.ADD_POLICY`; 1 policy, 1 table, 1 user principal; row-level filter assertion passes; cx_Oracle pool authenticated correctly ← P0 SECURITY GATE
- 1.10: **E2E trace GATE** — curl → Kong (JWT validated) → FastAPI → Cerbos (policy check) → LangGraph stub → response; full trace visible in Grafana Tempo ← WALKING SKELETON COMPLETE

**Phase:** 1 (Sprint 0) | **Blocks:** All other epics | **NFR baseline:** NFR-P1 SLO targets documented; NFR-S1-S4 encryption standards implemented; NFR-HA1-3 backup strategy configured

---

### Epic 2A — Minimal Viable Query

**User outcome:** Sales/Finance users can ask a question in Vietnamese, receive Oracle data results with SQL explanation, filtered by their row-level permissions, with every query logged.

**Done When:** A logged-in business user can submit a Vietnamese query through the streaming UI, receive a governed Oracle answer under 3 seconds P50 for datasets under 1M rows, see stream-safe screen reader announcements, and have policy + audit traces recorded for the request.

**Explicitly Out of Scope:** Document retrieval, cross-domain decomposition execution, approval workflow for sensitive exports, forecast generation, curated onboarding demo data.

**FRs covered:** FR-O1, FR-O2, FR-O3, FR-O4 (orchestration), FR-S1, FR-S2 (bootstrap API only), FR-S3, FR-S4 (Text-to-SQL core), FR-A2 (RBAC baseline), FR-A3 (Oracle VPD enforce), FR-A6 (identity passthrough), FR-M1 (short-term memory Redis)

**ARCH items:** ARCH-10 (AIALGraphState finalized), ARCH-11 (Celery config), ARCH-12 (bge-m3 lock)
**UX items:**
- UX-DR5 (StreamingMessage with UX-DR25 live region behavior)
- UX-DR6 (ProgressiveDataTable)
- UX-DR7 (StreamAbortButton)
- UX-DR8 (ConnectionStatusBanner)
- UX-DR16 (IntentConfirmationDialog)
- UX-DR25 (screen reader announcement strategy for streaming)
- UX-DR26a (onboarding flow structure, navigation logic, step progression only)

**Story outline:**
- 2A.0: Weaviate schema bootstrap — own `weaviate/schema.py`; create bootstrap/migration path used by Epic 2A and Epic 3; no duplicate schema ownership
- 2A.1: Intent classification + query contract enforcement (`POST /v1/chat/query`) with input validation, UTF-8 handling, and query length limits
- 2A.2: Semantic layer bootstrap API + glossary lookup service for governed business terms
- 2A.3: SQL generation guardrails — whitelist/AST validation + query governor + row/timeout limits
- 2A.4: Oracle execution path with identity passthrough + VPD enforcement wired to authenticated principal
- 2A.5: Streaming chat UX + SSE transport (`StreamingMessage`, `ProgressiveDataTable`, abort/reconnect, accessibility behavior)
- 2A.6: Redis short-term memory isolation + per-turn privilege re-check
- 2A.7: Baseline Cerbos policy mapping — principal schema frozen for `department` and `clearance`; JWT mapping documented for later Epic 4 extension
- 2A.8: Audit/event logging for query lifecycle + query explanation payload
- 2A.9: Onboarding shell (DR26a) + first-query scaffold without demo data

**Required coordination notes:**
- Cerbos PDP must already be deployed in Story 1.4; Epic 2A consumes it and must not re-home PDP deployment.
- `principal.attr` schema is frozen in Epic 2A with `department` and `clearance` even if baseline authorization still relies mainly on roles.
- ADR required before parallel Epic 4 work starts: `Cerbos principal.attr schema frozen at Epic 2A Story 2A.7`.
- `services/embedding/client.py` contract from Epic 1.5 is the shared bge-m3 client consumed by Epic 2A and Epic 3.

**Component Interface Notes:**
- Frontend: `QueryComposer`, `StreamingMessage`, `ProgressiveDataTable`, `ConnectionStatusBanner`, `IntentConfirmationDialog`, `OnboardingFlowShell`
- Backend: Query API service, orchestration service, SQL validation service, Oracle execution adapter, audit logger
- Shared contracts: `ChatQueryRequest`, `ChatStreamEvent`, `QueryResultPayload`, `PrincipalContext`, `AIALGraphState`

**NFR thresholds:** NFR-P1 query response P50<3s/P95<8s for single-domain datasets under 1M rows; NFR-CM1/CM2 token cost + rate limiting recorded per request; NFR-MT2 regression tests cover policy/SQL leakage paths.

**Phase:** 1 (Sprint 1-2) | **Requires:** Epic 1 complete | **Parallel with:** Epic 3, Epic 5A

---

### Epic 2B — Trust & Audit Layer

**User outcome:** Every answer shows exactly where data came from with citations; every query is fully auditable by compliance officers; users understand AI confidence level.

**Done When:** Query answers render provenance and citation UI sourced from audited backend metadata, and compliance staff can trace a completed request end-to-end without asking engineering to reconstruct logs.

**Explicitly Out of Scope:** New citation/parsing component implementations in later epics, full ABAC expansion, document ingestion pipeline.

**FRs covered:** FR-O5 (SQL explanation full), FR-A8 (comprehensive audit log), FR-S2 (management integration)

**UX items:**
- UX-DR9 (ChartReveal)
- UX-DR10 (CitationBadge) — build here, later epics consume
- UX-DR11 (ProvenanceDrawer) — build here, later epics consume

**Component Interface Notes:**
- Frontend: `CitationBadge`, `ProvenanceDrawer`, `AuditTimeline`, `SqlExplanationPanel`
- Backend: provenance formatter, audit read model, query explanation serializer
- Shared contracts: `CitationRef`, `ProvenanceEntry`, `AuditLogRecord`, `SqlExplanation`

**NFR thresholds:** Audit lookup and provenance payload retrieval <3s for standard query history views; NFR-OB1/OB2/OB3 events emitted for every completed or failed answer.

**Phase:** 1 (Sprint 2-3) | **Requires:** Epic 2A complete

---

### Epic 3 — Document Intelligence & Hybrid Answers

**User outcome:** Users can ask questions that combine Oracle database data with internal documents; answers include citations from both data sources with source attribution.

**Done When:** Authorized documents can be ingested, filtered before retrieval by policy metadata, and surfaced in hybrid answers using the shared provenance UI built in Epic 2B.

**Explicitly Out of Scope:** Rebuilding Weaviate schema ownership, duplicating citation/provenance UI, cross-domain query decomposition across business domains.

**FRs covered:** FR-R1, FR-R2, FR-R3, FR-R4, FR-R5

**ARCH items:** ARCH-12 (bge-m3 embedding), Weaviate schema migrations
**UX items:**
- UX-DR10 (citation from documents) — consume implementation from Epic 2B
- UX-DR11 (ProvenanceDrawer for docs) — consume implementation from Epic 2B

**Required coordination notes:**
- Consume `weaviate/schema.py` from Story 2A.0 or Epic 1.6 baseline; Epic 3 must not fork schema ownership.
- Consume shared `services/embedding/client.py` scaffold from Epic 1.5/1.6 for bge-m3 access.

**Component Interface Notes:**
- Frontend: hybrid answer view, provenance drawer integration, document citation rendering
- Backend: ingestion worker, retrieval service, metadata policy filter, hybrid answer orchestrator
- Shared contracts: `DocumentChunk`, `DocumentCitation`, `HybridAnswerPayload`, `EmbeddingVectorRef`

**NFR thresholds:** File ingest <5 minutes for documents under 100 pages; retrieval responses meet FR-R3 citation completeness and enforce FR-R2 policy filtering before vector search.

**Phase:** 2 (Sprint 3-4) | **Requires:** Epic 1 | **Parallel with:** Epic 2A/2B

---

### Epic 4 — Protected Access for Sensitive Data

**User outcome:** HR users can safely query employee data without PII exposure; Approval Officers can review and decide on sensitive queries within 4 hours; column-level security enforces data boundaries.

**Done When:** Sensitive queries are checked against expanded attribute-based policies, PII/masked columns are safely handled, approval workflows gate protected data access, and users receive actionable permission/approval UX states.

**Explicitly Out of Scope:** Reworking principal attribute JWT mapping introduced in Epic 2A, export/report scheduling, forecast-specific explainability.

**FRs covered:** FR-A2 (full ABAC with department/region/clearance attributes), FR-A4 (column-level security), FR-A5 (PII masking Presidio), FR-A7 (approval workflow)

**UX items:**
- UX-DR12 (ConfidenceBreakdownCard) — build here, later Epic 7 consumes
- UX-DR13 (ApprovalBriefingCard)
- UX-DR15 (ExportConfirmationBar) — build here, later Epic 6 consumes
- UX-DR17 (PermissionRequestState)

**Required coordination notes:**
- Extend the `principal.attr` schema frozen in Epic 2A; do not backfill or rename baseline JWT-to-Cerbos mappings.

**Component Interface Notes:**
- Frontend: `ConfidenceBreakdownCard`, `ApprovalBriefingCard`, `PermissionRequestState`, `ExportConfirmationBar`
- Backend: policy decision service, masking/redaction pipeline, approval workflow service
- Shared contracts: `ApprovalRequest`, `PermissionDecision`, `MaskedField`, `ConfidenceBreakdown`

**NFR thresholds:** Approval workflow SLA <4 hours; masking regressions blocked by automated redaction tests; all protected-path failures emit auditable deny events.

**Phase:** 2 (Sprint 4-5) | **Requires:** Epics 2A, 2B

---

### Epic 5A — IT Admin Control Center

**User outcome:** IT Admin can onboard new departments, configure data source access, manage users/roles, and monitor system health and audit logs — without any manual Oracle configuration.

**Done When:** Admin users can manage core operational settings from the portal, observe system health and audits, and prepare department onboarding without touching infra manifests directly.

**Explicitly Out of Scope:** Semantic layer rollback authoring, medium/long-term memory management, curated onboarding demo experience.

**FRs covered:** FR-AD2 (user/role management + LDAP sync), FR-AD3 (data source configuration), FR-AD4 (audit dashboard), FR-AD5 (system health dashboard)

**UX items:** UX-DR27 (Admin Portal layout), partial UX-DR28 (Semantic Layer management UI read-only view), UX-DR26b candidate consume point for demo data if product wants admin-configurable demos later

**Component Interface Notes:**
- Frontend: admin shell, user/role management tables, data source config forms, audit dashboard, health dashboard
- Backend: admin API, LDAP sync adapter, data source config service, health aggregation service
- Shared contracts: `AdminUser`, `RoleAssignment`, `DataSourceConfig`, `HealthSnapshot`

**NFR thresholds:** Admin dashboard search/filter under 3 seconds for standard datasets; health signals refresh every 30 seconds with alert propagation under 2 minutes.

**Phase:** 1.5 (Sprint 2-3, parallel with 2A) | **Requires:** Epic 1.3 (Keycloak ready)

---

### Epic 5B — Data Governance & KPI Management

**User outcome:** Data Owners can manage KPI definitions with versioning and rollback; users benefit from persistent conversation memory across sessions; advanced memory features preserve context intelligently.

**Done When:** KPI/version governance workflows are operational in the admin portal, memory summaries persist across sessions without storing raw Oracle data, and governance users can audit and roll back semantic definitions safely.

**Explicitly Out of Scope:** Rebuilding admin shell foundations from Epic 5A, forecast-specific workflows, cross-domain execution logic.

**FRs covered:** FR-AD1 (Semantic Layer management full), FR-S2 (management UI), FR-M2, FR-M3, FR-M4, FR-M5, FR-M6, FR-M7 (full memory stack)

**UX items:** UX-DR28 (Semantic Layer admin with diff view + rollback), UX-DR26b (curated demo data integration and "try it now" flows if product keeps onboarding in Phase 2)

**Component Interface Notes:**
- Frontend: KPI version diff/rollback UI, memory history search, preference panels
- Backend: semantic layer version service, memory summarizer, history search service
- Shared contracts: `KpiDefinitionVersion`, `ConversationSummary`, `PreferenceProfile`, `HistorySearchResult`

**NFR thresholds:** History search <2 seconds; memory storage stores summaries/intents only and never raw Oracle values; rollback operations are fully audited.

**Phase:** 2 (Sprint 5-6) | **Requires:** Epic 2A (memory store), Epic 5A (admin portal shell)

---

### Epic 6 — Automated Reporting & Cross-domain Analysis

**User outcome:** Finance users get scheduled reports delivered automatically to their inbox; users can query across Finance + Budget domains simultaneously; popular queries return instantly from cache.

**Done When:** Export/report workflows operate end-to-end, cache improves common-query latency, and the team can execute cross-domain queries using a decomposition approach already validated by the Story 6.0 spike.

**Explicitly Out of Scope:** First implementation of decomposition research, new export confirmation UX implementation, forecasting models.

**FRs covered:** FR-E1, FR-E2, FR-E3, FR-E4 (export complete), FR-S5 (cross-domain query decomposition), FR-S6 (semantic result cache)

**UX items:**
- UX-DR14 (ExportJobStatus)
- UX-DR15 (ExportConfirmationBar) — consume implementation from Epic 4
- UX-DR22 (routing for report pages)
- UX-DR23 (command palette for report templates)

**Story outline:**
- 6.0: FR-S5 spike — define `QueryDecompositionState` TypedDict, horizontal vs vertical decomposition strategies, and merge patterns; runs in parallel with Epic 2B but implementation stays after Epic 2B
- 6.1: Scheduled report generation + delivery pipeline
- 6.2: Export authorization/audit integration on top of Epic 4 controls
- 6.3: Semantic result cache for common governed queries
- 6.4: Production cross-domain execution using the approved 6.0 decomposition model

**Component Interface Notes:**
- Frontend: report pages, export job status, export confirmation consume path, report template palette
- Backend: report scheduler, export worker, cache service, decomposition orchestrator
- Shared contracts: `ReportJob`, `ExportRequest`, `CachedQueryResult`, `QueryDecompositionState`, `MergedDomainResult`

**NFR thresholds:** Export async completion under 5 minutes for standard report sizes; cross-domain queries target P50<8s/P95<20s once implemented; cache hit rate goal >40% after two weeks of steady-state use.

**Phase:** 2 (Sprint 6-7) | **Requires:** Epics 2A, 4

---

### Epic 7 — Forecasting & Predictive Intelligence

**User outcome:** HR and Finance analysts can request time-series forecasts, anomaly detection alerts, and trend analysis in natural language, receiving explainable results without ML jargon.

**Done When:** Forecast and anomaly jobs run asynchronously, return business-readable explanations with uncertainty handling, and reuse shared confidence UI without duplicating it.

**Explicitly Out of Scope:** Rebuilding confidence breakdown UX, export/reporting, onboarding demo infrastructure.

**FRs covered:** FR-F1, FR-F2, FR-F3, FR-F4, FR-F5, FR-F6

**ARCH items:** Nixtla TimeGPT integration, async forecast worker (Celery)
**UX items:** UX-DR12 (ConfidenceBreakdownCard for forecast uncertainty) — consume implementation from Epic 4

**Component Interface Notes:**
- Frontend: forecast request form, anomaly alert panels, forecast result views
- Backend: forecast orchestrator, async worker, explainability formatter
- Shared contracts: `ForecastRequest`, `ForecastJob`, `ForecastExplanation`, `AnomalyAlert`

**NFR thresholds:** Forecast responses P50<10s/P95<30s after job execution begins; explainability outputs must include confidence intervals and top contributing factors.

**Phase:** 3 (Sprint 8+) | **Requires:** Epics 2A, 5B (memory for forecast context)

---

### Cross-cutting Clarifications

**UX ownership and consume rules:**
- UX-DR10 and UX-DR11 are built in Epic 2B; Epic 3 consumes the same components and must not rebuild them.
- UX-DR12 is built in Epic 4; Epic 7 consumes the same component for forecast uncertainty and must not fork it.
- UX-DR15 is built in Epic 4; Epic 6 consumes the same export confirmation component and must not create a parallel version.

**Accessibility enforcement:**
- UX-DR24 base ownership sits in Epic 1 for ARIA landmark structure and contrast validation in design tokens.
- UX-DR25 streaming screen reader behavior sits in Epic 2A alongside UX-DR5 `StreamingMessage`.
- Axe-core accessibility audit is acceptance criteria for every epic touching UI.

**Onboarding split:**
- UX-DR26a belongs to Epic 2A for flow structure, navigation logic, and step progression.
- UX-DR26b belongs to Epic 5A/5B for curated demo data integration and "try it now" flows.

**Shared infrastructure ownership:**
- `weaviate/schema.py` has single ownership through Story 2A.0 with Epic 1.6 bootstrap roots; Epic 2A and Epic 3 both consume it.
- `services/embedding/client.py` is scaffolded in Epic 1.5 and treated as the shared bge-m3 client contract before Epic 2A and Epic 3 parallel work starts.
- Cerbos principal attribute contract is frozen in Epic 2A before Epic 4 extends attribute-based policy coverage.

---

### Query Contract Sketch — Epic 2A

- Endpoint: `POST /v1/chat/query`
- Auth: Bearer JWT from Keycloak; request rejected if token missing, expired, or principal mapping incomplete.
- Content type: `application/json; charset=utf-8`
- Input contract:
  - `query`: UTF-8 string, Vietnamese or English, 1-1000 characters after trim
  - `session_id`: UUID string
  - `department_context`: optional string if chosen by user but must still be validated against JWT/Cerbos principal
  - `stream`: boolean, default `true`
- Success path:
  - API validates payload, resolves principal context, runs policy pre-check, classifies intent, starts orchestration, and returns stream handle or inline stream response
  - SSE events follow `thinking|querying|streaming|done|error` contract from ARCH-16
- Failure modes:
  - `400` invalid payload, encoding, or query length
  - `401` missing/invalid token
  - `403` policy deny or department mismatch
  - `409` ambiguous intent requiring confirmation
  - `422` SQL safety validation failure
  - `504` Oracle/query timeout
  - `5xx` orchestration or downstream service failure with structured problem payload

---

### Technology Decisions Appendix

- Database: PostgreSQL 16
- Cache/session store: Redis
- Vector store: Weaviate
- Auth: Keycloak with LDAP/AD federation
- API style: REST/JSON with SSE for streaming
- Frontend: React 18 + Vite 6 + TanStack Router + TanStack Query + Zustand
- Gateway: Kong
- Policy engine: Cerbos
- Backend orchestration: FastAPI + LangGraph
- Embedding model: `bge-m3` with 1024 dimensions
- Observability: OpenTelemetry + Tempo + Grafana + Langfuse
- Secret management baseline: HashiCorp Vault dev mode in Compose for local/dev

---

### Domain Glossary

- Query: the user's natural-language analytical question submitted to the system.
- Request: the API-level invocation carrying one query plus session/auth context.
- Job: an asynchronous unit of work such as export, ingestion, or forecasting.
- Task: an internal orchestration or worker step inside a request or job.
- Domain: a governed business data area such as Finance, Sales, or Budget.
- Principal: the authenticated user context projected into Cerbos and Oracle access checks.
- Semantic Layer: the governed business metric/dimension abstraction exposed to the LLM instead of raw Oracle schema.

---

### Epic Dependency Graph

```
Epic 1 (Walking Skeleton + SSO)
    ├──► Epic 2A (Core Query) ──► Epic 2B (Trust & Audit)
    │         └──► Epic 5A (Admin Control) [parallel with 2A]
    └──► Epic 3 (RAG) [parallel with 2A]

Epic 2A + 2B ──► Epic 4 (Security)
Epic 2A + 5A ──► Epic 5B (Data Governance)
Epic 2B  ──► Story 6.0 (Cross-domain spike) [parallel research]
Epic 2A + 4  ──► Epic 6 (Export & Reporting)
Epic 2A + 5B ──► Epic 7 (Forecasting)
```

### Phase Delivery Map

| Phase | Epics | User Value |
|-------|-------|-----------|
| **Phase 1** | 1, 2A, 2B, 5A | Minh can query; Lan can configure; audit works |
| **Phase 2** | 3, 4, 5B, 6 | Hoa/Hùng protected; RAG; export; cross-domain |
| **Phase 3** | 7 | Forecasting + predictive analytics |

---

## Epic 1: Governed Infrastructure & Walking Skeleton

**Goal:** Engineering team có thể chạy hệ thống end-to-end với E2E distributed traces observable; bất kỳ user nào có thể đăng nhập bằng SSO doanh nghiệp.

**Stories:** 9 stories (after merging 1.1+1.1b → 1.1; 1.3+1.4 → 1.3; 1.7 scoped to 1.7a minimal)

---

### Story 1.1: Monorepo Scaffold + Secrets Baseline

As a developer,
I want the AIAL monorepo initialized with uv workspaces, per-service pyproject.toml, Dockerfiles, Makefile, pre-commit hooks, and HashiCorp Vault dev mode for secrets,
So that every contributor can install, lint, run the project with one command and no credentials are ever hardcoded.

**Acceptance Criteria:**

**Given** a developer clones the repository for the first time
**When** they run `make install`
**Then** all Python workspace packages are installed via uv, Node packages installed, pre-commit hooks active, and `uv sync --all-packages` completes without version conflict warnings

**Given** the Pydantic version conflict between langchain-core and FastAPI is present
**When** `uv sync` resolves dependencies
**Then** pydantic v2 is the resolved version (`python -c "import pydantic; assert pydantic.VERSION.startswith('2')"` passes in CI); no runtime import errors from langchain-core

**Given** `docker-compose.dev.yml` starts
**When** any service reads a secret (Keycloak client secret, Oracle credentials, Kong admin token)
**Then** the secret is sourced from Vault dev mode via `infra/scripts/seed-secrets.sh` — never from a committed `.env` file; `.env` is gitignored; `.env.example` documents all required variables

**Given** a developer runs `make dev`
**When** the stack starts
**Then** `make test` runs all unit tests green; `make lint` runs Ruff + ESLint without errors; `.python-version` contains `3.12`

---

### Story 1.2: Compose Infrastructure Stack

As a developer,
I want all seven infrastructure services (PostgreSQL, Redis, Weaviate, Keycloak, Kong, Cerbos, Vault) to start reliably with Weaviate schema initialized,
So that the full local environment is reproducible with one command.

**Acceptance Criteria:**

**Given** `make dev` is run on a clean machine
**When** Docker Compose starts
**Then** all 7 services pass health checks within 60 seconds; `infra/scripts/wait-for-services.sh` exits 0; no manual step required

**Given** Weaviate starts
**When** `infra/scripts/init-weaviate-schema.py` runs
**Then** the shared `weaviate/schema.py` collections are created idempotently; this is the single owner of collection schema — Epics 2A and 3 consume this schema, never redefine it

**Given** Keycloak starts
**When** Docker Compose initializes
**Then** `keycloak/realm-export.json` is imported automatically; no manual realm configuration required

**And** `infra/scripts/seed-secrets.sh` populates Vault dev mode before services start; the Makefile target `make infra-up` executes full stack bootstrap

---

### Story 1.3: Auth Layer — SSO Login + Kong Gateway + Cerbos Authorization

As a business user,
I want to log in with my corporate credentials via SSO and have all API requests enforced by Kong and Cerbos,
So that unauthorized access is blocked at the gateway before reaching any service.

**Acceptance Criteria:**

**Given** a user navigates to the AIAL login page on a system under normal load (≤50 concurrent users)
**When** they click "Log in with corporate account"
**Then** they are redirected to Keycloak, authenticate via LDAP/AD, and a JWT is returned to the client within 3 seconds (measured from SSO redirect initiation to token receipt)

**Given** successful SSO authentication
**When** the JWT is decoded
**Then** it contains ALL of: `sub`, `email`, `department`, `roles[]`, `clearance` — each field non-null and non-empty; token expiry is 8h with refresh rotation enabled

**Given** a request to `POST /v1/chat/query` without a Bearer token
**When** Kong processes the request
**Then** HTTP 401 is returned immediately; no backend service is called; denial is logged in audit

**Given** a valid JWT but the user's role lacks access to the requested route
**When** Kong delegates to Cerbos
**Then** HTTP 403 is returned; Cerbos denial event is logged with principal context; no Oracle query is executed

**And** Kong configuration is stored in `infra/kong/kong.yml` (declarative DB-less mode); Cerbos PDP is deployed and connected in this story; rate limiting baseline active (100 requests/day per user)

---

### Story 1.4: FastAPI Service Skeleton + OpenTelemetry

As a developer,
I want a FastAPI application skeleton with health/readiness endpoints, OpenTelemetry instrumentation, and a shared embedding client scaffold,
So that every service emits distributed traces from the first request and the bge-m3 client contract is established before parallel tracks start.

**Acceptance Criteria:**

**Given** the orchestration service starts
**When** `GET /health` is called
**Then** HTTP 200 `{ "status": "healthy" }` is returned; `GET /readiness` returns 200 only when downstream dependencies (PostgreSQL, Redis, Cerbos) are reachable

**Given** any API request is processed
**When** OpenTelemetry middleware runs
**Then** a trace span is created with `trace_id`, `service.name`, `span.kind` attributes; spans are exported to the Tempo collector via OTLP

**And** `aial_shared/telemetry/tracer.py` exports `setup_tracing(service_name)` called as the first line of every service `main.py`; `services/embedding/client.py` stub scaffolded with `BGE_MODEL_NAME="BAAI/bge-m3"`, `DIMS=1024` — this is the shared contract before Epic 2A and Epic 3 parallel work begins

---

### Story 1.5: LangGraph Stub Graph + Shared State Contract

As a developer,
I want a LangGraph stub graph with the finalized `AIALGraphState` TypedDict and a single pass-through node wired to Redis checkpointer,
So that Epic 2A can extend the graph with real nodes without redefining the state contract.

**Acceptance Criteria:**

**Given** the orchestration service receives a chat query request
**When** the LangGraph stub graph is invoked
**Then** it processes through the stub node and returns `{ "answer": "stub", "trace_id": <uuid> }` with `AIALGraphState` fields populated

**Given** `AIALGraphState` is defined in `services/orchestration/src/orchestration/graph/state.py`
**When** any node in Epic 2A imports it
**Then** it uses the exact TypedDict without redefining fields; schema includes: `trace_id`, `session_id`, `user_id`, `department_id`, `messages`, `intent_type`, `sql_result`, `rag_result`, `final_response`, `error`, `should_abort`

**Given** unit tests for LangGraph nodes run
**When** Redis is not available
**Then** tests use `fakeredis.FakeRedis` as the checkpointer backend and pass without a real Redis connection; integration tests tagged `@pytest.mark.requires_redis` are skipped if Redis unavailable

**And** `RedisSaver` checkpointer configured with `thread_id=session_id`; ARCH-10 state contract frozen and documented before Epic 2A story work begins; prerequisite note: "Requires Story 1.2 Redis service for integration tests"

---

### Story 1.6: Observability Minimal Stack

As a platform engineer,
I want distributed traces and LLM observability viewable in Grafana with a single dashboard covering latency, error rate, and LLM node execution,
So that any request failure can be investigated from day one of feature development.

**Acceptance Criteria:**

**Given** any service processes a request
**When** the OpenTelemetry collector receives spans
**Then** traces are stored in Grafana Tempo and searchable by `trace_id` within 10 seconds; Langfuse captures LLM invocation events with token counts

**Given** the Grafana dashboard is opened
**When** a query completes
**Then** the dashboard shows 3 panels: P50/P95 request latency by service, error rate %, and LangGraph node execution count per session

**And** full Prometheus alerting rules and extended dashboard library are deferred to Sprint 1 (Story 1.6b); this story delivers the minimum needed for Story 1.9 E2E gate

---

### Story 1.7: Frontend Shell + Design Tokens + Accessibility Foundation

As a developer,
I want the React 18 + Vite 6 frontend shell with design tokens, TanStack Router skeleton, Error Boundary hierarchy, and a passing axe-core accessibility baseline,
So that Epic 2A can build streaming components on a consistent, accessible foundation without design drift.

**Acceptance Criteria:**

**Given** the frontend starts
**When** the app renders
**Then** CSS custom properties from `packages/ui/src/styles/tokens.css` are loaded (Deep Teal `#0F7B6C`, warm gray neutrals, animation tokens); Inter + Noto Sans Vietnamese font stack is active; auth redirect to Keycloak login page works

**Given** a streaming component crashes during development
**When** the error propagates
**Then** `StreamErrorBoundary` renders a fallback (not a blank screen); `PageErrorBoundary` catches page-level errors; `AppErrorBoundary` is root safety net

**Given** axe-core accessibility audit runs against the shell (login page, main layout)
**When** audit completes with ruleset `["wcag2a", "wcag2aa"]`
**Then** ZERO violations of impact level "critical" or "serious"; ≤5 moderate violations each with a documented exception ticket; audit report artifact is saved to CI; ARIA landmark structure (`<main>`, `<nav>`, `<header>`) is present

**And** `useSSEStream` hook stub is scaffolded with interface only (not connected to backend); TanStack Router `defaultPreload: 'intent'` configured; scope is strictly shell + auth + error boundaries — NO Storybook, NO full design system, NO theme switching

---

### Story 1.8: Oracle VPD Smoke Test

As a security engineer,
I want Oracle Virtual Private Database row-level security validated in CI before any Epic 2A Oracle code is written,
So that the P0 security requirement is confirmed and Epic 2A cannot merge code that bypasses VPD.

**Acceptance Criteria:**

**Given** Oracle XE runs in testcontainers (`gvenzl/oracle-xe:21-slim`, startup timeout 120s) with a VPD policy applied to a test table
**When** Service Account A queries the table with `user_id=A` in the Oracle session context
**Then** only rows owned by user A are returned; rows owned by user B are not visible in the result

**Given** Service Account A's connection is returned to the connection pool and reused for a user B request WITHOUT context reset
**When** user B's query executes
**Then** the test **FAILS** — this verifies that `ALTER SESSION SET CONTEXT` must be called before every query; the pool must force context reset before releasing connections

**And** test is tagged `@pytest.mark.p0_security @pytest.mark.slow @pytest.mark.requires_oracle`; runs in CI before any Epic 2A story is merged (ARCH-13 resolved); test uses `cx_Oracle` or `python-oracledb` with `homogeneous=False` SessionPool

**Referenced story file:** `implementation-artifacts/1-9-oracle-vpd-smoke-test.md`

---

### Story 1.9: E2E Walking Skeleton Gate

As a developer and PM,
I want a complete authenticated request to flow end-to-end (Kong → FastAPI → Cerbos → LangGraph stub) with a distributed trace visible in Tempo and a demo-able happy path,
So that the integration harness is proven and stakeholders can see the system responding before Epic 2A features are built.

**Acceptance Criteria:**

**Given** a valid Keycloak JWT is obtained for a test user with `roles=["analyst"]` and `department="sales"`
**When** `POST /v1/chat/query` is called with `{ "query": "test query", "session_id": "<uuid>" }`
**Then** HTTP 200 OK is returned within 5 seconds; response body contains `{ "answer": <non-empty string>, "trace_id": <uuid> }`

**Given** the request completes successfully
**When** Grafana Tempo is queried for the `trace_id` within 30 seconds
**Then** a complete trace is visible with spans for ALL FOUR services: `kong-gateway`, `cerbos-authz`, `fastapi-orchestration`, `langgraph-stub`; all spans linked by the same `trace_id`; if ANY span is missing, this gate FAILS

**Given** an expired or malformed JWT
**When** `POST /v1/chat/query` is called
**Then** HTTP 401 is returned with error body `{ "code": "AUTH_FAILED" }`; NO backend spans appear in Tempo for this request

**Given** the system is running and a PM clicks through the application
**When** the demo flow is executed (login via SSO → land on dashboard → submit a query → receive mock response)
**Then** the complete user flow is click-through-able without engineering assistance; the UI does not show a blank screen or unhandled error at any step

**Given** Kong is stopped while the system is running
**When** a new request is sent
**Then** the frontend's `ConnectionStatusBanner` displays a degraded-state message; Grafana fires an alert; the Error Boundary renders a graceful fallback — not a blank screen

**And** this story is the WALKING SKELETON GATE — Epic 2A, Epic 3, and Epic 5A MUST NOT start until Story 1.9 passes in CI; gate is automated in the CI pipeline

---

## Epic 2A: Minimal Viable Query

**Goal:** Sales/Finance users can ask a question in Vietnamese, receive Oracle data results with SQL explanation stub, filtered by their row-level permissions, with every query logged.

**Done When:** A real business user (Minh/Sales persona) submits a NL query through the streaming UI, receives a governed Oracle result within P50 <3s TTFB, Cerbos policy enforcement verified by unit test, short-term memory resolves follow-up "nó/cái đó"; FR-O5 SQL explanation renders as placeholder stub (full implementation in Epic 2B).

**Stories:** 2A.0–2A.9 (10 stories)

---

### Story 2A.0: Weaviate Schema Bootstrap

As a developer,
I want a single authoritative `weaviate/schema.py` that creates all required Weaviate collections idempotently,
So that Epic 2A (semantic query cache) and Epic 3 (document RAG) can both consume schema without forking ownership.

**Acceptance Criteria:**

**Given** `init-weaviate-schema.py` runs against a fresh Weaviate instance
**When** the script completes
**Then** collections `QueryResultCache` and `DocumentChunk` are created with correct vectorizer config; script is idempotent — running twice produces no error

**Given** Epic 3 ingestion pipeline imports from `weaviate/schema.py`
**When** it references collection names
**Then** it uses the same definitions without redefinition; schema changes must be made in `weaviate/schema.py` only — Epic 3 never forks schema ownership

**And** `model_version="bge-m3-v1"` is stored as a property on all vector documents; changing the embedding model requires a migration script, not a silent overwrite

**Referenced story file:** `implementation-artifacts/2a-0-weaviate-schema-bootstrap.md`

---

### Story 2A.1: Query API Endpoint + Input Validation

As a business user,
I want `POST /v1/chat/query` to accept my Vietnamese query and return a stream handle,
So that my question enters the system correctly validated before any Oracle query runs.

**Acceptance Criteria:**

**Given** a valid authenticated request with `{ "query": "Doanh thu HCM tháng 3?", "session_id": "<uuid>" }`
**When** `POST /v1/chat/query` is called
**Then** HTTP 200 is returned with `{ "request_id": "<uuid>", "status": "streaming", "trace_id": "<uuid>" }`; SSE stream begins

**Given** a query string longer than 2000 characters or empty after trim
**When** the endpoint receives the request
**Then** HTTP 400 with `{ "type": ".../errors/invalid-query", "detail": "..." }`; no LangGraph invocation occurs

**Given** a user requests SQL explanation for a completed query
**When** FR-O5 is not yet implemented (Epic 2B)
**Then** the UI renders: "Giải thích câu truy vấn sẽ có trong bản cập nhật tiếp theo" (graceful placeholder stub); no error, no broken UI; full FR-O5 implementation deferred to Epic 2B

**And** `ChatQueryRequest` Pydantic v2 model validates: `query` (str 1–2000 chars), `session_id` (UUID); NFR-CM2 rate limit (100/day per user) enforced via Kong + Redis counter

---

### Story 2A.2: Semantic Layer Bootstrap + Business Glossary API

As a data analyst,
I want queries to resolve through a governed semantic layer so business terms map correctly to Oracle columns,
So that "doanh thu thuần" reliably maps to the correct formula without LLM guessing.

**Acceptance Criteria:**

**Given** a query containing "doanh thu thuần" is processed
**When** the semantic layer resolves business terms
**Then** the term maps to the pre-defined metric formula from the glossary catalog; the LLM receives this definition, NOT raw column names from Oracle

**Given** the glossary service is called with `GET /v1/glossary/{term}`
**When** the term exists in the catalog
**Then** it returns `{ "term": "doanh thu thuần", "definition": "...", "formula": "...", "owner": "Finance", "freshness_rule": "daily" }` from PostgreSQL

**Given** a term is not in the glossary
**When** the semantic layer is queried
**Then** it returns `{ "status": "not_found" }` and the orchestrator initiates intent clarification; no raw Oracle schema column name is exposed to the LLM

**And** S2 Interface Contract document created before this story merges; Epic 5B management UI will extend this API without breaking changes; management CRUD deferred to Epic 5B

---

### Story 2A.3: SQL Generation Guardrails + Query Governor

As a security engineer,
I want all LLM-generated SQL to pass two-layer validation (AST + regex blocklist) and be subject to execution limits,
So that no destructive, resource-abusive, or Oracle-specific injection can execute even if the LLM is compromised.

**Acceptance Criteria:**

**Given** the LLM generates SQL containing `DROP TABLE`, `INSERT`, `UPDATE`, `DELETE`, or any DDL
**When** the AST validator (sqlglot Oracle dialect) runs
**Then** the query is rejected with `{ "code": "SQL_UNSAFE_OPERATION" }`; no Oracle connection is opened; rejection logged in audit

**Given** the LLM generates SQL containing Oracle-specific dangerous patterns
**When** the regex blocklist runs in parallel with sqlglot
**Then** queries matching any of these patterns are blocked: `\bCONNECT\s+BY\b` (hierarchical query billion-row exploit), `\bXMLQUERY\b` (sqlglot weak support), `\bDBMS_\w+\b` (PL/SQL injection), `@\w+` (database links), `\bFLASHBACK\b` (temporal VPD bypass), `\bEXECUTE\s+IMMEDIATE\b`

**Given** a valid SELECT query on a table with >1M rows without a partition predicate
**When** the query governor evaluates
**Then** it is blocked with `{ "code": "QUERY_GOVERNOR_VIOLATION", "reason": "full_table_scan_prohibited" }`; user receives friendly message suggesting to add date filters

**Given** a valid SELECT query is approved
**When** the query governor applies limits
**Then** `FETCH FIRST 50000 ROWS ONLY` is appended if absent; query timeout set to 30 seconds; Cartesian joins detected and blocked

---

### Story 2A.4: Oracle Execution with Identity Passthrough + VPD Enforcement

As a business user,
I want Oracle queries to execute under my own identity with row-level security enforced at the database layer,
So that I can only see data I am authorized to access, even if the SQL was generated incorrectly.

**Acceptance Criteria:**

**Given** a connection pool session previously used by User A, with NO Oracle session context reset applied
**When** User B's request attempts to use that connection
**Then** the system DETECTS the missing context reset, REJECTS the connection before query execution, returns `SESSION_CONTEXT_VIOLATION` error; Oracle query is NEVER executed; the rejection is logged in audit

**Given** a connection with full VPD context reset applied for User B (`SYS_CONTEXT` populated with User B's `USER_ID`, `DEPARTMENT`)
**When** User B's query executes
**Then** Oracle returns ONLY rows authorized for User B; VPD policy filters are verified; integration test `1-8-oracle-vpd-smoke-test.md` must pass in CI before this story can merge

**Given** the Oracle connector completes a query (success or failure)
**When** the connection is returned to the pool
**Then** `_clear_oracle_context(conn)` is called in a `finally` block (not `else`) BEFORE the connection is released; this guarantees cleanup even if an exception occurs mid-query

**And** connection pool uses `homogeneous=False` (heterogeneous pool) with `homogeneous=False` so each request sets its own proxy context; service account used is per-service read-only (not shared DBA); `principal.attr` schema (`department`, `clearance`) must be documented from Story 2A.7 before this story implements Oracle context mapping

---

### Story 2A.5: Streaming Chat UI + SSE Transport

As a business user,
I want to see my query results stream progressively with precise thinking-state feedback and accessible screen reader announcements,
So that I understand the system is working and trust the result as it arrives.

**Acceptance Criteria:**

**Given** a query is submitted (0–300ms)
**When** Thinking Pulse Phase 1 starts
**Then** the input query is echoed; "Đang phân tích..." text appears; animation: opacity 0.4→1.0, duration 600ms, `cubic-bezier(0.4, 0, 0.2, 1)`, loop; ARIA live region announces "AI đang xử lý"

**Given** processing continues 300ms–2s
**When** Thinking Pulse Phase 2 is active
**Then** scale animation: 1.0→1.05→1.0, duration 800ms, ease-in-out, loop; cross-fade transition 200ms between phases

**Given** processing continues beyond 2 seconds
**When** LangGraph emits SSE step events
**Then** step narration updates: "Bước 1/4: Phân loại..." → "Bước 2/4: Truy vấn Oracle..." → "Bước 3/4: Tổng hợp..."; `prefers-reduced-motion`: replace all animation with static indicator + "đang xử lý..." text; no animation runs

**Given** data rows stream back
**When** `ProgressiveDataTable` receives row events
**Then** rows are batched every 150ms (data trigger interval); each chunk renders with fade-in 60ms ease-out (presentation layer); minimum visible chunk ≥15 tokens to prevent micro-flicker; column headers locked during streaming (no layout shift); `isAnimationActive={false}` on Recharts

**Given** stream completes or user presses Escape
**When** `StreamAbortButton` is activated
**Then** SSE connection closes; `_clear_oracle_context` called if Oracle query in-flight; UI shows "Đã hủy"; button visible at ALL times during streaming — never hidden in a menu

**And** `useSSEStream` hook is the ONLY source of SSE connections; UX-DR25: ARIA live region announces per sentence boundary, not per token; `ConnectionStatusBanner` appears within 3 seconds if SSE drops

---

### Story 2A.6: Short-term Session Memory + Per-Turn Security

As a business user,
I want the system to remember context within my current session for natural follow-up questions, with security re-checked every turn,
So that I don't repeat context and no privilege can accumulate across turns.

**Acceptance Criteria:**

**Given** Minh asks "Doanh thu HCM tháng 3?" followed by "Vì sao giảm?"
**When** the second question is processed
**Then** the orchestrator injects context from Redis session memory; the follow-up resolves correctly without Minh repeating "tháng 3, chi nhánh HCM"

**Given** user A's session is active in Redis
**When** user B sends a request
**Then** user B has NO access to user A's session memory; `session_id` is bound to `user_id + department_id`; cross-user memory injection is technically impossible

**Given** a new conversation turn runs
**When** LangGraph processes the turn
**Then** Cerbos policy check is executed independently for EVERY turn with the current principal context; no permissions from a previous turn carry forward

**And** Redis TTL = 24 hours; after expiry backend returns `{ "session_expired": true }`; UI shows "Phiên làm việc đã hết hạn"; token usage increases <20% after 10 turns (FR-M5); unit tests use `fakeredis.FakeRedis`; integration tests use `testcontainers-python` with `redis:7-alpine` (tagged `@pytest.mark.requires_redis`)

---

### Story 2A.7: Baseline Cerbos Policy + principal.attr Schema Freeze

As a developer,
I want Cerbos policies deployed with a frozen `principal.attr` schema so Epic 4's full ABAC extension can build on a stable contract,
So that Epic 4 never needs to backfill JWT claim mapping.

**Acceptance Criteria:**

**Given** a user authenticates and JWT is decoded
**When** the principal context is constructed for Cerbos
**Then** `principal.attr` always contains: `department` (string), `clearance` (string) — both non-null, mapped from Keycloak JWT claims; fields populated even if Epic 2A uses only role-based checks

**Given** Epic 2A baseline policy is evaluated
**When** `roles=["analyst"]` and `department="sales"` user queries Sales data
**Then** Cerbos returns ALLOW; same user querying Finance data returns DENY; denial logged with principal context

**Given** this story is marked complete and Epic 4 begins
**When** Epic 4 extends Cerbos policies
**Then** Epic 4 ADDS new attributes (`region`, `approval_authority`) but does NOT rename, remove, or re-type `department` or `clearance`; an ADR documents this contract freeze before Epic 4 begins

**And** policy files in `infra/cerbos/policies/` with YAML unit test fixtures in `tests/`; `cerbos compile ./policies` runs in CI; test coverage: ALLOW for correct dept, DENY for wrong dept, DENY without required role

**Referenced story file:** `implementation-artifacts/2a-7-cerbos-principal-attr-baseline.md`

---

### Story 2A.8: Query Lifecycle Audit Logging

As a compliance officer,
I want every query lifecycle event recorded in an immutable audit log without storing raw PII or query results,
So that any query can be fully traced for compliance without violating PDPA data minimization principles.

**Acceptance Criteria:**

**Given** a query completes successfully
**When** the audit logger writes the event
**Then** `audit_events` table (PostgreSQL, append-only) contains: `request_id`, `user_id`, `department_id`, `timestamp`, `intent_type`, `sensitivity_tier`, `sql_hash` (SHA-256), `data_sources[]`, `rows_returned`, `latency_ms`, `policy_decision`, `session_id`; raw SQL text and raw result values are NEVER stored

**Given** a query is classified as sensitive (references columns tagged `PII_TIER_1` or `PII_TIER_2` in metadata catalog, OR WHERE clause matches patterns in `sensitivity-patterns.yaml`)
**When** the audit entry is written
**Then** only hash + metadata is stored (no raw SQL text for sensitive queries); non-sensitive queries store encrypted raw SQL in a separate audit column

**Given** a query is rejected by Cerbos or SQL validator
**When** the rejection occurs
**Then** denial event is logged with `status=DENIED`, `denial_reason`, `principal_context`; log entry created even if no Oracle connection was opened

**And** audit log is append-only enforced at PostgreSQL level; retention ≥12 months; `GET /v1/admin/audit-logs` returns results <3s for standard date ranges; NFR-OB1/OB2/OB3 events emitted for every audit write

---

### Story 2A.9: Onboarding Shell + First-Query Scaffold

As a first-time business user,
I want a guided onboarding flow that helps me successfully submit my first query without IT assistance,
So that I feel confident and competent using AIAL from day one.

**Acceptance Criteria:**

**Given** a user logs in for the FIRST TIME (no stored role preference)
**When** the onboarding flow starts
**Then** Screen 0 is mandatory (cannot be skipped): "Bạn thường dùng dữ liệu để làm gì?" with 3 visual options `[📅 Báo cáo định kỳ]` `[⚡ Trả lời câu hỏi từ sếp]` `[🔍 Phân tích chuyên sâu]`; user cannot proceed without selecting; role preference stored server-side (not localStorage)

**Given** a RETURNING user with an existing role preference logs in
**When** the app loads
**Then** Screen 0 is SKIPPED; user goes directly to chat shell; a "Change role" option is available in the profile menu to re-trigger Screen 0; trigger condition is "role stored", not "previously logged in"

**Given** a user selects their role and reaches Screen 2 (First Query Scaffold)
**When** the chat input renders
**Then** role-specific placeholder is shown: Sales → "VD: Doanh thu chi nhánh HCM tháng này?"; real-time intent hint appears after 500ms pause: "AIAL sẽ dùng dữ liệu từ SALES domain"

**Given** the user's first query returns no data (production data unavailable for their domain)
**When** the system responds
**Then** it renders the "First Query Guide" variant (NOT a generic EmptyStateCard): includes (1) plain-language explanation of why no data was found, (2) a suggested alternative query pre-filled specific to the user's role, (3) a "Try this instead →" CTA button; user has ≥1 clear path forward without reading documentation or contacting support

**Given** any error occurs during the first query (timeout, permission denied, validation failure)
**When** the error state renders
**Then** the UI NEVER shows a blank screen or raw error JSON; an appropriate `ErrorBoundary` or `EmptyStateCard` variant is shown with role-aware guidance and ≥2 exit actions

**And** this story implements UX-DR26a (flow structure, navigation, step progression) only — curated demo data (UX-DR26b) deferred to Epic 5A/5B; progressive reveal begins after first success: export tooltip on first result, context indicator on first follow-up

---

## Epic 2B: Trust & Audit Layer

**Goal:** Every answer shows exactly where data came from; every query is fully auditable by compliance officers; users understand AI reasoning.

**Done When:** CitationBadge, ProvenanceDrawer, and ChartReveal are built and published to `packages/ui`; compliance officers can trace any completed request end-to-end; FR-O5 SQL explanation replaces the stub from Epic 2A.

**Note:** Story 6.0 (FR-S5 cross-domain spike) runs in parallel with Epic 2B timeline — see Epic 6.

---

### Story 2B.1: Full SQL Explanation (FR-O5)

As a business user,
I want to see a plain-Vietnamese explanation of how my answer was calculated — what data was used, which filters applied, and what the metric formula means,
So that I can trust and verify the answer before using it in a meeting.

**Acceptance Criteria:**

**Given** a query produces an Oracle-backed result
**When** the user expands "Xem giải thích"
**Then** the explanation shows: (1) human-readable data source description, (2) metric formula in plain Vietnamese if applicable, (3) filters applied; raw SQL is NOT shown by default

**Given** the user clicks "Xem SQL gốc" (progressive disclosure)
**When** the SQL panel expands
**Then** generated SQL displayed in read-only syntax-highlighted block with disclaimer "SQL được kiểm tra an toàn trước khi thực thi"

**Given** the LLM cannot produce a confident explanation
**When** the explanation renders
**Then** `ConfidenceIndicator` shows "Đây là giải thích ước tính — độ tin cậy: Trung bình"; uncertainty surfaced proactively

**And** explanation generated in LangGraph `compose_response` node; cached alongside query result; stub from Epic 2A Story 2A.1 replaced by this implementation

---

### Story 2B.2: Citation Badge Component (UX-DR10 — BUILD HERE)

As a business user,
I want inline citation markers that expand to show the exact data source for each claim,
So that I can verify any number traces back to a real, authorized source.

**Acceptance Criteria:**

**Given** a response contains a cited claim (e.g., "Doanh thu đạt 45.2 tỷ [1]")
**When** `CitationBadge` renders
**Then** the `[1]` badge is a focusable button with `aria-label="Xem nguồn số 1"`; badge index uses `citationNumber` from `CitationRef` object — NOT computed from array index

**Given** user hovers or focuses the badge
**When** tooltip opens
**Then** shows: data source name, table/document reference, data freshness timestamp; raw schema names are NOT the primary label

**Given** Epic 3 or later epics need citations
**When** they import `CitationBadge` from `packages/ui`
**Then** they use this component — no rebuild; accepts both `{ type: "sql" }` and `{ type: "document" }` variants

**And** `CitationRef` contract: `{ citationNumber: number, type: "sql"|"document", label: string, details: CitationDetails }`; Epic 3 consumes — no new implementation

---

### Story 2B.3: Provenance Drawer Component (UX-DR11 — BUILD HERE)

As a power user,
I want a side panel showing the complete provenance of an answer — all sources, freshness, metric definitions, and confidence — without navigating away,
So that I can perform due diligence before sharing AI-generated insights.

**Acceptance Criteria:**

**Given** user clicks "Xem toàn bộ nguồn"
**When** `ProvenanceDrawer` opens
**Then** slides in from right as side panel (not modal); conversation remains visible and interactive; closeable with Escape; focus returns to trigger button on close

**Given** drawer is open for SQL-backed result
**When** user reviews provenance
**Then** shows: all data sources (table names, freshness, row counts), metric formulas in plain Vietnamese, Cerbos policy decision summary, SQL explanation

**Given** Epic 3 or Epic 4 imports `ProvenanceDrawer`
**When** opened for RAG or masked result
**Then** same component renders with additional `{ type: "document" }` or `{ type: "masked" }` sections — no fork; accepts pluggable `ProvenanceSection` children

**And** `role="complementary"`, accessible label "Nguồn dữ liệu và bằng chứng"; focus trapped when open; `data-testid="provenance-drawer"`

---

### Story 2B.4: Chart Reveal + Data Freshness Signals (UX-DR9)

As a business user,
I want charts to appear smoothly only when data is complete, with freshness clearly indicated,
So that I never see a half-rendered chart that could mislead me.

**Acceptance Criteria:**

**Given** chart data JSON stream is incomplete
**When** `ChartReveal` is active
**Then** skeleton placeholder shown with same dimensions as expected chart; no partial bars or axis labels rendered

**Given** JSON stream completes
**When** `ChartReveal` transitions
**Then** chart fades in over 400ms, `cubic-bezier(0.4, 0, 0.2, 1)`; `prefers-reduced-motion` → instant reveal; `isAnimationActive={false}` on all Recharts

**Given** any chart renders
**When** user views it
**Then** freshness indicator visible: `🟢 Cập nhật lúc 09:00 hôm nay` / `🟡 Dữ liệu từ hôm qua` / `🔴 Dữ liệu > 24 giờ`; color-coded AND text-labeled (not color-only)

**And** `useChartTheme()` hook provides CSS-var-based colors; aspect ratio locked during skeleton to prevent layout shift

---

### Story 2B.5: Audit Read Model + Compliance Dashboard

As a compliance officer,
I want to search and filter the complete audit log for any query, user, or data access event,
So that I can fulfill compliance investigations without requiring engineering database access.

**Acceptance Criteria:**

**Given** compliance officer applies filters (user, date range, action type, data source, policy decision)
**When** search executes
**Then** results returned in <3 seconds for ranges up to 90 days; shows timestamp, user, intent, data sources, policy decision, rows returned — NOT raw query text for sensitive queries or raw result values

**Given** officer searches for a specific `request_id`
**When** search executes
**Then** full lifecycle displayed: intake → classification → policy check → Oracle execution → result delivery → audit write; each step with timestamp

**Given** audit entry exists for DENIED query
**When** officer views it
**Then** shows: `status=DENIED`, `denial_reason`, `principal_context`, which Cerbos rule triggered deny

**And** read-only UI — no edit/delete; paginated API; CSV export for date ranges; can be delivered as read-only page within Admin Portal shell from Epic 1 Story 1.3

---

## Epic 3: Document Intelligence & Hybrid Answers

**Goal:** Users get combined Oracle + document answers with citations from both sources; Admin can manage documents.

**Done When:** Documents can be ingested, policy-filtered before retrieval, and surfaced in hybrid answers using shared CitationBadge + ProvenanceDrawer from Epic 2B; all 5 FRs (R1-R5) verified.

---

### Story 3.1: Document Ingestion Pipeline (FR-R1)

As an IT Admin,
I want to upload PDF, DOCX, XLSX, and TXT files that are automatically parsed, chunked, embedded, and indexed with required metadata,
So that documents are searchable within 5 minutes of upload completion.

**Acceptance Criteria:**

**Given** an admin uploads a PDF file < 100 pages via Admin Portal
**When** HTTP 200 upload response is returned (T0)
**Then** the document is queryable via the search API within 300 seconds (T0 + 5 minutes); this is measured from HTTP 200 response, not from when ingestion begins; measurement excludes network latency

**Given** ingestion pipeline runs
**When** chunks are written to Weaviate
**Then** each chunk contains: `document_id`, `department`, `classification` (int: 0=PUBLIC, 1=INTERNAL, 2=CONFIDENTIAL, 3=SECRET), `source_trust`, `effective_date` (ISO 8601 date type), `model_version="bge-m3-v1"`, `chunk_index`, `page_number`; `effective_date` must be stored as Weaviate `date` type — NOT text (required for range filtering in Story 3.4)

**Given** a document is uploaded without required metadata
**When** the upload form is submitted
**Then** upload is rejected with HTTP 400 with field-level errors; file is not ingested; rollback is clean

**And** chunking uses `SentenceSplitter(chunk_size=512, chunk_overlap=64)` with Vietnamese-aware separators; ingestion runs as Celery task `rag.document.sync_index` with `acks_late=True`, `reject_on_worker_lost=True`; Weaviate schema from Story 2A.0 consumed — no schema forking

---

### Story 3.2: Pre-retrieval Policy Filtering (FR-R2)

As a business user,
I want document retrieval to enforce my department access permissions before any vector search runs,
So that I never receive document chunks from departments I'm not authorized to access — even if they are semantically relevant.

**Acceptance Criteria:**

**Given** user from Sales department submits a query about "salary negotiation policy"
**When** RAG retrieval runs
**Then** `PolicyEnforcementService` calls Cerbos first → receives `allowed_departments` and `max_classification` → `WeaviateFilterBuilder` translates this into a Weaviate `where` filter → vector search runs only on permitted chunks; HR chunks with semantic score 0.95 are EXCLUDED; a Sales chunk with semantic score 0.60 is returned instead

**Given** Cerbos returns ALLOW for Sales data
**When** `WeaviateFilterBuilder` constructs the filter
**Then** the filter uses `Filter.by_property("department").contains_any(allowed_departments)` combined with classification range filter; filtering happens at the Weaviate layer before vector scoring — NOT post-retrieval

**Given** policy filtering excludes relevant chunks for the user's query
**When** the answer is composed
**Then** the response includes a notice: "Kết quả có thể bị giới hạn bởi quyền truy cập của bạn" (Results may be limited by your access level); user is not left wondering why the answer is incomplete

**And** `PolicyEnforcementService` and `WeaviateFilterBuilder` are separate classes; Cerbos timeout (>500ms) triggers circuit breaker with fail-closed behavior — request denied, not passed through; the Cerbos policy decision is logged in audit

---

### Story 3.3: Hybrid Answer Composition with Citations (FR-R3)

As a business user,
I want answers that combine Oracle data with document insights, with every claim cited from its specific source,
So that I know exactly which database table and which document supported each part of the answer.

**Acceptance Criteria:**

**Given** a hybrid query ("Vì sao doanh thu giảm?") requires both SQL data and document context
**When** LangGraph orchestrates the hybrid path
**Then** SQL retrieval and RAG retrieval run in PARALLEL via `asyncio.gather()`; results are merged in `merge_results_node` using Reciprocal Rank Fusion (RRF, k=60); final answer is composed in `compose_answer_node`; citations are formatted in `format_citations_node`

**Given** `format_citations_node` builds the citation structure
**When** the response is rendered
**Then** SQL sources use `CitationBadge { type: "sql", table, timestamp }`; document sources use `CitationBadge { type: "document", title, page, department }`; Epic 2B CitationBadge and ProvenanceDrawer components are consumed — NOT rebuilt

**Given** the 3-node decomposition: `merge_results_node` → `compose_answer_node` → `format_citations_node`
**When** any single node fails
**Then** only that node is retried; merge and citation formatting are idempotent; LangGraph traces show per-node latency separately (diagnose whether SQL, RAG, or LLM is the bottleneck)

**And** cross-source merge does not expose data from unauthorized departments; NFR-OB1 traces cover both SQL and RAG execution paths with separate spans

---

### Story 3.4: Document Access Control (FR-R4)

As an IT Admin,
I want every document to have mandatory access control metadata validated at upload and enforced at retrieval including time-based staleness exclusion,
So that no document can be accessed without explicit authorization or after it has expired.

**Acceptance Criteria:**

**Given** a document upload request arrives without all required metadata fields
**When** validation runs
**Then** HTTP 400 with specific field-level errors for each missing field (`department`, `classification`, `effective_date`, `source_trust`); partial uploads are rolled back; no Celery task is enqueued

**Given** a document has `classification="CONFIDENTIAL"` and the user's `clearance < 2`
**When** retrieval runs
**Then** that document's chunks are excluded from vector search via Weaviate classification filter; the exclusion is transparent to the query (system still returns available results from permitted sources); exclusion is logged in audit

**Given** a document's `effective_date` is older than the configured staleness threshold
**When** retrieval runs
**Then** chunks from that document are excluded via `Filter.by_property("effective_date").greater_or_equal(cutoff)`; staleness threshold is CONFIGURABLE (default: 180 days) per department in the Admin Portal — NOT hardcoded; a document with `effective_date` exactly at the boundary (180th day) is INCLUDED (greater_or_equal behavior)

**And** access control metadata is stored per Weaviate chunk (not only document-level); `effective_date` stored as Weaviate `date` type from Story 3.1; staleness threshold configurable by IT Admin in data source config

---

### Story 3.5: Admin Document Management (FR-R5)

As an IT Admin or Data Owner,
I want to view, edit metadata, re-index, and delete documents through the Admin Portal with observable async re-index progress,
So that I can maintain document quality without direct database or Weaviate access.

**Acceptance Criteria:**

**Given** an admin navigates to Document Management
**When** the document list loads
**Then** all ingested documents shown with: name, upload date, department, classification, chunk count, status (indexed/processing/failed/partial_failed), last modified

**Given** an admin updates a document's metadata (e.g., `classification` from INTERNAL to CONFIDENTIAL)
**When** the change is saved
**Then** the update is applied atomically — either ALL Weaviate chunks for that document reflect the new metadata, OR ALL chunks retain the original metadata; partial state where some chunks have new classification and others have old classification MUST NOT persist beyond a 30-second recovery window; update is logged in audit with `user_id` and `timestamp`; no re-embedding required for metadata-only changes

**Given** an admin triggers a re-index operation on a large document
**When** the Celery re-index job runs
**Then** re-index is split into batches of 100 chunks dispatched as sub-tasks on queue `rag.reindex` (separate from `rag.document.sync_index`); the Admin UI polls `GET /admin/documents/{id}/reindex-status` every 5 seconds showing `{ status, progress_percent, processed_chunks, failed_chunks }`; on partial failure, status is `PARTIAL_FAILED` and admin can retry only failed batches

**Given** an admin deletes a document
**When** deletion is confirmed
**Then** all Weaviate chunks are removed; PostgreSQL document record is soft-deleted (not hard delete) for audit trail; deletion is irreversible from UI (hard delete requires DB access); deletion is logged

**And** all admin operations logged in `audit_events`; operations require `roles=["data_owner", "admin"]`; `ReindexJob` table tracks `total_chunks`, `processed_chunks`, `failed_chunks`, `status` in PostgreSQL

---

## Epic 4: Protected Access for Sensitive Data

**Goal:** HR users can query employee data with full PII masking; Approval Officers review sensitive queries within SLA; column-level security enforces data boundaries.

**Done When:** Full ABAC active; Presidio PII masking integrated with async threshold; approval workflow gates sensitivity_tier ≥ 2; ConfidenceBreakdownCard + ExportConfirmationBar + PermissionRequestState built in `packages/ui`.

**Sprint boundary:** Sprint A: Stories 4.1 + 4.2 (infra); Sprint B: Stories 4.3 + 4.4 + 4.5 (features).

---

### Story 4.1: Full ABAC Extension (FR-A2 Full)

As a security engineer,
I want Cerbos policies extended with region and approval_authority attributes without breaking existing Epic 2A policies,
So that access decisions reflect complete organizational context.

**Acceptance Criteria:**

**Given** Epic 2A has frozen `principal.attr` with `department`, `clearance`
**When** Epic 4 extends Cerbos policies
**Then** `region` and `approval_authority` are ADDED; `department` and `clearance` are NOT renamed, removed, or retyped; all Epic 2A policy unit tests continue passing without modification

**Given** a Finance user in `region="north"` queries data tagged `region="south"`
**When** Cerbos evaluates the attribute-based policy
**Then** DENY with `denial_reason="region_mismatch"`; logged with full principal context

**Given** a user with `approval_authority=True` queries sensitivity_tier=2 data
**When** Cerbos evaluates
**Then** pre-authorization granted without entering approval queue; users without `approval_authority` still trigger approval gate

**And** ADR confirming attribute extension (not redefinition) updated before merge; `cerbos compile ./policies` passes in CI

---

### Story 4.2: Column-level Security (FR-A4)

As a business user,
I want sensitive columns automatically masked or excluded based on my clearance level,
So that I never accidentally access unauthorized data even in correctly-structured queries.

**Acceptance Criteria:**

**Given** the column clearance mapping:

| Column Tag | Clearance Required | User Clearance | Behavior |
|------------|-------------------|----------------|---------|
| PUBLIC / untagged | 0 | any | Full value returned |
| CONFIDENTIAL | ≥ 2 | < 2 | Value replaced with `***` |
| CONFIDENTIAL | ≥ 2 | ≥ 2 | Full value returned |
| SECRET | ≥ 3 | < 3 | Column entirely excluded (name AND value absent) |
| SECRET | ≥ 3 | ≥ 3 | Full value returned |

**When** Oracle Connector processes the structured column result
**Then** masking/exclusion is applied according to the table above; untagged columns default to PUBLIC (no restriction)

**Given** column masking is applied in Oracle Connector for a STRUCTURED column (typed: ID, phone, salary)
**When** Presidio middleware runs on the same result
**Then** Presidio SKIPS that column (determined by `is_free_text=False` flag in `ColumnResult`); Presidio only scans FREE_TEXT columns (comments, notes, descriptions) — no overlap

**Given** a user sees a masked `***` field
**When** they click the lock icon `🔒`
**Then** `PermissionRequestState` opens with: what is blocked and why, what is accessible, CTA "Yêu cầu quyền truy cập"

**And** column sensitivity tags stored in Semantic Layer metadata catalog; masking enforced in Oracle Connector result processing layer — NOT in frontend; column masking is audited per query (field name + masking applied, not the masked value)

---

### Story 4.3: PII Masking with Presidio (FR-A5)

As a compliance officer,
I want all query results scanned for PII before reaching users, with async processing for large result sets and clearance-threshold-based bypass for authorized HR staff,
So that PDPA compliance is maintained without degrading performance.

**Acceptance Criteria:**

**Given** a query result with `rows × sensitive_columns ≤ 10,000 cells`
**When** Presidio middleware runs inline (synchronous)
**Then** entities `PERSON`, `ID_CARD_VN`, `EMAIL`, `PHONE_NUMBER` are replaced: `<TÊN_ĐƯỢC_ẨN>`, `<CMND_ĐƯỢC_ẨN>`, `<EMAIL_ĐƯỢC_ẦN>`, `<SĐT_ĐƯỢC_ẨN>`; total scan time <200ms

**Given** a query result with `rows × sensitive_columns > 10,000 cells`
**When** Presidio runs
**Then** scan executes as async Celery job; client receives `{ "status": "pending", "scan_id": "<uuid>" }` immediately; polls `GET /v1/scan/{scan_id}/status` until complete; result delivered when scan done

**Given** a user with `clearance ≥ 3`
**When** Presidio evaluates
**Then** PII fields returned unmasked; if clearance is insufficient → PII is masked regardless; Cerbos validates the clearance threshold before Presidio bypass is granted

**Given** Presidio scans any response
**When** PII is detected and masked
**Then** audit log records ONLY: `{ "field_name": "PERSON", "masked_count": 3 }` — actual PII values are NEVER written to any log, memory store, or trace; this satisfies FR-A8 "comprehensive audit" which means: all access events logged with actor/timestamp/resource/operation; for PII fields, field metadata (name + count) is logged, actual values excluded

**And** `SanitizedLogger` wrapper used before emitting any Presidio metrics; Vietnamese-specific recognizers added for CMND (12-digit), Vietnamese phone patterns; Presidio hooks into `post_query_hook` — NOT `pre_execution_hook`; Presidio scans ALL responses (SQL, RAG, hybrid, forecast)

---

### Story 4.4: Query Approval Workflow (FR-A7)

As a Finance Analyst,
I want to submit sensitive queries that route to an Approval Officer with a clear briefing card and defined SLA,
So that I can access sensitive data through a governed, auditable process.

**Acceptance Criteria:**

**Given** a query is classified with `sensitivity_tier ≥ 2`
**When** the orchestrator processes the request
**Then** query enters `ApprovalRequested` state; analyst receives "Câu hỏi này đang chờ phê duyệt"; notification sent to users with `approval_authority=True` via email + Admin Portal badge; system stores `QueryIntent` (structured object with intent type, filters, sensitivity_tier) — NOT raw SQL string

**Given** Hùng reviews the ApprovalBriefingCard
**When** he opens the approval queue item
**Then** the card shows exactly these 5 elements: (1) requester identity + department + recent query history, (2) business justification from query intent analysis, (3) data scope + sensitivity_tier + estimated row count, (4) anomaly risk signal (unusual time/volume pattern), (5) one-click escalation button; card renders completely in <500ms; all 5 elements verifiable by component test

**Given** the SLA timer runs
**When** query is not acted upon within 4 hours
**Then** query transitions to `Expired`; BOTH analyst and approver receive expiry notification; `EXPIRED` does NOT auto-resubmit — analyst must explicitly resubmit; resubmit creates a NEW `QueryIntent` with new approval cycle (any param change = new approval)

**Given** Hùng approves or rejects
**When** decision is saved
**Then** approval stores `(user_id, query_fingerprint, sensitivity_tier, decision, reason)`; approval executes the stored `QueryIntent` — no user-modified SQL is accepted; lifecycle is fully logged: `ApprovalRequested → PendingReview → Approved/Rejected/Expired`

**And** `ApprovalBriefingCard` built in this story; approval does NOT interrupt other users' query flows

---

### Story 4.5: Trust & Permission UI Components

As a developer,
I want three reusable UI components (ConfidenceBreakdownCard, ExportConfirmationBar, PermissionRequestState) published to `packages/ui`,
So that Epic 4 can render trust signals and Epic 6 + Epic 7 can consume them without rebuilding.

**Acceptance Criteria:**

**Given** a query produces low-confidence results (cross-source discrepancy, partial data, or stale data)
**When** `ConfidenceBreakdownCard` renders
**Then** it shows one of 5 named states: `low-confidence`, `partial-data`, `stale-data`, `permission-limited`, `cross-source-conflict`; each state has plain-Vietnamese explanation + exactly 3 exit actions; status is indicated by BOTH color AND text label (not color-only); Epic 7 CONSUMES this component from `packages/ui` passing `{ type: "forecast-uncertainty" }` — no rebuild

**Given** a user triggers an export action
**When** `ExportConfirmationBar` renders
**Then** sticky bottom bar (NOT modal) shows: file format, estimated row count, sensitivity warning if applicable; "Xác nhận xuất" requires Human-in-the-Loop Signature checkbox "Tôi đã xem xét và xác nhận dữ liệu này"; auto-dismisses after 30 seconds with cancel default; **ExportConfirmationBar component interface contract is frozen before this story begins and Epic 6 team has reviewed and signed off**; Epic 6 CONSUMES — no rebuild

**Given** a user encounters a permission denial
**When** `PermissionRequestState` renders
**Then** shows: what is blocked (plain Vietnamese), what user CAN access, primary CTA "Yêu cầu quyền truy cập" → IT Admin queue, secondary CTA "Xem dữ liệu khả dụng" → re-run with available scope

**And** all 3 components shared state verified before treating as single story: PermissionRequestState state influences ExportConfirmationBar disabled state → shared context → 1 story is correct; all 3 published to `packages/ui/src/components/custom/`; UX-DR12 + UX-DR15 + UX-DR17 coverage complete

---

## Epic 5A: IT Admin Control Center

**Goal:** IT Admin can onboard departments, configure data sources, manage users/roles, and monitor system health without manual Oracle configuration.

**Done When:** FR-AD2-AD5 verified; admin shell functional; Lan can configure a new department end-to-end without engineering support.

---

### Story 5A.1: User & Role Management (FR-AD2)

As an IT Admin,
I want to create, update, and delete users and role assignments with LDAP synchronization,
So that user access reflects the current organizational structure without manual DB operations.

**Acceptance Criteria:**

**Given** Lan creates a new role `finance_analyst` and assigns schema `FINANCE_ANALYTICS`
**When** the role is saved
**Then** the role is created in Cerbos policy store; schema allowlist is persisted in data source config; assigned users inherit the role on next login; the operation is logged in `audit_events` with Lan's `user_id` and timestamp

**Given** a user's LDAP group changes (e.g., moved from Sales to Finance)
**When** the LDAP sync runs (configurable interval, default: 15 minutes)
**Then** the user's Keycloak claims are updated; Cerbos principal context reflects new department on next query; no manual action required from IT Admin

**Given** Lan deletes a user account
**When** deletion is confirmed
**Then** user's active sessions are invalidated (Keycloak session revoked); audit record is created; user's historical audit entries are preserved (not deleted); soft-delete in user table for 90-day retention

**And** CRUD operations require `roles=["admin"]`; bulk import via CSV with preview + validation before commit; sync status visible on dashboard

---

### Story 5A.2: Data Source Configuration (FR-AD3)

As an IT Admin,
I want to configure Oracle database connections, schema allowlists, query timeouts, and row limits through the Admin Portal,
So that I can control what data each department can access without editing config files or restarting services.

**Acceptance Criteria:**

**Given** Lan adds a new Oracle data source with host, port, service name, and schema allowlist
**When** the configuration is saved
**Then** the data source is registered in `DataSourceRegistry`; a connection test is run automatically (timeout 5 seconds); credentials are stored in Vault — NEVER displayed in UI after initial entry; configuration is logged in audit without credential values

**Given** Lan updates the row limit for a data source from 50,000 to 10,000
**When** the change is saved
**Then** the new limit takes effect on the NEXT query (no restart required); currently-running queries complete with old limit; change logged with `previous_value`, `new_value`, `changed_by`

**Given** the connection test fails
**When** Lan saves the configuration
**Then** save is still allowed with a warning "Kết nối thất bại — kiểm tra thông tin trước khi dùng"; the data source is marked `status=UNVERIFIED`; queries against an `UNVERIFIED` source return an informational warning to users

**And** Oracle connection credentials injected at runtime from Vault; no credentials in environment variables or config files; timeout and row limit editable without service restart; schema allowlist validated against actual Oracle schemas on test connection

---

### Story 5A.3: Audit Dashboard (FR-AD4)

As an IT Admin,
I want to search and filter audit logs by user, time range, action, data source, and policy decision,
So that I can investigate anomalies and fulfill compliance requests quickly.

**Acceptance Criteria:**

**Given** Lan searches audit logs with filters: `user_id="hoa@company.com"`, `date_range=last_7_days`, `action="query"`
**When** the search executes
**Then** results return in <3 seconds; each result shows: timestamp, user, intent type, data sources, policy decision, rows returned (not raw data); results are paginated (50 per page)

**Given** Lan searches for a specific `request_id`
**When** the result is found
**Then** full lifecycle is displayed: every state transition with timestamp; if the query was denied, shows the denial reason and Cerbos rule triggered

**Given** audit log results are shown
**When** Lan exports to CSV
**Then** export completes within 60 seconds for date ranges up to 90 days; CSV contains same fields as UI (no additional PII or raw data); export action itself is logged in audit

**And** audit log is read-only in Admin UI (no edit/delete); retention is ≥12 months; audit data sourced from PostgreSQL `audit_events` table (append-only)

---

### Story 5A.4: System Health Dashboard (FR-AD5)

As an IT Admin,
I want a real-time dashboard showing system health metrics, latency, error rates, and active alerts,
So that I can identify and respond to system issues before users are impacted.

**Acceptance Criteria:**

**Given** Lan opens the System Health Dashboard
**When** the page loads
**Then** metrics panels show: P50/P95 query latency per mode (sql/rag/hybrid/forecast), cache hit ratio, error rate %, token cost per day, active Oracle connections, Weaviate index status; metrics refresh every 30 seconds

**Given** P95 latency exceeds the configured SLO threshold
**When** the alert fires
**Then** an alert banner appears on the dashboard within 2 minutes of threshold crossing; alert shows: metric name, current value, threshold, affected service; dismissable after acknowledgment; alert is also logged in `audit_events`

**Given** Lan wants historical performance trends
**When** they change the time range picker to "Last 7 days"
**Then** Grafana-sourced charts load within 5 seconds; P50/P95 percentiles visible for the selected period; no data older than 12 months is retained

**And** dashboard powered by Prometheus/Grafana via embedded iframe or Grafana API; no raw log data shown; rate limit alerts configurable per user/department by IT Admin

---

## Epic 5B: Data Governance & KPI Management

**Goal:** Data Owners can manage KPI definitions with versioning and rollback; users benefit from persistent cross-session memory; advanced memory features preserve context intelligently.

**Done When:** FR-AD1 (KPI versioning), FR-S2 (management UI), FR-M2-M7 (full memory stack) verified.

---

### Story 5B.1: Semantic Layer & KPI Management UI (FR-AD1 + FR-S2)

As a Data Owner,
I want to manage KPI metric definitions with version history, diff view, and one-click rollback through the Admin Portal,
So that business term changes are controlled, audited, and reversible.

**Acceptance Criteria:**

**Given** Nam updates the formula for "doanh thu thuần"
**When** the new version is published
**Then** a new version entry is created with `version_id`, `changed_by`, `timestamp`, `previous_formula`, `new_formula`; all caches referencing the metric are invalidated within 60 seconds; subsequent queries use the new formula

**Given** Nam views two versions of a metric
**When** the diff view opens
**Then** side-by-side comparison shows formula changes highlighted (added: green, removed: red); no merge required — versions are immutable snapshots

**Given** Nam rollbacks to a previous version
**When** rollback is confirmed
**Then** the previous version becomes the active definition; a new version entry is created recording the rollback action; cache invalidation triggered; rollback is logged with reason (optional free text)

**And** management UI extends the API from Story 2A.2 (Semantic Layer bootstrap); Epic 5B adds management CRUD without breaking the read-only API; only users with `roles=["data_owner", "admin"]` can publish/rollback

---

### Story 5B.2: Medium-term Memory (FR-M2)

As a business user,
I want the system to remember a summary of my recent conversations across sessions,
So that I can pick up where I left off without repeating context.

**Acceptance Criteria:**

**Given** a user's session ends (logout or TTL expiry)
**When** the session summarizer runs
**Then** a compressed summary of the session is stored in PostgreSQL `conversation_memory` table tagged with `user_id`, `department_id`, `session_id`, `sensitivity_level`, `created_at`, `expires_at`; raw Oracle data values are NEVER stored in the summary — only business intent, topic, and filter context

**Given** a user opens a new session
**When** the orchestrator loads context
**Then** summaries from the last 30 sessions are retrieved; only summaries with `sensitivity_level` ≤ user's current clearance are included; cross-user memory access is impossible (RLS on `conversation_memory` table)

**Given** session summaries are retrieved
**When** they are injected into LangGraph context
**Then** token usage increases <20% compared to sessions without medium-term memory (measured via Langfuse); irrelevant summaries are excluded via semantic similarity score (cosine > 0.7 threshold)

**And** `conversation_memory` table has PostgreSQL RLS policy preventing cross-user reads; summaries expire after configurable period (default: 90 days); PDPA: no PII in summaries

---

### Story 5B.3: Long-term Preference Memory (FR-M3)

As a business user,
I want the system to remember my frequently used KPIs, report templates, and query patterns across all sessions,
So that the system proactively surfaces what I need most.

**Acceptance Criteria:**

**Given** a user has completed ≥5 sessions
**When** they open a new session
**Then** the Chat UI displays top 3 most-used KPIs/reports from the last 30 days as suggested queries (not blocking the input); suggestions are role-appropriate and within the user's permitted data scope

**Given** a user marks a query result as "Lưu mẫu báo cáo"
**When** the template is saved
**Then** it appears in their saved templates list; template includes: query intent, filters, time range, output format preference; templates are private to the user (not shared by default)

**And** preference data stored in PostgreSQL `user_preferences` table; no raw Oracle data stored; preference learning is opt-out (user can disable in settings); NFR-CM1 token cost tracking per session applies to preference-loaded sessions

---

### Story 5B.4: Memory Isolation + Selective Injection (FR-M4 + FR-M5)

As a security engineer,
I want user memory to be strictly isolated and selectively injected into context without privilege escalation,
So that no user can access another user's memory and context injection remains token-efficient.

**Acceptance Criteria:**

**Given** two users (User A and User B) in the same department
**When** User B's LangGraph invocation runs
**Then** User B has ZERO access to User A's session summaries, preferences, or saved templates; verified by: `conversation_memory` PostgreSQL RLS policy, and `user_preferences` table RLS policy; unit test attempts cross-user memory read and asserts zero results

**Given** a session with 15 turns of conversation history
**When** LangGraph injects context for turn 16
**Then** token usage for turn 16 is <20% higher than turn 1 (memory compaction active); selective recall uses semantic similarity — only summaries with cosine >0.7 to current query are injected; full history replay is never used

**And** memory compaction runs as Celery task after every 10 turns; `fakeredis` for unit tests; testcontainers Redis for integration; after session TTL expiry: graceful "session expired" message returned, no stale data access

---

### Story 5B.5: Conversation History Search (FR-M6 + FR-M7)

As a business user,
I want to search my conversation history by keyword, time range, and topic,
So that I can find a previous analysis without remembering the exact query I used.

**Acceptance Criteria:**

**Given** a user searches their history with "doanh thu tháng 3"
**When** the search executes
**Then** results return in <2 seconds; results show: query date, intent type, key result summary (not raw data); results are scoped strictly to the requesting user's history

**Given** a user views a historical conversation
**When** they click "Dùng lại câu hỏi này"
**Then** the query intent (filters, topic, time range) is pre-loaded into the chat input; user can modify before submitting; no raw Oracle data from the original result is cached or re-used

**Given** any memory or history entry was created
**When** it is inspected
**Then** it contains ZERO raw Oracle data values (no salary numbers, no margin %, no PII); only business intent metadata, topic tags, and filter descriptions; this is verified by automated memory audit test on every push

---

## Epic 6: Automated Reporting & Cross-domain Analysis

**Goal:** Finance users get scheduled reports automatically; users query across Finance + Budget domains; popular queries return instantly from cache.

**Done When:** FR-E1-E4 (export complete), FR-S5 (cross-domain verified), FR-S6 (cache >40% hit rate) all met.

---

### Story 6.0: Cross-domain Decomposition Spike (FR-S5 Research)

As a developer,
I want a documented decomposition architecture for cross-domain queries before production implementation,
So that Epic 6 Story 6.4 implementation is unambiguous and architecturally sound.

**Acceptance Criteria:**

**Given** this is a research spike (runs during Epic 2B timeline)
**When** the spike is complete
**Then** it delivers: (1) `QueryDecompositionState` TypedDict definition, (2) horizontal vs vertical decomposition strategy documentation with examples, (3) RRF merge strategy for cross-domain results, (4) stub code for `decompose_query_node` and `merge_domain_results_node`, (5) ADR documenting the chosen approach

**And** spike output is a document + stub code only — NO production traffic; spike runs parallel to Epic 2B; implementation (Story 6.4) begins only after Epic 2B is complete; referenced in implementation-artifacts/6-0-cross-domain-decomposition-spike.md

---

### Story 6.1: Export Results (FR-E1 + FR-E4)

As a business user,
I want to export query results to Excel, PDF, or CSV with an async job that doesn't block my conversation,
So that I can share insights without leaving the chat interface.

**Acceptance Criteria:**

**Given** a user clicks "Generate Report" after receiving a query result
**When** `ExportConfirmationBar` (from Epic 4) renders
**Then** shows: file format, estimated row count, sensitivity warning; requires Human-in-the-Loop Signature checkbox before confirm; auto-dismisses after 30 seconds with cancel default

**Given** the user confirms export
**When** the Celery task `export.report.generate_excel` is dispatched
**Then** user immediately receives `{ "job_id": "<uuid>", "status": "queued" }`; user can continue chatting; when done: toast "Báo cáo đã sẵn sàng ↗ Tải xuống"; export file contains only data within user's permitted scope — no data from other departments

**Given** export completes
**When** the audit entry is written
**Then** `audit_events` records: `user_id`, `job_id`, `format`, `row_count`, `department_scope`, `sensitivity_tier`, `recipient` (if shared), `timestamp`; raw exported data is NOT stored in audit — only metadata

**And** Celery task `acks_late=True`, `reject_on_worker_lost=True`; export jobs on queue `export-jobs` (separate from chat path); file format support: Excel (.xlsx), PDF, CSV; download link valid for 24 hours then expires

---

### Story 6.2: Scheduled Reports (FR-E2 + FR-E3)

As a Finance user,
I want to schedule recurring reports that are automatically generated and delivered to my inbox,
So that I receive regular data updates without manual re-querying.

**Acceptance Criteria:**

**Given** Tuấn configures a weekly Finance report (every Monday 08:00)
**When** the scheduled time arrives
**Then** Celery Beat triggers `export.report.generate_scheduled`; report is generated with the same access controls as a live query; delivered to Tuấn's email; `audit_events` records every scheduled delivery with timestamp and recipient

**Given** a scheduled report contains sensitivity_tier ≥ 2 data
**When** the schedule is created
**Then** the schedule requires approval from an Approval Officer before it can be activated; one-time approval covers all future scheduled deliveries of that template; re-approval required if report scope changes

**Given** a scheduled report delivery fails (email delivery failure)
**When** the failure is detected
**Then** retry 3 times with exponential backoff; after 3 failures: notify IT Admin + log failure in audit; user receives "Báo cáo tuần này gặp sự cố — liên hệ IT" notification

**And** scheduled reports use same ExportConfirmationBar audit trail per delivery; recipients validated against authorized user list — no reports sent to external addresses; Celery Beat configuration stored in `infra/docker-compose.dev.yml`

---

### Story 6.3: Semantic Result Cache (FR-S6)

As a platform engineer,
I want frequently-asked queries to be served from cache with semantic similarity matching,
So that repeated or similar queries return instantly instead of re-executing Oracle queries.

**Acceptance Criteria:**

**Given** user A asks "Doanh thu Q1 2026 theo chi nhánh?"
**When** the response is cached with key = hash(`normalized_intent + role_scope + department`)
**Then** user B from the same department asking "Cho tôi xem doanh thu Q1 2026 chia theo chi nhánh?" retrieves the cache hit (semantic similarity >0.85); response latency <300ms for cache hits

**Given** a cache hit is returned
**When** the response is delivered
**Then** a `🟡 Kết quả từ cache — cập nhật lúc [timestamp]` freshness indicator is displayed; user can force refresh with "Tải lại dữ liệu mới" button; force refresh invalidates cache entry for that query

**Given** user's permissions change (role revoked, department changed)
**When** the permission change event is processed
**Then** ALL cache entries for that user are invalidated within 60 seconds; TOCTOU risk: permission check happens at query time before cache lookup — not vice versa

**And** cache keys include: `department_id`, `role_scope`, `semantic_layer_version`, `data_freshness_class`; cache stored in Redis with TTL from ADR-002 (SQL: 5 min, RAG: 60 min); cache hit rate target: >40% after 2 weeks steady-state; cache hit rate tracked in Grafana

---

### Story 6.4: Cross-domain Query Execution (FR-S5)

As a Finance user,
I want to query data across Finance and Budget domains in a single natural language question,
So that I get a unified answer without submitting two separate queries and manually joining the results.

**Acceptance Criteria:**

**Given** Tuấn asks "Chi phí vận hành Q1 so với ngân sách được duyệt?"
**When** the orchestrator detects a cross-domain query (FINANCE + BUDGET)
**Then** it applies the decomposition strategy from Story 6.0 spike; two sub-queries execute against their respective Oracle sources; results are merged at application layer using canonical business key (`department_code`, `period_key`); a single unified answer is returned

**Given** cross-domain merge produces a data discrepancy (FINANCE says 5.2B, BUDGET says 4.9B)
**When** the discrepancy is detected
**Then** `ConfidenceBreakdownCard` with state `cross-source-conflict` is shown; both source values are displayed; user is offered: "Xem chi tiết nguồn lệch" (opens ProvenanceDrawer showing both sources), "Loại trừ một nguồn" (re-query with single source), "Tạo ticket cho Data Owner"

**And** cross-domain queries route through decomposition orchestrator only AFTER Epic 2B is complete (Story 6.0 spike validated); each sub-query is independently policy-checked; NFR-P1 cross-domain P50<8s/P95<20s; sub-query results independently audited

---

## Epic 7: Forecasting & Predictive Intelligence

**Goal:** Analysts request time-series forecasts, anomaly detection, and trend analysis in natural language with explainable business-readable results.

**Done When:** FR-F1-F6 all verified; ConfidenceBreakdownCard consumed from Epic 4 for uncertainty visualization.

---

### Story 7.1: Time-series Forecasting (FR-F1)

As a Finance analyst,
I want to request a revenue or cost forecast for the next quarter in natural language and receive results with confidence intervals,
So that I can plan budgets based on data-driven predictions with clear uncertainty bounds.

**Acceptance Criteria:**

**Given** Tuấn asks "Dự báo doanh thu Q3 2026 theo kênh phân phối"
**When** the forecast job runs
**Then** Nixtla TimeGPT generates forecasts for each channel; results include point forecast + 80% and 95% confidence intervals; MAPE on validation holdout set is <15%

**Given** the forecast result is returned
**When** rendered in the UI
**Then** time-series chart shows: historical data (solid line), forecast period (dashed line), confidence band (shaded area); `ConfidenceBreakdownCard` from Epic 4 is consumed with `{ type: "forecast-uncertainty" }` — NOT rebuilt; chart built with Recharts + `useChartTheme()` hook

**Given** the forecast job is submitted
**When** Celery task `forecast.time_series.generate_report` is dispatched
**Then** job_id returned immediately; user can continue chatting; `ExportJobStatus` (from Epic 4) shows progress; when complete: toast notification + download option

**And** Celery task: `acks_late=True`, `reject_on_worker_lost=True`; queue: `forecast-batch`; Nixtla API key stored in Vault; if Nixtla unavailable: fallback to `statsmodels` Prophet; forecast inputs are governed by same ABAC as query path

---

### Story 7.2: Anomaly Detection & Alerts (FR-F2)

As a Sales manager,
I want to be automatically alerted when metrics show unusual patterns,
So that I can investigate anomalies before they become problems.

**Acceptance Criteria:**

**Given** anomaly detection runs on order volume time-series
**When** an anomaly is detected (Isolation Forest score below threshold)
**Then** alert fires within 1 hour of the data being available; alert includes: metric name, anomaly timestamp, deviation from expected range, severity (low/medium/high); false positive rate is <10% measured over 30-day rolling window

**Given** Hoa receives an anomaly alert
**When** she opens the alert
**Then** she sees: (1) the time-series chart with anomaly highlighted in red, (2) natural language explanation "Đơn hàng khu vực HCM ngày 15/3 thấp hơn 40% so với dự kiến", (3) 3 suggested next actions; `ConfidenceBreakdownCard` from Epic 4 consumed for uncertainty visualization

**And** anomaly alerts routed only to users with access to the affected data domain (Cerbos policy check); alert history stored in PostgreSQL; user can acknowledge/dismiss alerts; dismissed alerts still visible in history

---

### Story 7.3: Trend Analysis (FR-F3)

As a business analyst,
I want to compare metrics across time periods (YoY, MoM, QoQ) with plain-language explanations,
So that I can understand business trends without statistical expertise.

**Acceptance Criteria:**

**Given** Minh asks "Doanh thu Q1 2026 so với Q1 2025 thay đổi thế nào?"
**When** trend analysis runs
**Then** result shows: percentage change, absolute change, direction (tăng/giảm); explanation uses ZERO ML/statistical jargon; acceptable: "Tăng 12% so với cùng kỳ năm ngoái"; not acceptable: "Positive YoY delta of 12% with p-value 0.03"

**Given** the trend explanation is generated
**When** user acceptance test runs
**Then** 3 non-technical reviewers (HR, Sales, Finance personas) independently rate explanation clarity ≥4/5 on the "no jargon" rubric; this is a manual UAT gate before story is closed

**And** trend analysis uses statsmodels for computation; results cached per FR-S6 rules; drill-down by department/product/region available within user's permitted scope (FR-F4)

---

### Story 7.4: Drill-down Analytics + Result Explainability (FR-F4 + FR-F5)

As a business analyst,
I want to drill down into forecast and trend results by department, product, region, or channel, with top contributing factors explained in plain language,
So that I can understand what drives the numbers without statistical expertise.

**Acceptance Criteria:**

**Given** a forecast result for total revenue
**When** user clicks "Phân tích chi tiết theo khu vực"
**Then** chart updates to show regional breakdown; only regions the user is authorized to see are shown (Cerbos policy enforced); drill-down respects the same data scope as the original query

**Given** the explainability engine runs
**When** results are returned
**Then** top 3 contributing factors are shown in plain Vietnamese: "Yếu tố 1: Mùa vụ (đóng góp 45%)", "Yếu tố 2: Xu hướng thị trường (đóng góp 30%)", "Yếu tố 3: Chiến dịch marketing (đóng góp 15%)"; confidence level stated as: "có khả năng tăng" / "khả năng cao giảm" / "không rõ xu hướng" — NOT raw probability values

**And** SHAP feature importance used internally; business-friendly labels mapped from SHAP output; if SHAP is unavailable: show "Giải thích chi tiết đang được xử lý" with async job fallback

---

### Story 7.5: Async Forecast Jobs (FR-F6)

As a platform engineer,
I want heavy forecasting jobs to run asynchronously on dedicated workers without blocking the chat path,
So that users can continue chatting while bulk forecasts compute.

**Acceptance Criteria:**

**Given** a forecast request with large date range (e.g., 2-year forecast, 50 SKUs)
**When** the job is classified as "heavy" (estimated >10 seconds)
**Then** `POST /v1/forecast/run` returns `{ "job_id": "<uuid>", "status": "queued" }` within 500ms; `ExportJobStatus` component (from Epic 4) shows progress in chat thread; user can continue chatting

**Given** the forecast job completes
**When** results are ready
**Then** user receives toast notification; results available at `GET /v1/forecast/{job_id}/result`; results cached for 60 minutes; if user navigates away and returns within 60 minutes, result is immediately available

**Given** the forecast Celery worker is overwhelmed (queue depth >20 jobs)
**When** a new forecast is submitted
**Then** user receives estimated wait time: "Kết quả dự kiến sau 15 phút"; no silent timeout; after 30 minutes, job marked `FAILED` with `"reason": "queue_timeout"`; user notified to retry

**And** Celery tasks on dedicated `forecast-batch` queue (separate from `chat-low-latency`); `acks_late=True`, `reject_on_worker_lost=True`; Nixtla timeout 120 seconds per forecast unit; forecast access governed by ABAC (same as query path)
