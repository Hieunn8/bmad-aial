# Story 1.9: E2E Walking Skeleton Gate

Status: review

## Story

As a delivery team member,
I want to deliver **E2E Walking Skeleton Gate** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **1.9 - E2E Walking Skeleton Gate** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
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

### Review Findings

- [x] [Review][Patch] `_wait_for_tempo_trace` propagates 5xx và trả sớm khi resourceSpans rỗng [tests/test_e2e_walking_skeleton.py:64-79] — fixed
- [x] [Review][Patch] `analyst_jwt` module-scope → expired token gây opaque failures [tests/test_e2e_walking_skeleton.py:100] — fixed
- [x] [Review][Patch] `_get_keycloak_jwt` không guard `access_token` absent → opaque KeyError [tests/test_e2e_walking_skeleton.py:58-61] — fixed
- [x] [Review][Patch] `_extract_service_names` fallback `val.get("value")` trả dict cho OTLP complex types [tests/test_e2e_walking_skeleton.py:89] — fixed
- [x] [Review][Defer] Kong 401 body format unverified qua Kong proxy — cần Kong plugin, deferred, pre-existing
- [x] [Review][Defer] RequestValidationError envelope inconsistency — separate concern, deferred, pre-existing
- [x] [Review][Defer] ROPC grant deprecation — OK với Keycloak 25.0, deferred
- [x] [Review][Defer] `result["trace_id"]` bare access trong query.py — pre-existing, deferred

## Dev Notes

- Epic context: **Epic 1 — Governed Infrastructure & Walking Skeleton**.
- Canonical source of truth: `_bmad-output/planning-artifacts/epics.md`.
- Keep implementation aligned with architecture/PRD constraints; avoid speculative scope.

### Technical Requirements

- Reuse existing patterns in the repo before introducing new abstractions.
- Validate boundary inputs and handle errors explicitly.
- Preserve naming and folder conventions to keep automation stable.

### Architecture Compliance

- Confirm alignment with `_bmad-output/planning-artifacts/architecture.md` before coding.
- Preserve API/data contracts unless the story explicitly requires a controlled change.

### File Structure Requirements

- Primary artifact file: `_bmad-output/implementation-artifacts/1-9-e2e-walking-skeleton-gate.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 1.9
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Đọc epics.md Story 1.9 để lấy ACs thực sự (5 AC cụ thể: happy path, Tempo trace, auth failure, PM demo, Kong degraded).
- Kiểm tra realm-export.json: client `aial-web` (public, directAccessGrantsEnabled), user `dev-user` (sales/1/user role).
- fastapi_deps.py raise HTTPException(401) — cần custom exception handler để trả `{"code": "AUTH_FAILED"}`.
- Tất cả 115 unit tests pass sau khi thêm exception handler; E2E tests skip đúng khi không có `AIAL_RUN_E2E_TESTS=1`.

### Completion Notes List

- Thêm `_http_exception_handler` vào orchestration app: mọi HTTP 401 trả về `{"code": "AUTH_FAILED"}` (AC3).
- Thêm 2 unit tests cho 401 format vào `test_orchestration_query.py` (RED → GREEN, pass).
- Tạo `tests/test_e2e_walking_skeleton.py` với 7 tests (5 skippable với env guard + 2 manual skip):
  - AC1: POST /v1/chat/query qua Kong → 200 trong 5s, answer non-empty, trace_id UUID.
  - AC2: Polling Grafana Tempo /api/traces/{trace_id} trong 30s, verify `orchestration` span hiện diện.
  - AC3: 3 tests — no auth, malformed JWT, direct app 401 với body `{"code": "AUTH_FAILED"}`.
  - AC4/AC5: Đánh dấu `pytest.mark.skip` với hướng dẫn manual verification.
- Thêm 2 markers mới vào pyproject.toml: `e2e_gate`, `walking_skeleton_gate`.
- Thêm `walking-skeleton-gate` Makefile target (AIAL_RUN_E2E_TESTS=1, -m walking_skeleton_gate, --timeout=60, -x).
- AC4 (PM demo) và AC5 (Kong offline) là UI-based, không automatable trong scope này — documented as manual gates.

### File List

- services/orchestration/main.py
- tests/test_orchestration_query.py
- tests/test_e2e_walking_skeleton.py
- pyproject.toml
- Makefile
- _bmad-output/implementation-artifacts/1-9-e2e-walking-skeleton-gate.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
