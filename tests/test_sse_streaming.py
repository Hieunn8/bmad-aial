"""Tests for Story 2A.5 SSE streaming backend."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from aial_shared.auth.keycloak import JWTClaims
from orchestration.streaming.events import (
    SseEventType,
    make_done_event,
    make_error_event,
    make_step_event,
    make_thinking_event,
)
from orchestration.streaming.queue import StreamEventQueue


@pytest.fixture()
def sample_claims() -> JWTClaims:
    return JWTClaims(
        sub="user-123",
        email="user@aial.local",
        department="sales",
        roles=("user",),
        clearance=1,
        raw={},
    )


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app

    return TestClient(app)


def _auth(mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock, claims: JWTClaims) -> None:
    mock_decode.return_value = {
        "sub": claims.sub,
        "email": claims.email,
        "department": claims.department,
        "roles": list(claims.roles),
        "clearance": claims.clearance,
    }
    mock_validate.return_value = claims
    mock_cerbos = MagicMock()
    mock_cerbos.check.return_value = MagicMock(allowed=True)
    mock_cerbos_cls.return_value = mock_cerbos


class TestSseEvents:
    def test_thinking_event_type(self) -> None:
        event = make_thinking_event(phase=1, message="dang phan tich")
        assert event.type == SseEventType.THINKING
        assert event.data["phase"] == 1

    def test_step_event_type(self) -> None:
        event = make_step_event(step=1, total=4, description="phan loai yeu cau")
        assert event.type == SseEventType.STEP
        assert event.data["step"] == 1
        assert event.data["total"] == 4

    def test_done_event_type(self) -> None:
        event = make_done_event(trace_id="abc123")
        assert event.type == SseEventType.DONE
        assert event.data["trace_id"] == "abc123"

    def test_error_event_uses_shared_contract(self) -> None:
        event = make_error_event(error_code="timeout", message="Too slow", trace_id="trace-1")
        assert event.type == SseEventType.ERROR
        assert event.data["error_code"] == "timeout"
        assert event.data["trace_id"] == "trace-1"

    def test_event_serializes_to_sse_format(self) -> None:
        event = make_step_event(step=1, total=4, description="test")
        sse_text = event.to_sse()
        assert sse_text.startswith("data:")
        assert "\n\n" in sse_text
        payload = json.loads(sse_text.split("data:")[1].strip())
        assert payload["type"] == SseEventType.STEP


class TestStreamEventQueue:
    def test_push_and_consume_events(self) -> None:
        q = StreamEventQueue()
        request_id = str(uuid4())
        q.create(request_id, owner_user_id="user-1")
        q.push(request_id, make_thinking_event(phase=1, message="test"))
        q.push(request_id, make_done_event(trace_id="t1"))
        events = list(q.drain(request_id))
        assert len(events) == 2
        assert events[1].type == SseEventType.DONE

    def test_verify_owner_correct(self) -> None:
        q = StreamEventQueue()
        request_id = str(uuid4())
        q.create(request_id, owner_user_id="user-A")
        assert q.verify_owner(request_id, "user-A") is True
        assert q.verify_owner(request_id, "user-B") is False

    def test_drain_unknown_id_returns_empty(self) -> None:
        q = StreamEventQueue()
        events = list(q.drain("nonexistent"))
        assert events == []

    @pytest.mark.anyio
    async def test_next_event_waits_for_future_push(self) -> None:
        q = StreamEventQueue()
        request_id = str(uuid4())
        q.create(request_id, owner_user_id="user-1")

        async def push_later() -> None:
            await asyncio.sleep(0.01)
            q.push(request_id, make_done_event(trace_id="t-late"))
            q.close(request_id)

        push_task = asyncio.create_task(push_later())
        event = await q.next_event(request_id)
        await push_task

        assert event is not None
        assert event.type == SseEventType.DONE

    def test_close_marks_queue_done(self) -> None:
        q = StreamEventQueue()
        request_id = str(uuid4())
        q.create(request_id, owner_user_id="user-1")
        q.close(request_id)
        assert q.is_closed(request_id)


class TestStreamEndpoint:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_stream_unknown_request_id_returns_404(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        resp = client.get(
            f"/v1/chat/stream/{uuid4()}",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 404

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_stream_endpoint_returns_event_stream_content_type(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        from orchestration.streaming.queue import get_stream_queue

        request_id = str(uuid4())
        queue = get_stream_queue()
        queue.create(request_id, owner_user_id=sample_claims.sub)
        queue.push(request_id, make_done_event(trace_id="trace-1"))
        queue.close(request_id)

        resp = client.get(
            f"/v1/chat/stream/{request_id}",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_stream_emits_done_event(
        self,
        mock_cerbos_cls: MagicMock,
        mock_validate: MagicMock,
        mock_decode: MagicMock,
        client: TestClient,
        sample_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, sample_claims)
        from orchestration.streaming.queue import get_stream_queue

        request_id = str(uuid4())
        queue = get_stream_queue()
        queue.create(request_id, owner_user_id=sample_claims.sub)
        queue.push(request_id, make_done_event(trace_id="trace-2", answer="ready"))
        queue.close(request_id)

        resp = client.get(
            f"/v1/chat/stream/{request_id}",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        content = resp.text
        assert '"type": "done"' in content
        assert '"answer": "ready"' in content
