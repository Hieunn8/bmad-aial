# ADR-4A1: Epic 4 ABAC Attribute Extension

**Status:** Accepted  
**Date:** 2026-05-02  
**Epic:** 4 — Protected Access for Sensitive Data

## Context

Epic 2A froze `principal.attr.department` and `principal.attr.clearance` (ADR-2A7).
Epic 4 requires additional attributes for full ABAC: `region` and `approval_authority`.

## Decision

The following `principal.attr` fields are **ADDED** as of Epic 4:

| Attribute | Type | Source | Description |
|-----------|------|--------|-------------|
| `region` | string | Keycloak JWT `region` claim | User's geographic region — gates region-tagged data |
| `approval_authority` | bool | Keycloak JWT `approval_authority` claim | Allows bypass of approval queue for sensitivity_tier ≥ 2 |

**ADR-2A7 freeze is preserved:** `department` and `clearance` are NOT renamed, removed, or retyped.

## Consequences

- Epic 4 adds `region` and `approval_authority` — never modifies existing attrs.
- `JWTClaims` now carries `region: str = ""` and `approval_authority: bool = False` as safe defaults.
- `CerbosClient.check()` passes all four attrs in every request.
- Region-mismatch DENY rule: `R.attr.region != '' AND R.attr.region != P.attr.region → DENY`.
- `approval_authority=True` grants `query_sensitive` action pre-authorization.
- Future epics (5+) MAY ADD further attrs but MUST NOT rename existing ones.
