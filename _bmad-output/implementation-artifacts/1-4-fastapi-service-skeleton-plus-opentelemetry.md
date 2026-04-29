# Story 1.4: FastAPI Service Skeleton + OpenTelemetry

Status: review

## Story

As a delivery team member,
I want to deliver **FastAPI Service Skeleton + OpenTelemetry** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **1.4 - FastAPI Service Skeleton + OpenTelemetry** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 1 (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
3. Thiết kế triển khai tuân thủ ràng buộc kiến trúc và security hiện có; không mở rộng scope ngoài story.
4. Có bộ kiểm chứng rõ ràng (unit/integration/e2e nếu áp dụng) để chứng minh AC pass.
5. Tài liệu Dev Notes nêu rõ dependencies, assumptions, và tiêu chí review/done.

## Tasks / Subtasks

- [x] Chốt phạm vi và dependency của story từ epics/architecture.
- [x] Thiết kế thay đổi ở mức interface + data contract cho story này.
- [x] Triển khai theo TDD (RED → GREEN) với test cases map trực tiếp AC.
- [x] Bổ sung observability/security checks theo vùng tác động.
- [x] Tổng hợp evidence để chuyển trạng thái sang review/done.

## Dev Notes

- Epic context: **Epic 1 — Governed Infrastructure & Walking Skeleton**.
- Canonical source of truth: `_bmad-output/planning-artifacts/epics.md`.
- Keep implementation aligned with architecture/PRD constraints; avoid speculative scope.
- Orchestration service binds to port 8090 on host — matches Kong upstream from Story 1.3.

### Technical Requirements

- Reuse existing patterns in the repo before introducing new abstractions.
- Validate boundary inputs and handle errors explicitly.
- Preserve naming and folder conventions to keep automation stable.
- `setup_tracing(service_name)` must be called as first line in service `main.py` per architecture mandate.

### Architecture Compliance

- Confirm alignment with `_bmad-output/planning-artifacts/architecture.md` before coding.
- Preserve API/data contracts unless the story explicitly requires a controlled change.
- Embedding client contract locked at `BGE_MODEL_NAME="BAAI/bge-m3"`, `DIMS=1024` per ADR-003.

### File Structure Requirements

- Primary artifact file: `_bmad-output/implementation-artifacts/1-4-fastapi-service-skeleton-plus-opentelemetry.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 1.4
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

- `PYTHONPATH="shared/src;services;services/orchestration" python -m pytest tests/ -v` → 78 passed, 0 failed
- Health endpoint: `GET /health` → 200 `{"status": "healthy"}`
- Readiness endpoint: `GET /readiness` → 200 when postgres/redis/cerbos reachable, 503 when any down
- OpenTelemetry: TracerProvider created with service.name resource, spans with trace_id
- Embedding stub: `BGE_MODEL_NAME="BAAI/bge-m3"`, `DIMS=1024`, raises NotImplementedError

### Completion Notes List

- Created shared telemetry module: `shared/src/aial_shared/telemetry/tracer.py` — `setup_tracing(service_name)` configures TracerProvider with service.name resource, OTLP exporter (default endpoint `localhost:4317`, overridable via parameter), and optional console export. Called as first line in orchestration `main.py`.
- Created orchestration service skeleton: `services/orchestration/main.py` — FastAPI app with OpenTelemetry FastAPIInstrumentor, health router. Port 8090 matches Kong upstream.
- Created health/readiness endpoints: `GET /health` returns `{"status": "healthy"}` (HTTP 200). `GET /readiness` checks TCP connectivity to PostgreSQL (5432), Redis (6379), Cerbos (3592) — returns 200 with all checks or 503 with per-dep status.
- Created embedding client stub: `services/embedding/client.py` — `BGE_MODEL_NAME="BAAI/bge-m3"`, `DIMS=1024`. Immutable `EmbeddingResult` dataclass. `embed()` and `embed_batch()` raise NotImplementedError (Epic 2A implementation).
- 78 tests total — 6 health/readiness, 6 tracer (incl. OTLP default endpoint + exporter-always-attached), 9 embedding, 57 existing — all pass.

### File List

- shared/src/aial_shared/telemetry/__init__.py
- shared/src/aial_shared/telemetry/tracer.py
- services/orchestration/__init__.py
- services/orchestration/pyproject.toml
- services/orchestration/main.py
- services/orchestration/routes/__init__.py
- services/orchestration/routes/health.py
- services/embedding/__init__.py
- services/embedding/client.py
- tests/test_orchestration_health.py
- tests/test_telemetry_tracer.py
- tests/test_embedding_client.py

### Change Log

- 2026-04-29: Implemented Story 1.4 — FastAPI orchestration service skeleton with health/readiness endpoints, OpenTelemetry instrumentation, shared telemetry setup_tracing module, and embedding client stub (bge-m3/1024).
- 2026-04-29: Review fix — OTLP exporter now always attached with default endpoint `http://localhost:4317` (Tempo collector target). Spans are exported unconditionally; env var `OTEL_EXPORTER_OTLP_ENDPOINT` overrides the default. 2 new tests added (78 total).
