# Story 1.2: Compose Infrastructure Stack

Status: review

## Story

As a delivery team member,
I want to deliver **Compose Infrastructure Stack** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **1.2 - Compose Infrastructure Stack** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
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

### Technical Requirements

- Reuse existing patterns in the repo before introducing new abstractions.
- Validate boundary inputs and handle errors explicitly.
- Preserve naming and folder conventions to keep automation stable.

### Architecture Compliance

- Confirm alignment with `_bmad-output/planning-artifacts/architecture.md` before coding.
- Preserve API/data contracts unless the story explicitly requires a controlled change.

### File Structure Requirements

- Primary artifact file: `_bmad-output/implementation-artifacts/1-2-compose-infrastructure-stack.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 1.2
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

cx/gpt-5.3-codex

### Debug Log References

- `docker compose -f D:/WORKING/AIAL/infra/docker-compose.dev.yml config` render thành công toàn bộ 7 services
- `PYTHONPATH=D:/WORKING/AIAL/infra python -m py_compile D:/WORKING/AIAL/infra/scripts/init-weaviate-schema.py D:/WORKING/AIAL/infra/weaviate/schema.py` pass

### Completion Notes List

- Implemented full local compose infrastructure stack with 7 services: PostgreSQL, Redis, Weaviate, Keycloak, Kong, Cerbos, Vault.
- Added healthchecks and dependency ordering for reproducible startup behavior.
- Added automated realm import via `infra/keycloak/realm-export.json`.
- Added schema ownership contract via `infra/weaviate/schema.py` and idempotent initializer `infra/scripts/init-weaviate-schema.py`.
- Added bootstrap scripts: `infra/scripts/wait-for-services.sh` and `infra/scripts/seed-secrets.sh`.
- Kept scope constrained to Story 1.2 infra compose baseline per epic definition.

### File List

- infra/docker-compose.dev.yml
- infra/cerbos/conf.yaml
- infra/keycloak/realm-export.json
- infra/kong/kong.yml
- infra/weaviate/schema.py
- infra/scripts/wait-for-services.sh
- infra/scripts/init-weaviate-schema.py
- infra/scripts/seed-secrets.sh

### Change Log

- 2026-04-28: Implemented Story 1.2 compose infrastructure stack baseline and bootstrap scripts.
