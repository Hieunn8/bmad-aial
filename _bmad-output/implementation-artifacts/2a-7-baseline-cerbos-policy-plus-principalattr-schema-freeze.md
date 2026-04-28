# Story 2A.7: Baseline Cerbos Policy + principal.attr Schema Freeze

Status: ready-for-dev

## Story

As a security/platform engineer,
I want the Phase 1 Cerbos `principal.attr` schema and JWT mapping frozen with a minimal baseline,
so that Epic 2A can enforce governed query access now and Epic 4 can extend attributes later without breaking token contracts.

## Acceptance Criteria

1. Phase 1 baseline `principal.attr` schema is explicitly defined with at least `department` and `clearance`.
2. JWT-to-Cerbos principal mapping for those attributes is documented and implemented in the policy decision path.
3. Cerbos policies and tests compile and validate against the baseline mapping contract.
4. The story produces or updates an ADR that freezes the contract before Epic 4 extends ABAC behavior.
5. The implementation does not defer Cerbos to a later phase and does not rely only on hardcoded role checks.

## Tasks / Subtasks

- [ ] Define the baseline principal contract.
  - [ ] Freeze `principal.attr.department`.
  - [ ] Freeze `principal.attr.clearance`.
  - [ ] Clarify whether role claims remain separate from attrs in the Cerbos input payload.
- [ ] Implement JWT mapping into the Cerbos request context.
  - [ ] Map Keycloak JWT claims to the Cerbos principal payload.
  - [ ] Fail safely when required attrs are missing or malformed.
- [ ] Align policy fixtures and compile checks.
  - [ ] Update `infra/cerbos/policies/` and `tests/` yaml fixtures.
  - [ ] Ensure `cerbos compile ./policies` remains a required CI gate.
- [ ] Add ADR and documentation updates.
  - [ ] Record the freeze decision: `Cerbos principal.attr schema frozen at Epic 2A`.
  - [ ] State explicitly that later epics may extend but must not rename/backfill the baseline JWT mapping.
- [ ] Add verification coverage.
  - [ ] Allowed case with matching baseline attrs.
  - [ ] Deny case for department mismatch or insufficient clearance.

## Dev Notes

- Cerbos is not deferred anymore. Architecture now explicitly states Cerbos must ship in Phase 1 with Kong/Keycloak. [Source: _bmad-output/planning-artifacts/architecture.md#Phase 1 mandatory security lock]
- The baseline contract is already locked in multiple artifacts: `department` and `clearance` are the minimum attrs and Epic 4 may only extend them. [Source: _bmad-output/planning-artifacts/prd.md#Module 4 — Security & Access Control (CRITICAL)]
- Epic 2A owns the freeze; Epic 4 consumes and extends it. This story exists primarily to eliminate future JWT mapping drift. [Source: _bmad-output/planning-artifacts/epics.md#Epic 2A — Minimal Viable Query]
- Policy testing is not optional. Architecture requires `cerbos compile ./policies` plus YAML fixtures to catch policy drift before production. [Source: _bmad-output/planning-artifacts/architecture.md#Technical Constraints & Dependencies]

### Technical Requirements

- Minimum Cerbos principal attrs:
  - `department`
  - `clearance`
- Mapping source: Keycloak JWT claims
- Missing required attrs should produce a predictable deny/error path, not an implicit allow.
- Keep role-based checks compatible with baseline attrs, but do not stop at hardcoded role-only logic.

### Architecture Compliance

- Must align with the locked stack: Keycloak → Cerbos → App → Oracle VPD. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Must respect the explicit principal contract section added to architecture. [Source: _bmad-output/planning-artifacts/architecture.md#Cerbos principal contract (Phase 1 lock)]
- Must produce/update the ADR freeze before Epic 4 ABAC expansion begins. [Source: _bmad-output/planning-artifacts/epics.md#Epic 2A — Minimal Viable Query]

### File Structure Requirements

- Primary files likely touched:
  - `infra/cerbos/policies/`
  - `infra/cerbos/policies/tests/`
  - Keycloak/JWT auth helpers under `shared/` or service auth boundary
  - policy validation path such as `validate_permissions.py`
  - ADR docs under `docs/adr/`
- Keep auth claim parsing close to the auth/policy boundary, not scattered through business logic.

### Testing Requirements

- Policy compile gate must pass.
- YAML policy fixtures must cover:
  - matching department/clearance allow
  - mismatch deny
  - missing attr deny/fail-safe
- Integration test should verify JWT claims actually appear in the Cerbos request principal payload.

### Project Structure Notes

- The architecture tree already reserves Cerbos policy storage under `infra/cerbos/policies/` and auth helpers under shared/service auth boundaries. Reuse that structure. [Source: _bmad-output/planning-artifacts/architecture.md#Selected Approach: Custom Monorepo]
- This story is a contract story, not the full ABAC feature story. Keep scope on baseline mapping, policy compileability, and ADR freeze.

### References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2A, Story 2A.7
- `_bmad-output/planning-artifacts/prd.md` — FR-A2 and Phase 2 pilot notes
- `_bmad-output/planning-artifacts/architecture.md` — Phase 1 mandatory security lock
- `_bmad-output/planning-artifacts/architecture.md` — Cerbos principal contract (Phase 1 lock)
- `_bmad-output/planning-artifacts/architecture.md` — Automated policy testing / `cerbos compile`

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
