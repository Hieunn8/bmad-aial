# Story 1.6: Observability Minimal Stack

Status: review

## Story

As a delivery team member,
I want to deliver **Observability Minimal Stack** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. HÃ nh vi/Ä‘áº§u ra cá»§a story **1.6 - Observability Minimal Stack** bÃ¡m Ä‘Ãºng pháº¡m vi mÃ´ táº£ trong `_bmad-output/planning-artifacts/epics.md`.
2. Táº¥t cáº£ yÃªu cáº§u liÃªn quan Ä‘Æ°á»£c trace Ä‘Æ°á»£c vá» Epic 1 (vÃ­ dá»¥: CÃ¡c yÃªu cáº§u chá»©c nÄƒng/NFR liÃªn quan trong epics.md).
3. Thiáº¿t káº¿ triá»ƒn khai tuÃ¢n thá»§ rÃ ng buá»™c kiáº¿n trÃºc vÃ  security hiá»‡n cÃ³; khÃ´ng má»Ÿ rá»™ng scope ngoÃ i story.
4. CÃ³ bá»™ kiá»ƒm chá»©ng rÃµ rÃ ng (unit/integration/e2e náº¿u Ã¡p dá»¥ng) Ä‘á»ƒ chá»©ng minh AC pass.
5. TÃ i liá»‡u Dev Notes nÃªu rÃµ dependencies, assumptions, vÃ  tiÃªu chÃ­ review/done.

## Tasks / Subtasks

- [x] Chá»‘t pháº¡m vi vÃ  dependency cá»§a story tá»« epics/architecture.
- [x] Thiáº¿t káº¿ thay Ä‘á»•i á»Ÿ má»©c interface + data contract cho story nÃ y.
- [x] Triá»ƒn khai theo TDD (RED â†’ GREEN) vá»›i test cases map trá»±c tiáº¿p AC.
- [x] Bá»• sung observability/security checks theo vÃ¹ng tÃ¡c Ä‘á»™ng.
- [x] Tá»•ng há»£p evidence Ä‘á»ƒ chuyá»ƒn tráº¡ng thÃ¡i sang review/done.

## Dev Notes

- Epic context: **Epic 1 â€” Governed Infrastructure & Walking Skeleton**.
- Canonical source of truth: `_bmad-output/planning-artifacts/epics.md`.
- Keep implementation aligned with architecture/PRD constraints; avoid speculative scope.

### Technical Requirements

- Reuse existing patterns in the repo before introducing new abstractions.
- Validate boundary inputs and handle errors explicitly.
- Preserve naming and folder conventions to keep automation stable.

### Architecture Compliance

- Confirm alignment with `_bmad-output/planning-artifacts/architecture.md` before coding.
- Preserve API/data contracts unless the story explicitly requires a controlled change.

### File Structure Requirements

- Primary artifact file: `_bmad-output/implementation-artifacts/1-6-observability-minimal-stack.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` â€” Story 1.6
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

gpt-5 codex

### Debug Log References

- Context verified against `_bmad-output/planning-artifacts/epics.md` and `_bmad-output/planning-artifacts/architecture.md` for Tempo, OTEL Collector, Grafana, and Langfuse minimal-stack requirements.
- `python -m pytest tests/test_infra_observability_config.py -q`
- `python -m pytest tests/test_orchestration_query.py tests/test_langgraph_stub_graph.py tests/test_telemetry_tracer.py -q`
- `python -m ruff check services/orchestration tests`
- `python -m ruff format services/orchestration tests`
- `python -m ruff format --check services/orchestration tests`
- `python -m pytest tests -q` â†’ `111 passed, 1 skipped`
- `docker compose -f infra/docker-compose.dev.yml config`
- `docker compose --profile llm-observability -f infra/docker-compose.dev.yml config`
- `docker compose -f infra/docker-compose.dev.yml up -d --force-recreate tempo otel-collector prometheus grafana`
- Runtime smoke: emitted OTLP span with `setup_tracing("observability-smoke", otlp_endpoint="http://localhost:4317")` and verified retrieval at `http://localhost:3200/api/traces/4463e36db0d9270908fb4a9764245724`
- Runtime smoke: verified Prometheus scrape targets via `http://localhost:9090/api/v1/targets` and Grafana provisioning via container logs
- `docker compose -f infra/docker-compose.dev.yml stop grafana prometheus otel-collector tempo`

### Completion Notes List

- Provisioned a minimal local observability stack in `infra/docker-compose.dev.yml` with Tempo, OpenTelemetry Collector, Prometheus, and Grafana so Epic 1 traces can be stored, scraped, and inspected without adding non-essential production scope.
- Added an optional `llm-observability` profile with Langfuse, ClickHouse, Postgres, and MinIO so token/call instrumentation can be enabled locally without forcing the heavier stack into the default bootstrap path.
- Added config-as-code for the collector, Tempo, Prometheus, and Grafana provisioning, including preloaded dashboards covering latency percentiles, error rate, LangGraph node execution counts, and Langfuse request/token visibility.
- Extended orchestration tracing so `/v1/chat/query` and the LangGraph stub node stamp spans with `trace_id`, `session_id`, `user_id`, `department_id`, and node/route metadata required for cross-tool correlation.
- Added infrastructure-focused tests that validate compose wiring, OTEL/Tempo/Prometheus config shape, Grafana provisioning, and dashboard panel presence, then backed that with a runtime smoke that successfully retrieved a test trace from Tempo by trace ID.

### File List

- infra/docker-compose.dev.yml
- infra/observability/otel-collector/config.yaml
- infra/observability/tempo/config.yaml
- infra/observability/prometheus/prometheus.yml
- infra/observability/grafana/provisioning/datasources/datasources.yml
- infra/observability/grafana/provisioning/dashboards/dashboards.yml
- infra/observability/grafana/dashboards/aial-overview.json
- infra/observability/grafana/dashboards/llm-observability.json
- services/orchestration/graph/nodes/stub_response.py
- services/orchestration/routes/query.py
- tests/test_infra_observability_config.py

### Change Log

- 2026-04-29: Implemented Story 1.6 observability baseline with OTEL Collector, Tempo, Prometheus, Grafana dashboards/provisioning, optional Langfuse profile, and span metadata updates for the orchestration walking skeleton.
