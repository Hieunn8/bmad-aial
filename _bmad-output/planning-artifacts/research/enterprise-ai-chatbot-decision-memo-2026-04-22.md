# Decision Memo: Enterprise Internal AI Chatbot

**Date:** 2026-04-22  
**Audience:** Leadership / Sponsors / Steering Committee  
**Decision Type:** Architecture and phased investment approval

## Recommendation

Approve this initiative as a **governed AI data access platform** rather than a simple chatbot project.

The platform should provide secure, auditable access to enterprise data and internal documents across Oracle data sources, with AI used as the interface layer, not as an unconstrained database actor.

## What We Should Build

- A controlled chat and API experience for business users
- A semantic layer for KPI definitions, business terms, and approved join paths
- An orchestration layer that routes between SQL, RAG, hybrid answers, and forecasting
- A connector gateway that enforces read-only, validated, identity-aware data access
- A policy layer that filters before retrieval and preserves auditability
- A separate async path for exports, reports, and forecasting jobs

## What We Should Not Build

- Direct AI access to raw Oracle schemas
- Free-form text-to-SQL across the full enterprise estate
- Security filtering after data has already been fetched
- A single execution path that mixes chat, exports, and heavy analytics jobs

## Why This Matters

- It reduces dependency on technical teams for repeated analytical questions
- It improves decision speed through governed self-service access
- It lowers data leakage risk versus ad hoc querying
- It creates a reusable platform for reporting, analytics, forecasting, and future AI workflows

## Key Architecture Decisions

- `API-first`, not DB-first
- `Semantic-layer-first`, not raw schema prompting
- `Policy-enforced retrieval`, not post-fetch filtering
- `Decomposed multi-domain execution`, not unrestricted cross-DB SQL
- `Async-first` for heavy reporting and forecasting

## Investment Logic

This project succeeds only if governance is built in from the start. The semantic layer, policy layer, audit layer, and connector controls are not optional overhead; they are the foundation that makes AI access safe and credible in an enterprise setting.

## Delivery Approach

Use phased rollout:

1. `Foundation`
   Define owners, KPI scope, Oracle source inventory, policy attributes, and target integration boundaries.
2. `MVP`
   Deliver single-domain governed SQL Q&A plus basic RAG for a narrow business scope.
3. `Pilot`
   Add cross-domain decomposition, policy obligations, async exports, and stronger observability.
4. `Production`
   Harden performance, enable read scaling, hierarchical memory, approval flows, and operational runbooks.
5. `Advanced Scale`
   Add bulk forecasting, anomaly detection, and multi-region/distributed patterns where justified.

## Conditions for Approval

- Named business, data, security, and engineering owners
- Prioritized list of questions and tier-0 KPIs
- Agreement that rollout starts narrow, not enterprise-wide
- Agreement that success is measured by answer quality, auditability, latency, and adoption

## Executive Bottom Line

Approve investment in a **governed AI access layer for enterprise data**, not in a free-form chatbot that happens to talk to Oracle. This is the lower-risk, higher-leverage path and the only one likely to scale beyond demo quality.
