# Story 7.5: Async Forecast Jobs (FR-F6)

Status: review

## Story

As a delivery team member,
I want to deliver **Async Forecast Jobs (FR-F6)** with measurable acceptance checks,
so that Epic 7 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **7.5 - Async Forecast Jobs (FR-F6)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 7 (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
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

- Epic context: **Epic 7 — Forecasting & Predictive Intelligence**.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/7-5-async-forecast-jobs.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 7.5
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

- `pytest tests/test_forecasting.py`
- `npm --prefix apps/chat test -- --run src/components/epic7/ForecastStudio.test.tsx`
- `pytest` (unrelated existing failure in `tests/test_langgraph_stub_graph.py`)
- `npm --prefix apps/chat test -- --run` (unrelated existing failures in `src/test/designTokens.test.ts` and `src/components/epic5b/Epic5BWorkspace.test.tsx`)

### Completion Notes List

- Reused the Story 7.1 forecast route as the async execution surface for heavy forecasting jobs.
- Added immediate `job_id` response, dedicated `forecast-batch` queue metadata, ETA messaging, 60-minute cached result window, and 30-minute queue-timeout guard.
- Added client-side resume of the latest forecast job via session storage so users can leave and return without losing the in-flight/result handle.
- Closed the remaining overload gap by returning the explicit 15-minute ETA once forecast queue depth exceeds 20 jobs, matching the story acceptance text.
- Added queue-timeout retry messaging in Forecast Studio so failed async jobs surface a clear recovery path instead of a raw backend error code.
- Verified Story 7.5 directly with backend and frontend tests; broader repo regressions still exist outside forecast scope and were not introduced by this change.

### File List

- services/orchestration/forecasting/service.py
- services/orchestration/routes/forecast.py
- apps/chat/src/components/epic7/ForecastStudio.tsx
- apps/chat/src/components/epic7/ForecastStudio.test.tsx
- packages/ui/src/components/ExportJobStatus.tsx
- packages/ui/src/components/index.ts
- packages/ui/package.json
- apps/chat/vite.config.ts
- apps/chat/vitest.config.ts
- tests/test_forecasting.py

### Change Log

- 2026-05-03: Closed Story 7.5 overload coverage and queue-timeout UX messaging; validated targeted backend and frontend forecast flows.
