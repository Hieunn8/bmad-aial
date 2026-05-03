# Story 5B.1: Semantic Layer & KPI Management UI (FR-AD1 + FR-S2)

Status: review

## Story

As a delivery team member,
I want to deliver **Semantic Layer & KPI Management UI (FR-AD1 + FR-S2)** with measurable acceptance checks,
so that Epic 5B can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **5B.1 - Semantic Layer & KPI Management UI (FR-AD1 + FR-S2)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 5B (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
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

- Epic context: **Epic 5B — Data Governance & KPI Management**.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/5b-1-semantic-layer-and-kpi-management-ui.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 5B.1
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added semantic layer version service with immutable KPI versions, active-version tracking, diff generation, rollback, and cache invalidation timestamps.
- Extended admin API with publish/list-version/diff/rollback endpoints guarded for `admin` and `data_owner`.
- Preserved the Story 2A.2 glossary read contract while switching reads to the active semantic definition.
- Wired semantic context into the live query path so subsequent requests can consume the active KPI formula set.
- Verified with `python -m pytest tests/test_semantic_memory_5b.py tests/test_glossary.py tests/test_orchestration_query.py -q`.

### File List

- `services/orchestration/semantic/management.py`
- `services/orchestration/routes/admin.py`
- `services/orchestration/routes/glossary.py`
- `services/orchestration/routes/query.py`
- `services/orchestration/graph/state.py`
- `services/orchestration/graph/graph.py`
- `tests/test_semantic_memory_5b.py`
