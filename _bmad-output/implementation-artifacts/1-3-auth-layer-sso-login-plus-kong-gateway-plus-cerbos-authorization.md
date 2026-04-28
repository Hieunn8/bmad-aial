# Story 1.3: Auth Layer — SSO Login + Kong Gateway + Cerbos Authorization

Status: review

## Story

As a delivery team member,
I want to deliver **Auth Layer — SSO Login + Kong Gateway + Cerbos Authorization** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. Hành vi/đầu ra của story **1.3 - Auth Layer — SSO Login + Kong Gateway + Cerbos Authorization** bám đúng phạm vi mô tả trong `_bmad-output/planning-artifacts/epics.md`.
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
- Cerbos principal.attr contract locked: `department`, `clearance` (Phase 1 baseline per architecture).
- Kong JWT plugin validates RS256 tokens from Keycloak issuer.
- Rate limiting baseline: 100 requests/day per user (per epics.md AC).

### File Structure Requirements

- Primary artifact file: `_bmad-output/implementation-artifacts/1-3-auth-layer-sso-login-plus-kong-gateway-plus-cerbos-authorization.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` — Story 1.3
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

- `PYTHONPATH="shared/src;services" python -m pytest tests/ -v` → 57 passed, 0 failed
- `docker compose -f infra/docker-compose.dev.yml config` → validates successfully with all 7 services
- Keycloak realm JSON validated: 8h token lifespan, refresh rotation, department/clearance/roles mappers in access token
- Cerbos policies validated: api:chat allows admin/user with query, denies viewer
- Kong config validated: JWT plugin on chat-query route, rate-limiting 100/day, RS256 with rsa_public_key slot
- Kong upstream validated: points to port 8090 (Story 1.4 FastAPI), not Kong's own 8000
- CerbosClient validated: uses POST /api/check/resources with resources[] array format (Cerbos 0.38+ contract)

### Completion Notes List

- Enhanced Keycloak realm-export.json: added aial-api confidential client, aial-claims client scope with protocol mappers (department, clearance, roles), realm roles (admin, user, viewer), dev users with attributes, 8h token lifespan with refresh rotation.
- Configured Kong declarative config: orchestration-api service upstream to port 8090 (Story 1.4 will bind FastAPI here), chat-query route for POST /v1/chat/query, JWT plugin with RS256 validation + rsa_public_key placeholder, rate-limiting plugin (100/day per consumer), health route.
- Created `infra/scripts/configure-kong-jwt.sh`: bootstrap script that fetches Keycloak realm RSA public key at startup and patches kong.yml before Kong reads it. Wired into `make infra-up` with Kong restart after patching.
- Created Cerbos authorization policies: api:chat resource policy (admin/user ALLOW query with department+clearance check, viewer DENY), api:admin resource policy.
- Implemented shared auth module: `shared/src/aial_shared/auth/keycloak.py` — JWT decode with JWKS validation, claims extraction enforcing the 5-field contract (sub, email, department, roles[], clearance), immutable JWTClaims dataclass.
- Implemented Cerbos client: `shared/src/aial_shared/auth/cerbos.py` — CerbosClient using POST /api/check/resources (Cerbos 0.38+ contract) with resources[] array format, principal attrs (department, clearance).
- 57 tests total (16 keycloak unit, 11 cerbos unit, 27 config validation, 3 settings) — all pass with zero regressions.

### File List

- infra/keycloak/realm-export.json
- infra/kong/kong.yml
- infra/cerbos/policies/resource_api.yaml
- infra/cerbos/policies/resource_admin.yaml
- infra/scripts/configure-kong-jwt.sh
- shared/src/aial_shared/auth/__init__.py
- shared/src/aial_shared/auth/keycloak.py
- shared/src/aial_shared/auth/cerbos.py
- shared/pyproject.toml
- tests/test_auth_keycloak.py
- tests/test_auth_cerbos.py
- tests/test_infra_auth_config.py
- Makefile

### Change Log

- 2026-04-29: Implemented Story 1.3 auth layer — Keycloak realm with OIDC clients and JWT claim mappers, Kong gateway with JWT validation and rate limiting, Cerbos PDP policies for endpoint authorization, shared auth module with JWT validation and Cerbos client.
- 2026-04-29: Fixed 3 runtime issues — (1) Kong upstream changed from port 8000 (self-referencing) to 8090 (Story 1.4 FastAPI target); (2) Added rsa_public_key field to Kong JWT consumer + configure-kong-jwt.sh bootstrap script to fetch key from Keycloak at startup; (3) CerbosClient updated to use POST /api/check/resources with resources[] array format per Cerbos 0.38+ contract.
