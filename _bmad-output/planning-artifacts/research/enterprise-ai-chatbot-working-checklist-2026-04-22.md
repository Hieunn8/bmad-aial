# Working Checklist: Enterprise Internal AI Chatbot

**Date:** 2026-04-22  
**Audience:** Engineering / Data / Security / Platform teams  
**Use:** Delivery checklist for MVP, pilot, and production readiness

## 1. Governance & Scope

- [ ] Assign business owner
- [ ] Assign data owner
- [ ] Assign security owner
- [ ] Assign engineering owner
- [ ] Inventory Oracle sources, schemas, refresh cadence, and sensitivity classes
- [ ] Select 20-50 priority business questions
- [ ] Select 10-20 tier-0 KPIs
- [ ] Standardize canonical business keys across domains

## 2. Identity & Authorization

- [ ] Integrate Keycloak with LDAP/AD
- [ ] Define user attributes: `department`, `region`, `role`, `clearance`, `purpose`
- [ ] Choose policy engine: `Cerbos` or `OPA`
- [ ] Define policy decision contract for app/tool/retrieval access
- [ ] Enable DB-native row/column/cell enforcement where available
- [ ] Remove shared privileged AI query accounts
- [ ] Define audit tuple schema for every request and tool call

## 3. API & Orchestration

- [ ] Stand up API gateway with auth, rate limiting, tracing, and logging
- [ ] Implement `POST /v1/chat/query`
- [ ] Implement status endpoint for long-running jobs
- [ ] Implement streaming endpoint for interactive responses
- [ ] Define routing modes: `sql`, `rag`, `hybrid`, `forecast`
- [ ] Define internal contracts between orchestrator, policy, semantic, connector, and retrieval services

## 4. Semantic Layer

- [ ] Choose `Cube.dev`, `dbt MetricFlow`, or custom semantic catalog
- [ ] Model tier-0 metrics
- [ ] Model approved dimensions and joins
- [ ] Define freshness rules
- [ ] Build business glossary and aliases
- [ ] Version semantic definitions
- [ ] Define semantic cache keys

## 5. Oracle Connector Layer

- [ ] Build `DataSourceRegistry`
- [ ] Separate logical domains from physical schemas
- [ ] Route reads to replicas/reporting sources/cache nodes
- [ ] Enforce read-only SQL
- [ ] Add SQL validator / AST checker
- [ ] Add row limit, timeout, and cost controls
- [ ] Add identity/context propagation into DB path
- [ ] Add per-source audit logging

## 6. RAG Pipeline

- [ ] Define metadata schema for documents and chunks
- [ ] Build ingestion pipeline: parse -> classify -> chunk -> embed -> index -> verify
- [ ] Tag chunks with `department`, `classification`, `effective_date`, `source_trust`
- [ ] Enforce pre-retrieval filtering via policy
- [ ] Set top-K and rerank thresholds
- [ ] Add source validation and poisoned-content safeguards

## 7. Memory & Conversation

- [ ] Use Redis for short-term session state
- [ ] Use PostgreSQL for medium-term summaries
- [ ] Add user/department/sensitivity metadata to memories
- [ ] Use selective recall instead of full-history replay
- [ ] Track token usage per session

## 8. Performance & Reliability

- [ ] Define SLOs for `sql`, `rag`, `hybrid`, and `forecast`
- [ ] Add metadata cache
- [ ] Add semantic result cache
- [ ] Add retrieval candidate cache
- [ ] Split workload pools: chat, sql-heavy, ingestion, export, forecast
- [ ] Implement async job model for export/reporting/forecasting
- [ ] Identify hot paths for materialized views or curated marts
- [ ] Decide when to enable True Cache / read scaling

## 9. Observability & Quality

- [ ] Enable OpenTelemetry tracing end-to-end
- [ ] Collect P50/P95/P99 by mode
- [ ] Log source ids, rows returned, policy decisions, and prompt size
- [ ] Build dashboards for cache hit ratio, timeout rate, and token usage
- [ ] Build eval set for top business questions
- [ ] Add regression tests for SQL validation
- [ ] Add regression tests for policy enforcement
- [ ] Add leakage tests for RAG

## 10. Release Readiness

- [ ] Security review before pilot
- [ ] Data quality review for tier-0 metrics
- [ ] Rollback and incident runbooks for connector failures
- [ ] Approval flow for sensitive exports
- [ ] Capacity review before production rollout

## MVP Gate

- [ ] Tier-0 KPI definitions exist
- [ ] Audit logging is complete
- [ ] Connector path is read-only and validated
- [ ] One business domain works end-to-end
- [ ] Policy is enforced before retrieval/query execution

## Pilot Gate

- [ ] Cross-domain decomposition works reliably
- [ ] P95 is within target
- [ ] No known policy bypass path remains open
- [ ] Monitoring and incident response are active

## Production Gate

- [ ] Answer quality validated on real business questions
- [ ] Governance and auditability validated
- [ ] Cache/read-scaling strategy implemented
- [ ] Runbooks exist for Oracle, RAG, model, and policy failures

## Delivery Order

- [ ] Build auth, audit, and connector safety first
- [ ] Build semantic layer for tier-0 KPIs second
- [ ] Build single-domain SQL path third
- [ ] Build filtered RAG fourth
- [ ] Build cross-domain decomposition fifth
- [ ] Build async exports/reporting sixth
- [ ] Build forecasting scale-out last
