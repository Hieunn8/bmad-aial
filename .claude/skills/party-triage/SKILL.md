---
name: party-triage
description: Use party-mode style multi-agent discussion to surface blockers/ambiguities, then apply BMAD-safe triage decisions (not blanket acceptance).
---

# Party Triage (BMAD-safe)

Use this skill when the user wants to discuss blockers, ambiguities, or quality findings with multiple perspectives, while keeping decisions aligned to BMAD scope and gates.

## Invocation

- `/party-triage <context or question>`
- Example: `/party-triage Story 4.4 AC conflict with FR-A7, propose fixes`

## Required Behavior

1. Always run a party-mode style discussion to surface issues from multiple angles.
2. Never auto-accept all findings.
3. Auto-accept only findings that are:
   - Severity = Critical or High, and
   - Have concrete evidence (`file_path:line` or explicit FR/AC mismatch reference).
4. Medium/Low findings must go to triage list for explicit user approval.
5. Reject findings that expand scope beyond the current story/FR, unless user explicitly opts in.
6. Keep output concise and actionable.

## Severity Rules

- **Critical**: blocks delivery, security/compliance break, direct FR contradiction, or release gate failure.
- **High**: strong risk to acceptance criteria, architecture contract, or testability.
- **Medium**: quality/maintainability gap that does not block AC pass now.
- **Low**: nits, wording, optional cleanup.

## Decision Policy

- **Accepted**: only Critical/High with evidence.
- **Triage**: Medium/Low (await user decision).
- **Rejected**: out-of-scope or unsupported claims.

## Output Format (mandatory)

| Issue | Severity | Evidence | FR/AC Impact | Proposed Fix | Decision |
|---|---|---|---|---|---|

Decision values must be exactly: `Accepted` / `Triage` / `Rejected`.

## Final BMAD Gate Summary (mandatory)

End with:

- `BMAD Gate: Ready` or `BMAD Gate: Blocked`
- If blocked: list blocking items (Critical/High accepted findings) with file references.

## Scope Guardrails

- Anchor every finding to current story/epic FR context.
- Do not propose new features or cross-epic scope unless user asks.
- Prefer minimal diffs that make AC verifiable.

## Concise Example

Input:
`/party-triage Story 6.2 scheduled reports approval logic vs FR-E3`

Output shape:
- 1 table with findings + decisions
- 1 BMAD Gate line (Ready/Blocked)
- If Blocked: bullet list of blockers
