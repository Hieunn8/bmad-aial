# Story 1.8: Oracle VPD Smoke Test

Status: in-progress

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

- [x] Create a minimal VPD test design.
  - [x] Define test table schema and seeded rows representing at least two row scopes.
  - [x] Define Oracle context and VPD policy function.
- [x] Implement setup/bootstrap for the smoke test.
  - [x] Create or prepare `CREATE CONTEXT` usage.
  - [x] Add `DBMS_RLS.ADD_POLICY` for the test table.
  - [x] Bind policy predicate to the user principal / department-like context.
- [x] Implement the execution path using the projectâ€™s Oracle connector pattern.
  - [x] Use session pooling compatible with `homogeneous=False`.
  - [x] Ensure user identity or proxy context is applied before query execution.
- [x] Implement the core assertion set.
  - [x] Positive assertion: allowed rows are returned.
  - [x] Negative assertion: disallowed rows are filtered out.
  - [x] Leakage assertion: second execution does not inherit stale context.
- [x] Add teardown/isolation behavior suitable for repeated CI/local runs.
  - [x] Reset context before releasing pooled connections.
  - [x] Avoid leaving test policy artifacts in a way that breaks later runs.
- [x] Mark the smoke test as a release/staging blocker in story notes or test naming conventions.

## Dev Notes

