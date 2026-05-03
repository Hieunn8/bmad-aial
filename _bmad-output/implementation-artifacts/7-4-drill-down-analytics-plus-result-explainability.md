# Story 7.4: Drill-down Analytics + Result Explainability (FR-F4 + FR-F5)

Status: review

## Story

As a delivery team member,
I want to deliver **Drill-down Analytics + Result Explainability (FR-F4 + FR-F5)** with measurable acceptance checks,
so that Epic 7 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **7.4 - Drill-down Analytics + Result Explainability (FR-F4 + FR-F5)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/7-4-drill-down-analytics-plus-result-explainability.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 7.4
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added drill-down and explainability API flow for `department`, `product`, `region`, and `channel`.
- Enforced scoped regional drill-down using the caller's permitted region when present; department scope remains aligned with the authenticated principal.
- Returned top 3 contributing factors in plain Vietnamese with business-friendly confidence labels instead of raw probabilities.
- Added async explainability fallback path when SHAP is unavailable, with queued job handle and later result polling.
- Added UI panel for triggering drill-down analysis, rendering scoped chart breakdown, confidence label, and explainability factors or async fallback state.

### File List

- services/orchestration/explainability/service.py
- services/orchestration/routes/drilldown_explainability.py
- services/orchestration/main.py
- apps/chat/src/components/epic7/DrilldownExplainabilityPanel.tsx
- apps/chat/src/components/epic7/DrilldownExplainabilityPanel.test.tsx
- apps/chat/src/components/epic5b/Epic5BWorkspace.tsx
- tests/test_drilldown_explainability.py
