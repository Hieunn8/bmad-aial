# Story 7.2: Anomaly Detection & Alerts (FR-F2)

Status: review

## Story

As a delivery team member,
I want to deliver **Anomaly Detection & Alerts (FR-F2)** with measurable acceptance checks,
so that Epic 7 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **7.2 - Anomaly Detection & Alerts (FR-F2)** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/7-2-anomaly-detection-and-alerts.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 7.2
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

### Completion Notes List

- Added anomaly detection API endpoints for scan, history listing, detail view, acknowledge, and dismiss flows.
- Implemented department-scoped anomaly alert history with severity, deviation, isolation-forest score, 30-day false-positive rate, and detection latency metadata.
- Added chat UI anomaly panel with history rail, time-series chart highlighting anomaly point in red, business-readable explanation, 3 suggested next actions, and `ConfidenceBreakdownCard` reuse.
- Kept dismissed alerts in history while allowing acknowledge/dismiss state transitions.
- Added backend and frontend automated coverage for alert creation, access control, and UI interaction.

### File List

- services/orchestration/anomaly_detection/__init__.py
- services/orchestration/anomaly_detection/service.py
- services/orchestration/routes/anomaly_detection.py
- services/orchestration/main.py
- apps/chat/src/components/epic7/AnomalyAlertsPanel.tsx
- apps/chat/src/components/epic7/AnomalyAlertsPanel.test.tsx
- apps/chat/src/components/epic5b/Epic5BWorkspace.tsx
- tests/test_anomaly_detection.py
