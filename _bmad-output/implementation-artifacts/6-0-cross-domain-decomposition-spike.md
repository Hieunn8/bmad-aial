# Story 6.0: Cross-domain Decomposition Spike

Status: ready-for-dev

## Story

As an orchestration engineer,
I want a bounded spike that defines the state contract and strategy space for cross-domain query decomposition,
so that Epic 6 can implement production cross-domain execution later without inventing core abstractions under delivery pressure.

## Acceptance Criteria

1. The spike defines a `QueryDecompositionState` `TypedDict` for orchestration state exchange.
2. The spike documents at least two decomposition strategies: horizontal and vertical.
3. The spike documents merge patterns for recombining per-domain query results into one governed response contract.
4. The spike explicitly stays out of production execution delivery; it produces a design/output artifact and code scaffold only as needed.
5. The spike identifies follow-on implications for Epic 6 implementation, including risks, open decisions, and recommended execution path.

## Tasks / Subtasks

- [ ] Define the state contract.
  - [ ] Create `QueryDecompositionState` as a typed orchestration state object.
  - [ ] Include fields for source domains, subqueries, intermediate results, merge metadata, and failure surfaces.
- [ ] Describe horizontal decomposition.
  - [ ] Split one question across peer domains/data sources.
  - [ ] Document when this strategy is appropriate and what governance checks it needs.
- [ ] Describe vertical decomposition.
  - [ ] Split one question into sequential dependent steps or aggregation layers.
  - [ ] Document when this strategy is appropriate and what orchestration risks it adds.
- [ ] Define merge patterns.
  - [ ] Shape of per-domain result payloads.
  - [ ] Merge reconciliation rules for timestamps, units, missing data, and permission-limited slices.
  - [ ] Expected output contract such as `MergedDomainResult`.
- [ ] Record decision output.
  - [ ] Recommended strategy matrix for common cross-domain cases.
  - [ ] Risks, non-goals, and what production Epic 6.4 should implement later.

## Dev Notes

- This story is a spike, not production cross-domain delivery. Epic 6 explicitly says implementation comes later; this story just defines the contract and strategy. [Source: _bmad-output/planning-artifacts/epics.md#Epic 6 — Automated Reporting & Cross-domain Analysis]
- FR-S5 now requires a spike-defined `QueryDecompositionState`, horizontal/vertical strategies, and merge patterns before production implementation starts. [Source: _bmad-output/planning-artifacts/prd.md#Module 2 — Text-to-SQL & Semantic Layer]
- The architecture trace points cross-domain decomposition into orchestration execution nodes, so keep the spike anchored to orchestration state design rather than UI. [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Document]
- This story can run in parallel with Epic 2B research, but must not ship a production-grade execution path yet. [Source: _bmad-output/planning-artifacts/epics.md#Epic Dependency Graph]

### Technical Requirements

- Use `TypedDict` for the state contract to align with the project’s LangGraph state-driven orchestration style.
- The spike must define, at minimum:
  - domain/subquery descriptors
  - dependency ordering metadata
  - partial result envelopes
  - merge/error fields
  - provenance and permission-limited markers
- Output should be concrete enough that Epic 6.4 can implement directly without redefining contracts.

### Architecture Compliance

- Align with the shared orchestration contract style already used for `AIALGraphState`. [Source: _bmad-output/planning-artifacts/epics.md#Epic 2A — Minimal Viable Query]
- Keep production execution out of this story to respect Epic 6 scope boundaries.
- Capture performance implications because cross-domain target SLOs are materially slower than single-domain flows and need explicit orchestration planning. [Source: _bmad-output/planning-artifacts/prd.md#Non-Functional Requirements]

### File Structure Requirements

- Primary files likely touched:
  - orchestration state/contracts module
  - architecture or design note artifact for the spike result
  - optional Epic 6 planning/reference doc
- Avoid burying spike results in code comments only; produce a readable artifact future stories can cite.

### Testing Requirements

- This spike does not require full production tests.
- It should include at least light validation/examples for:
  - one horizontal case
  - one vertical case
  - one merge conflict or permission-limited case

### Project Structure Notes

- Architecture maps FR-S5 to orchestration execution, so keep the spike centered on orchestration nodes and state, not report UI or export flows. [Source: _bmad-output/planning-artifacts/architecture.md#Architecture Decision Document]
- The deliverable may be a story doc plus scaffold/interface file; avoid over-implementing runtime behavior in a research story.

### References

- `_bmad-output/planning-artifacts/epics.md` — Epic 6, Story 6.0
- `_bmad-output/planning-artifacts/prd.md` — FR-S5
- `_bmad-output/planning-artifacts/prd.md` — Performance SLOs for cross-domain decomposed query
- `_bmad-output/planning-artifacts/architecture.md` — FR-S5 trace to orchestration

## Dev Agent Record

### Agent Model Used

GPT-5

### Debug Log References

### Completion Notes List

### File List
