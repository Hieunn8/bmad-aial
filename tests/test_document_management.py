"""Tests for Story 3.5 — Admin Document Management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rag.retrieval.weaviate_store import IndexedDocument

from aial_shared.auth.keycloak import JWTClaims


@pytest.fixture()
def admin_claims() -> JWTClaims:
    return JWTClaims(
        sub="admin-1", email="admin@aial.local", department="engineering",
        roles=("admin",), clearance=3, raw={},
    )


@pytest.fixture()
def client() -> TestClient:
    from orchestration.main import app
    return TestClient(app)


def _auth(
    mock_cerbos_cls: MagicMock,
    mock_validate: MagicMock,
    mock_decode: MagicMock,
    claims: JWTClaims,
) -> None:
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


@pytest.fixture(autouse=True)
def mock_document_store(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Store:
        async def index_document(
            self,
            *,
            document_id: str,
            filename: str,
            source_url: str,
            uploaded_by: str,
            chunks: list[object],
        ) -> IndexedDocument:
            del source_url, uploaded_by
            return IndexedDocument(
                document_id=document_id,
                filename=filename,
                chunk_count=len(chunks),
                indexed_at="2026-05-04T00:00:00+00:00",
            )

    monkeypatch.setattr(
        "orchestration.routes.documents.get_weaviate_document_store",
        lambda: _Store(),
    )


def _upload_doc(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/v1/admin/documents",
        json={
            "filename": "test.pdf",
            "content_text": "Content. " * 30,
            "department": "sales",
            "classification": 1,
            "source_trust": "authoritative",
            "effective_date": "2024-03-01",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    return resp.json()["document_id"]


class TestDocumentList:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_list_returns_documents(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        _upload_doc(client, headers)
        resp = client.get("/v1/admin/documents", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "documents" in body
        assert "total" in body
        assert body["total"] >= 1


class TestDocumentMetadataUpdate:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_update_metadata_returns_200(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        doc_id = _upload_doc(client, headers)

        resp = client.patch(
            f"/v1/admin/documents/{doc_id}",
            json={"classification": 2},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"


class TestDocumentDelete:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_delete_soft_deletes_document(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        doc_id = _upload_doc(client, headers)

        resp = client.delete(f"/v1/admin/documents/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Document still accessible (soft delete)
        resp2 = client.get(f"/v1/admin/documents/{doc_id}", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "deleted"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_delete_nonexistent_returns_404(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        resp = client.delete(
            f"/v1/admin/documents/{uuid4()}",
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 404


class TestReindexStatus:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_reindex_status_returns_progress(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        headers = {"Authorization": "Bearer fake-jwt"}
        doc_id = _upload_doc(client, headers)

        resp = client.get(f"/v1/admin/documents/{doc_id}/reindex-status", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "progress_percent" in body
        assert "processed_chunks" in body
        assert "failed_chunks" in body
