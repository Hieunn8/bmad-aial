# ADR-2A7: Cerbos principal.attr Schema Freeze

**Status:** Accepted  
**Date:** 2026-04-30  
**Epic:** 2A — Minimal Viable Query  

## Context

Epic 4 (Full ABAC Extension) will extend Cerbos policies with additional principal attributes (`region`, `approval_authority`, etc.). To enable Epic 4 to build confidently on a stable contract without backfilling JWT claim mapping, the `principal.attr` schema must be frozen before Epic 2A ships.

## Decision

The following `principal.attr` fields are **frozen** as of Epic 2A:

| Attribute | Type | Source | Description |
|-----------|------|--------|-------------|
| `department` | string | Keycloak JWT `department` claim | User's organizational unit; used for tenant isolation |
| `clearance` | string | Keycloak JWT `clearance` claim (cast to string) | Numeric clearance level as string |

**Mapping location:** `shared/src/aial_shared/auth/cerbos.py` — `CerbosClient.check()`.

Both attributes are **always populated** in the Cerbos request, even when Epic 2A uses only role-based checks. This guarantees Epic 4 can add attribute-based conditions without requiring changes to the JWT mapping layer.

## Consequences

- `department` and `clearance` will always appear in `principal.attr` for every Cerbos check.
- Cerbos policies may use `P.attr.department` and `P.attr.clearance` unconditionally.
- Epic 4 **MAY ADD** new attributes (e.g., `region`, `approval_authority`) but **MUST NOT** rename, remove, or re-type `department` or `clearance`.
- Domain-restricted resources pass `R.attr.domain` to enable department-domain matching at the policy layer (`R.attr.domain != P.attr.department` → DENY).
- `cerbos compile ./infra/cerbos/policies` must remain a required CI gate.
