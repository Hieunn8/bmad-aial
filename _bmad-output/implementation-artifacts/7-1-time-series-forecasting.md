# Story 7.1: Time-series Forecasting (FR-F1)

Status: review

## Story

As a delivery team member,
I want to deliver **Time-series Forecasting (FR-F1)** with measurable acceptance checks,
so that Epic 7 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **7.1 - Time-series Forecasting (FR-F1)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 7 (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
3. Thiết kế triển khai tuân thủ ràng buộc kiến trúc và security hiện có; không mở rộng scope ngoài story.
4. Có bộ kiểm chứng rõ ràng (unit/integration/e2e nếu áp dụng) để chứng minh AC pass.
5. Tài liệu Dev Notes nêu rõ dependencies, assumptions, và tiêu chí review/done.

## Tasks / Subtasks

- [ ] Chốt phạm vi và dependency của story từ epics/architecture.
- [ ] Thiết kế thay đổi ở mức interface + data contract cho story này.
- [ ] Triển khai theo TDD (RED → GREEN) với test cases map trực tiếp AC.
- [ ] Bổ sung observability/security checks theo vùng tác động.
- [ ] Tổng hợp evidence để chuyển trạng thái sang review/done.

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

- Primary artifact file: `_bmad-output/implementation-artifacts/7-1-time-series-forecasting.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 7.1
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added authenticated forecast API endpoints: `POST /v1/forecast/run`, `GET /v1/forecast/{job_id}`, `GET /v1/forecast/{job_id}/result`, and `GET /v1/forecast/{job_id}/download`.
- Implemented async forecast job orchestration on dedicated `forecast-batch` queue contract with `acks_late=True` and `reject_on_worker_lost=True`.
- Forecast results now include provider selection (`nixtla-timegpt` or statsmodels fallback), MAPE, point forecast, and 80%/95% confidence intervals.
- Chat UI now renders forecast history vs forecast lines, confidence band, `ConfidenceBreakdownCard`, and shared job-status feedback with download link.
- Result cache window for completed forecast jobs is exposed to UI and resumable by job id within the client session.
- Verification passed with backend and frontend tests for forecast flow.

### File List

- services/orchestration/forecasting/__init__.py
- services/orchestration/forecasting/service.py
- services/orchestration/routes/forecast.py
- services/orchestration/main.py
- apps/chat/src/components/epic7/ForecastStudio.tsx
- apps/chat/src/components/epic7/ForecastStudio.test.tsx
- apps/chat/src/components/epic5b/Epic5BWorkspace.tsx
- apps/chat/vite.config.ts
- apps/chat/vitest.config.ts
- apps/chat/package.json
- apps/chat/package-lock.json
- packages/ui/src/components/ExportJobStatus.tsx
- packages/ui/src/components/index.ts
- packages/ui/package.json
- tests/test_forecasting.py
