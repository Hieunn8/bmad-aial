# Story 5A.2: Data Source Configuration (FR-AD3)

Status: review

## Story

As a delivery team member,
I want to deliver **Data Source Configuration (FR-AD3)** with measurable acceptance checks,
so that Epic 5A can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **5A.2 - Data Source Configuration (FR-AD3)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
2. Tất cả yêu cầu liên quan được trace được về Epic 5A (ví dụ: Các yêu cầu chức năng/NFR liên quan trong epics.md).
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

- Epic context: **Epic 5A — IT Admin Control Center**.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/5a-2-data-source-configuration.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 5A.2
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added admin API endpoints for Oracle data source create/list/get/update with runtime-editable row limits and query timeouts.
- Registered data sources in the in-memory `DataSourceRegistry` seam inside `user_role_management.py`.
- Added automatic 5-second connection test seam, schema allowlist validation, Vault secret reference storage, and `UNVERIFIED` warning behavior.
- Added audit logging for create/update operations without storing credential values.
- Verified with `python -m pytest tests/test_user_role_management.py tests/test_audit_api.py -q`.

### File List

- `services/orchestration/admin_control/user_role_management.py`
- `services/orchestration/routes/admin.py`
- `services/orchestration/audit/read_model.py`
- `tests/test_user_role_management.py`
- `tests/test_audit_api.py`
