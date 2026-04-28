# Story 1.9: Oracle VPD Smoke Test

Status: ready-for-dev

## Story

As a security engineer,
I want an automated Oracle VPD smoke test with one policy, one table, one user principal, and one assertion,
so that the team proves row-level isolation works before Epic 2A depends on Oracle identity paths.

## Acceptance Criteria

1. A test fixture creates or uses a minimal Oracle object set for VPD validation: one context, one table, one VPD policy, and one authenticated user principal path.
2. The test proves Oracle VPD enforces row filtering at the database layer and cannot be bypassed by the application path.
3. The Oracle connection flow uses heterogeneous/session proxy behavior consistent with the architecture, not a shared DBA identity.
4. The implementation resets connection/session context correctly to avoid context leakage between requests or test runs.
5. The smoke test is automatable and designated as a blocking security gate for the walking skeleton.

## Tasks / Subtasks

- [ ] Create a minimal VPD test design.
  - [ ] Define test table schema and seeded rows representing at least two row scopes.
  - [ ] Define Oracle context and VPD policy function.
- [ ] Implement setup/bootstrap for the smoke test.
  - [ ] Create or prepare `CREATE CONTEXT` usage.
  - [ ] Add `DBMS_RLS.ADD_POLICY` for the test table.
  - [ ] Bind policy predicate to the user principal / department-like context.
- [ ] Implement the execution path using the project’s Oracle connector pattern.
  - [ ] Use session pooling compatible with `homogeneous=False`.
  - [ ] Ensure user identity or proxy context is applied before query execution.
- [ ] Implement the core assertion set.
  - [ ] Positive assertion: allowed rows are returned.
  - [ ] Negative assertion: disallowed rows are filtered out.
  - [ ] Leakage assertion: second execution does not inherit stale context.
- [ ] Add teardown/isolation behavior suitable for repeated CI/local runs.
  - [ ] Reset context before releasing pooled connections.
  - [ ] Avoid leaving test policy artifacts in a way that breaks later runs.
- [ ] Mark the smoke test as a release/staging blocker in story notes or test naming conventions.

## Dev Notes

- Oracle VPD is not optional defense-in-depth fluff; it is the DB-layer enforcement for FR-A3 and a mandatory gate before Epic 2A Oracle paths. [Source: _bmad-output/planning-artifacts/prd.md#Module 4 — Security & Access Control (CRITICAL)]
- Architecture already calls out the exact failure mode to prevent: connection pool context leakage between concurrent requests. The test must explicitly cover context reset. [Source: _bmad-output/planning-artifacts/architecture.md#ADR-001 — Multi-tenancy Model: Shared Schema + Row-Level Security]
- Do not model this with a shared DBA account. The architecture locks heterogeneous/proxy behavior for per-user identity passthrough. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Epic 1 labels this story as a P0 security gate. Treat test readability and determinism as first-class deliverables. [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 — Governed Infrastructure & Walking Skeleton]

### Technical Requirements

- Oracle connector path must support `SessionPool` with `homogeneous=False`.
- VPD context must be set before query execution and reset before connection release.
- The test must be runnable repeatedly without manual DB cleanup.
- Assertions must verify filtered result behavior, not just that setup SQL executed.

### Architecture Compliance

- Conform to the locked security chain: Keycloak/Cerbos at app layers, Oracle VPD at DB layer. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Cover the documented risk: VPD context leak across pooled connections. [Source: _bmad-output/planning-artifacts/architecture.md#ADR-001 — Multi-tenancy Model: Shared Schema + Row-Level Security]
- Keep this as an automated integration/security test before staging deploy. [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Document]

### File Structure Requirements

- Primary files likely touched:
  - Oracle connector module under `services/data-connector/`
  - integration tests under the relevant service test tree
  - optional SQL fixtures/bootstrap scripts
- Reuse the architecture-indicated connector boundary rather than embedding Oracle test logic in orchestration or frontend paths.

### Testing Requirements

- Required automated integration test for:
  - allowed principal returns allowed rows
  - blocked principal cannot see filtered rows
  - context reset prevents stale row visibility on reused connections
- If possible, add a concurrent or sequential reuse scenario that specifically exercises pooled connection reuse.

### Project Structure Notes

- The architecture tree already reserves connector responsibilities under the data connector service. Keep VPD test logic near that boundary. [Source: _bmad-output/planning-artifacts/architecture.md#Selected Approach: Custom Monorepo]
- The outcome of this story directly gates Epic 2A Story 2A.4 Oracle execution.

### References

- `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.9
- `_bmad-output/planning-artifacts/prd.md` — FR-A3, FR-A6
- `_bmad-output/planning-artifacts/architecture.md` — Authentication & Security
- `_bmad-output/planning-artifacts/architecture.md` — ADR-001 — Multi-tenancy Model: Shared Schema + Row-Level Security

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
