---
stepsCompleted: [1, 2]
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
- FR-A2: RBAC + ABAC Policy Engine → enforce đúng role + attributes (department, region, clearance, purpose)
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