- Oracle VPD is not optional defense-in-depth fluff; it is the DB-layer enforcement for FR-A3 and a mandatory gate before Epic 2A Oracle paths. [Source: _bmad-output/planning-artifacts/prd.md#Module 4 â€” Security & Access Control (CRITICAL)]
- Architecture already calls out the exact failure mode to prevent: connection pool context leakage between concurrent requests. The test must explicitly cover context reset. [Source: _bmad-output/planning-artifacts/architecture.md#ADR-001 â€” Multi-tenancy Model: Shared Schema + Row-Level Security]
- Do not model this with a shared DBA account. The architecture locks heterogeneous/proxy behavior for per-user identity passthrough. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Epic 1 labels this story as a P0 security gate. Treat test readability and determinism as first-class deliverables. [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 â€” Governed Infrastructure & Walking Skeleton]

### Technical Requirements

- Oracle connector path must support `SessionPool` with `homogeneous=False`.
- VPD context must be set before query execution and reset before connection release.
- The test must be runnable repeatedly without manual DB cleanup.
- Assertions must verify filtered result behavior, not just that setup SQL executed.

### Architecture Compliance

- Conform to the locked security chain: Keycloak/Cerbos at app layers, Oracle VPD at DB layer. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Cover the documented risk: VPD context leak across pooled connections. [Source: _bmad-output/planning-artifacts/architecture.md#ADR-001 â€” Multi-tenancy Model: Shared Schema + Row-Level Security]
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

- `_bmad-output/planning-artifacts/epics.md` â€” Epic 1, Story 1.9
- `_bmad-output/planning-artifacts/prd.md` â€” FR-A3, FR-A6
- `_bmad-output/planning-artifacts/architecture.md` â€” Authentication & Security
- `_bmad-output/planning-artifacts/architecture.md` â€” ADR-001 â€” Multi-tenancy Model: Shared Schema + Row-Level Security

### Review Findings

- [x] [Review][Patch] `_set_scope` ngoài `try` block → context leak nếu callproc thực thi server-side rồi raise [services/data_connector/oracle_vpd.py:59] — fixed
- [x] [Review][Patch] Bootstrap passwords hardcoded constants, không dùng env vars (inconsistent với ADMIN_PASSWORD) [tests/test_oracle_vpd_smoke.py:16-23] — fixed
- [x] [Review][Patch] Teardown `_cleanup_security_objects` không exception-safe → partial schema trên cleanup failure [tests/test_oracle_vpd_smoke.py, prepared_database finally] — fixed
- [x] [Review][Patch] `_bootstrap_owner_objects`/`_bootstrap_policy` ngoài `try` → partial schema nếu bootstrap raise [tests/test_oracle_vpd_smoke.py:183-187] — fixed
- [x] [Review][Patch] Story task checkboxes core assertions chưa check dù đã implement — fixed
- [x] [Review][Defer] `fetch_scalar` không có VPD scope guard — design footgun cho future callers, chấp nhận được ở story này — deferred, pre-existing
- [x] [Review][Defer] `_clear_scope` raise trong finally sẽ replace original exception — uncommon path, deferred, pre-existing
- [x] [Review][Defer] Pool defaults min=max=1 là public API config — production concern, deferred, pre-existing

## Dev Agent Record

### Agent Model Used

gpt-5 codex

### Debug Log References

- Context verified against `_bmad-output/planning-artifacts/epics.md` and `_bmad-output/planning-artifacts/architecture.md` for Oracle VPD, proxy authentication, and context-reset requirements.
- Official references checked for implementation constraints:
  - python-oracledb connection/authentication docs on pooled proxy auth and `homogeneous=False`
  - gvenzl Oracle Free container docs for `ORACLE_PASSWORD`, `APP_USER`, and `healthcheck.sh`
- `python -m pip install oracledb>=3.4.0`
- `python -m ruff format services/data_connector tests/test_oracle_vpd_client.py tests/test_oracle_vpd_smoke.py`
- `python -m ruff check services/data_connector tests/test_oracle_vpd_client.py tests/test_oracle_vpd_smoke.py`
- `python -m ruff format --check services/data_connector tests/test_oracle_vpd_client.py tests/test_oracle_vpd_smoke.py`
- `python -m pytest tests/test_oracle_vpd_client.py -q` â†’ `2 passed`
- `python -m pytest tests/test_oracle_vpd_client.py tests/test_oracle_vpd_smoke.py -q` â†’ `2 passed, 3 skipped`
- `docker compose --profile oracle-vpd -f infra/docker-compose.dev.yml config`
- `docker compose --profile oracle-vpd -f infra/docker-compose.dev.yml up -d oracle-free` failed during image extract with Docker daemon `input/output error`
- Subsequent Docker commands also failed with host-side daemon/storage faults (`failed to retrieve image list`, `cannot allocate memory`, `meta.db: input/output error`)
- Retry check on 2026-04-29 13:48 ICT:
  - `docker version` succeeded
  - `docker pull gvenzl/oracle-free:23-slim-faststart` failed immediately with `write /var/lib/desktop-containerd/daemon/io.containerd.metadata.v1.bolt/meta.db: input/output error`
  - `docker compose --profile oracle-vpd -f infra/docker-compose.dev.yml up -d oracle-free` failed with the same `meta.db` error

### Completion Notes List

- Added a dedicated `services/data_connector` boundary with an `OracleVPDClient` and pooled proxy configuration helper that uses `homogeneous=False`, sets Oracle application context before query execution, and clears it in `finally` before the pooled connection is released.
- Added an Oracle VPD smoke test module that bootstraps a minimal Oracle object set in code: owner user, proxy user, session user, `CREATE CONTEXT`, VPD-protected table, PL/SQL package for set/clear context, and `DBMS_RLS.ADD_POLICY`.
- Added unit coverage for connector behavior so the context-clear path is exercised even without a live Oracle database.
- Added `oracle-vpd` Docker Compose profile plus `Makefile` targets so the smoke gate has a repeatable local/CI entrypoint once Docker runtime health is restored.
- Story is not moved to `review` because the live Oracle smoke gate could not be executed in this environment: Docker Desktop/containerd on the host is currently failing to pull/extract Oracle images with host-side storage/runtime errors before the database can boot.
- Retried the live Oracle path after Docker daemon recovered enough to answer `docker version`, but the containerd metadata store is still corrupt/unwritable, so the blocker remains active and AC 1-5 cannot be proven yet against a live database.

### File List

- Makefile
- infra/docker-compose.dev.yml
- pyproject.toml
- services/data_connector/__init__.py
- services/data_connector/oracle_vpd.py
- services/data_connector/pyproject.toml
- tests/test_oracle_vpd_client.py
- tests/test_oracle_vpd_smoke.py

### Change Log

- 2026-04-29 (code-review): Applied 4 patches — moved `_set_scope` inside `try` block, converted bootstrap passwords to env vars, made teardown exception-safe, moved bootstrap calls inside `try`. 2 unit tests pass. Story remains `in-progress` pending Docker daemon recovery for live Oracle gate.
- 2026-04-29: Added Oracle VPD connector boundary, live-smoke test scaffolding, `oracle-vpd` Compose profile, and blocking security-gate test markers; live Oracle execution remains blocked by local Docker daemon storage/runtime failures.
- 2026-04-29: Retried Oracle image bootstrap; blocker persists at Docker Desktop containerd `meta.db` I/O layer, so story remains `in-progress`.
