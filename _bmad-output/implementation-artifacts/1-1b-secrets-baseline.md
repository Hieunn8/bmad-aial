# Story 1.1b: Secrets Baseline

Status: ready-for-dev

## Story

As an infrastructure engineer,
I want a local/dev secrets baseline using HashiCorp Vault dev mode and a repeatable injection pattern,
so that Kong, Keycloak, and Oracle credentials are never hardcoded and later environments can promote the same contract safely.

## Acceptance Criteria

1. Docker Compose local/dev stack includes HashiCorp Vault dev mode and starts reliably alongside the Epic 1 backbone services.
2. Kong admin token, Keycloak client secret, and Oracle credentials are sourced through a documented injection pattern instead of hardcoded values in tracked config files.
3. Application/service settings load secrets via environment injection compatible with Pydantic settings and can be promoted to staging/production Vault-integrated delivery without code rewrites.
4. Repository guardrails make it hard to accidentally commit real secrets, and the story documents the expected Vault path structure for local/dev.
5. A smoke test or operator checklist proves the stack can resolve required secrets and boot dependent services successfully.

## Tasks / Subtasks

- [ ] Add Vault dev service to `infra/docker-compose.dev.yml` and wire health/startup ordering.
  - [ ] Expose only local/dev-safe Vault configuration.
  - [ ] Ensure dependent services wait until Vault is reachable before resolving secrets.
- [ ] Define the baseline secret path contract.
  - [ ] Use `secret/aial-dev/oracle/credentials`.
  - [ ] Use `secret/aial-dev/keycloak/client`.
  - [ ] Use `secret/aial-dev/kong/admin`.
- [ ] Implement the local injection pattern for services that need secrets.
  - [ ] Prefer environment injection consumed by `pydantic_settings.BaseSettings`.
  - [ ] Avoid hardcoding secrets in `infra/kong/kong.yml`, `realm-export.json`, service source, or committed `.env` files.
- [ ] Add bootstrap instructions or script for loading dev secrets into Vault.
  - [ ] Include clearly fake/sample values only.
  - [ ] Document how devs override values locally without editing tracked configs.
- [ ] Add repository safety checks.
  - [ ] Confirm pre-commit/private-key detection remains enabled.
  - [ ] Add or update ignore/example files if needed so real secrets are not committed.
- [ ] Add verification guidance.
  - [ ] Smoke test: Vault reachable, secrets readable, Kong/Keycloak/Oracle dependent config resolved.
  - [ ] Failure mode: missing secret should fail fast with readable startup error.

## Dev Notes

- Local secret strategy is already locked to HashiCorp Vault dev mode for local/dev, not raw `.env` files as the system of record. Keep `.env` limited to non-secret wiring only if absolutely necessary. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- The same contract must promote cleanly to staging/prod Vault-integrated delivery with zero code changes beyond environment wiring. [Source: _bmad-output/planning-artifacts/architecture.md#HashiCorp Vault Path Structure]
- Epic 1 is the infra backbone gate for all later epics, so this story must optimize for repeatability over convenience hacks. [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 — Governed Infrastructure & Walking Skeleton]
- Secrets covered explicitly by epic scope: Kong admin token, Keycloak client secret, Oracle credentials. [Source: _bmad-output/planning-artifacts/epics.md#Epic 1 — Governed Infrastructure & Walking Skeleton]

### Technical Requirements

- Use Vault dev mode in local/dev only; do not model production with plaintext local files.
- Service configuration must be environment-driven and compatible with `pydantic_settings.BaseSettings`.
- No tracked file may contain real secrets.
- Missing secret resolution must fail fast instead of silently falling back to insecure defaults.

### Architecture Compliance

- Align with the locked security stack: Kong + Keycloak + Cerbos + Oracle VPD + Vault-backed secret management. [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Respect the repo-wide requirement `no hardcoded secrets`. [Source: _bmad-output/planning-artifacts/architecture.md#Starter Template Evaluation]
- Preserve the future staging/prod pattern:
  - local/dev: Vault dev mode
  - staging: Vault Agent / integrated delivery
  - production: Vault + K8s Secrets/dynamic secrets

### File Structure Requirements

- Primary files likely touched:
  - `infra/docker-compose.dev.yml`
  - `infra/kong/`
  - `infra/keycloak/`
  - service settings modules under `services/*`
  - optional bootstrap helper under `scripts/` or `infra/`
- Do not place secret-loading business logic in `shared/`; keep it in infra/configuration boundaries.

### Testing Requirements

- Verify Vault service becomes healthy in compose.
- Verify at least one dependent service resolves secrets successfully via the injection contract.
- Verify startup fails clearly when a required secret path/value is absent.
- Verify no real secret values are introduced into tracked repo files.

### Project Structure Notes

- Use the monorepo layout already locked in architecture: infra under `infra/`, services under `services/`, shared code under `shared/`. [Source: _bmad-output/planning-artifacts/architecture.md#Selected Approach: Custom Monorepo]
- Keep the implementation local to infra/config bootstrap; do not sprawl ad hoc secret readers across multiple services.

### References

- `_bmad-output/planning-artifacts/epics.md` — Epic 1, Story 1.1b
- `_bmad-output/planning-artifacts/prd.md` — Security / Secret management
- `_bmad-output/planning-artifacts/architecture.md` — Authentication & Security
- `_bmad-output/planning-artifacts/architecture.md` — Secret Management
- `_bmad-output/planning-artifacts/architecture.md` — HashiCorp Vault Path Structure

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
