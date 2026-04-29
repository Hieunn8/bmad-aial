# Story 1.5: LangGraph Stub Graph + Shared State Contract

Status: review

## Story

As a delivery team member,
I want to deliver **LangGraph Stub Graph + Shared State Contract** with measurable acceptance checks,
so that Epic 1 can progress safely with verifiable outcomes.

## Acceptance Criteria

1. HÃ nh vi/Ä‘áº§u ra cá»§a story **1.5 - LangGraph Stub Graph + Shared State Contract** bÃ¡m Ä‘Ãºng pháº¡m vi mÃ´ táº£ trong `_bmad-output/planning-artifacts/epics.md`.
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

- Primary artifact file: `_bmad-output/implementation-artifacts/1-5-langgraph-stub-graph-plus-shared-state-contract.md`.
- Keep related implementation/tests co-located per existing project structure.

### Testing Requirements

- Define unit test targets for core logic.
- Define integration test targets for boundary/system behavior.
- Define E2E expectations for critical user path impact (if applicable).

### References

- `_bmad-output/planning-artifacts/epics.md` â€” Story 1.5
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

gpt-5 codex

### Debug Log References

- Context verified against `_bmad-output/planning-artifacts/epics.md` and `_bmad-output/planning-artifacts/architecture.md` for `AIALGraphState`, LangGraph assembly, and `thread_id=session_id` checkpointing requirements.
- `python -m pip install langgraph==1.1.8 langgraph-checkpoint-redis==0.4.1 redis==7.4.0 fakeredis==2.35.1`
- `python -m pip install ruff==0.6.9`
- `python -m pytest tests/test_langgraph_stub_graph.py tests/test_orchestration_query.py tests/test_orchestration_health.py tests/test_auth_fastapi_deps.py -q`
- `python -m pytest tests/test_embedding_client.py tests/test_telemetry_tracer.py tests/test_auth_keycloak.py tests/test_auth_cerbos.py tests/test_infra_auth_config.py tests/test_settings.py -q`
- `python -m ruff check services/orchestration tests`
- `python -m ruff format --check services/orchestration tests`
- `python -m pytest tests -q` â†’ `95 passed, 1 skipped`

### Completion Notes List

- Locked shared `AIALGraphState` contract in `services/orchestration/graph/state.py` with the fields required by ARCH-10 and Story 1.5: `trace_id`, `session_id`, `user_id`, `department_id`, `messages`, `intent_type`, `sql_result`, `rag_result`, `final_response`, `error`, `should_abort`.
- Added LangGraph walking-skeleton assembly in `services/orchestration/graph/graph.py` with a single async pass-through node that returns the stub response and compiles with a checkpointer.
- Wired `/v1/chat/query` to invoke the LangGraph stub graph, derive `trace_id`, accept `query + session_id`, and return `{ "answer": "stub", "trace_id": <uuid> }`.
- Preserved authn/authz enforcement by keeping the existing `require_permission()` gateway dependency and reusing `get_current_user()` to seed graph state from the authenticated principal.
- Added `FakeRedisSaver` test helper backed by `fakeredis.FakeRedis` for unit tests without a live Redis server, and a `@pytest.mark.requires_redis` integration test path for real Redis checkpoint validation.
- Updated dependency metadata so orchestration declares LangGraph/Redis requirements and pytest knows the `requires_redis` marker.

### File List

- pyproject.toml
- services/orchestration/main.py
- services/orchestration/pyproject.toml
- services/orchestration/graph/__init__.py
- services/orchestration/graph/checkpointing.py
- services/orchestration/graph/graph.py
- services/orchestration/graph/state.py
- services/orchestration/graph/nodes/__init__.py
- services/orchestration/graph/nodes/stub_response.py
- services/orchestration/routes/query.py
- tests/test_langgraph_stub_graph.py
- tests/test_orchestration_query.py

### Change Log

- 2026-04-29: Implemented Story 1.5 LangGraph walking skeleton with frozen `AIALGraphState`, stub query graph, Redis-compatible checkpointing hooks, and authenticated `/v1/chat/query` response returning `answer + trace_id`.
