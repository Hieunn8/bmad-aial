# Story 6.1: Export Results (FR-E1 + FR-E4)

Status: review

## Story

As a delivery team member,
I want to deliver **Export Results (FR-E1 + FR-E4)** with measurable acceptance checks,
so that Epic 6 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **6.1 - Export Results (FR-E1 + FR-E4)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 6 (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
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

- Epic context: **Epic 6 — Automated Reporting & Cross-domain Analysis**.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/6-1-export-results.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 6.1
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added async export job flow on the orchestration service: preview, queue, status polling, and 24-hour download link.
- Export payloads are generated only from already-secured query rows captured after runtime masking/row-limit enforcement.
- Audit metadata is written for every completed export without persisting raw exported values.
- Added a lightweight export console in `apps/chat` that runs a query, streams rows, and consumes the export confirmation bar before dispatching the job.

### File List

- `services/orchestration/exporting/service.py`
- `services/orchestration/routes/exports.py`
- `services/orchestration/routes/query.py`
- `services/orchestration/main.py`
- `tests/test_export_results.py`
- `apps/chat/src/components/epic6/ExportResultsConsole.tsx`
- `apps/chat/src/components/epic6/ExportResultsConsole.test.tsx`
- `packages/ui/src/components/ExportConfirmationBar.tsx`
- `packages/ui/package.json`
- `packages/ui/tsconfig.json`
- `apps/chat/src/components/epic5b/Epic5BWorkspace.tsx`
- `apps/chat/src/components/AppLayout.tsx`
