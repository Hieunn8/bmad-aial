# Story 2A.0: Weaviate Schema Bootstrap

Status: ready-for-dev

## Story

As a platform engineer,
I want a single owned Weaviate schema bootstrap contract in `weaviate/schema.py`,
so that Epic 2A and Epic 3 share one collection definition, one migration path, and one embedding compatibility model.

## Acceptance Criteria

1. A single source of truth exists for Weaviate schema/bootstrap logic in `weaviate/schema.py` or the equivalent locked project path.
2. The bootstrap defines collection/property structure consistent with architecture naming conventions and current Phase 1 needs.
3. Schema logic is compatible with the locked embedding model `bge-m3` (1024 dims) and records `model_version` in schema-relevant definitions.
4. The bootstrap path is reusable by both Epic 2A and Epic 3 without duplicated schema ownership or forked definitions.
5. Migration/bootstrap execution is documented or scripted so local/dev and CI can initialize Weaviate deterministically.

## Tasks / Subtasks

- [ ] Create the owned schema contract.
  - [ ] Introduce or finalize `weaviate/schema.py` as the canonical bootstrap definition.
  - [ ] Make ownership explicit in comments/docs if the repo layout could otherwise confuse future stories.
- [ ] Define Phase 1 collection/property model.
  - [ ] Follow Weaviate naming conventions: collection names `PascalCase`, singular.
  - [ ] Follow property naming conventions: `camelCase`.
  - [ ] Include `modelVersion`-style tracking aligned with `bge-m3`.
- [ ] Align bootstrap with migration strategy.
  - [ ] Ensure the bootstrap can be called before RAG service starts.
  - [ ] Connect to or document `services/rag/migrations/` custom migration flow.
- [ ] Establish shared consumption rules.
  - [ ] Epic 2A consumes bootstrap for initial query-side needs.
  - [ ] Epic 3 consumes the same contract and must not fork schema ownership.
- [ ] Add verification.
  - [ ] Smoke check collection creation/update in a dev Weaviate instance.
  - [ ] Verify schema and embedding dimension assumptions remain compatible.

## Dev Notes

- This story exists to remove ownership ambiguity. `weaviate/schema.py` is now the single source of truth and both Epic 2A and Epic 3 consume it. [Source: _bmad-output/planning-artifacts/epics.md#Cross-cutting Clarifications]
- Architecture already locks `bge-m3` at 1024 dimensions and requires `model_version` tracking from day one. Do not create a schema that assumes provider-swappability without explicit version metadata. [Source: _bmad-output/planning-artifacts/architecture.md#ADR-003 — Embedding Model Lock: `bge-m3` (BAAI)]
- Weaviate migrations are custom scripts, not Alembic. The bootstrap must fit that reality. [Source: _bmad-output/planning-artifacts/architecture.md#Data Migration Strategy]
- The architecture currently points to `services/rag/migrations/` and a versioned initial schema pattern. Reuse that pattern instead of inventing a second initializer. [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Document]

### Technical Requirements

- Embedding lock:
  - model: `bge-m3`
  - dimensions: `1024`
  - schema metadata must preserve `model_version`
- Weaviate naming:
  - collections: singular `PascalCase`
  - properties: `camelCase`
- Bootstrap must be idempotent or safely repeatable enough for local/dev initialization.

### Architecture Compliance

- Must align with ARCH-7 and ARCH-12 from epic inventory: schema initialization before RAG starts; embedding model lock with version tracking. [Source: _bmad-output/planning-artifacts/epics.md#Additional Requirements (Architecture)]
- Must respect the shared ownership rule added to architecture: Epic 2A owns the bootstrap contract, Epic 3 consumes it. [Source: _bmad-output/planning-artifacts/architecture.md#Data Migration Strategy]
- Must not duplicate schema definitions across services or stories.

### File Structure Requirements

- Primary files likely touched:
  - `weaviate/schema.py`
  - `services/rag/migrations/`
  - optional bootstrap/init script used by compose or service startup
- Avoid placing authoritative schema definitions in multiple files that can drift.

### Testing Requirements

- Smoke test schema/bootstrap against a dev Weaviate instance.
- Verify collections/properties conform to naming rules.
- Verify the schema contract includes embedding version metadata compatible with `bge-m3`.
- Verify bootstrap can run more than once without destructive duplication errors or undefined behavior.

### Project Structure Notes

- Architecture already shows RAG-specific migration ownership under `services/rag/migrations/`; integrate with that rather than creating parallel infrastructure. [Source: _bmad-output/planning-artifacts/architecture.md#Selected Approach: Custom Monorepo]
- This story is intentionally narrower than full Epic 3 RAG ingestion; keep focus on ownership, bootstrap, and migration contract.

### References

- `_bmad-output/planning-artifacts/epics.md` — Epic 2A, Story 2A.0
- `_bmad-output/planning-artifacts/epics.md` — Cross-cutting Clarifications
- `_bmad-output/planning-artifacts/architecture.md` — Data Migration Strategy
- `_bmad-output/planning-artifacts/architecture.md` — ADR-003 — Embedding Model Lock: `bge-m3` (BAAI)
- `_bmad-output/planning-artifacts/architecture.md` — Naming conventions for Weaviate collections/properties

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
