"""Tests for Stories 3.1 + 3.4 — Document Ingestion + Access Control."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from rag.ingestion.chunker import DocumentChunk, DocumentChunker
from rag.ingestion.metadata import (
    Classification,
    DocumentMetadata,
    validate_document_metadata,
)
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


# ---------------------------------------------------------------------------
# DocumentMetadata — Story 3.4 AC: mandatory validation
# ---------------------------------------------------------------------------

class TestDocumentMetadata:
    def test_valid_metadata_passes(self) -> None:
        meta = DocumentMetadata(
            document_id=str(uuid4()),
            department="sales",
            classification=Classification.INTERNAL,
            source_trust="authoritative",
            effective_date=date(2024, 1, 1),
        )
        errors = validate_document_metadata(meta)
        assert errors == []

    def test_missing_department_rejected(self) -> None:
        meta = DocumentMetadata(
            document_id=str(uuid4()),
            department="",
            classification=Classification.PUBLIC,
            source_trust="authoritative",
            effective_date=date(2024, 1, 1),
        )
        errors = validate_document_metadata(meta)
        assert any("department" in e for e in errors)

    def test_missing_effective_date_rejected(self) -> None:
        meta = DocumentMetadata(
            document_id=str(uuid4()),
            department="sales",
            classification=Classification.INTERNAL,
            source_trust="authoritative",
            effective_date=None,
        )
        errors = validate_document_metadata(meta)
        assert any("effective_date" in e for e in errors)

    def test_classification_values(self) -> None:
        assert Classification.PUBLIC.value == 0
        assert Classification.INTERNAL.value == 1
        assert Classification.CONFIDENTIAL.value == 2
        assert Classification.SECRET.value == 3


# ---------------------------------------------------------------------------
# DocumentChunker — Story 3.1 AC: chunking with metadata
# ---------------------------------------------------------------------------

class TestDocumentChunker:
    def test_chunks_text_into_parts(self) -> None:
        chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
        text = " ".join(f"Từ {i}" for i in range(200))
        chunks = chunker.chunk_text(text, document_id="doc-1")
        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    def test_effective_date_stored_as_date_type_not_string(self) -> None:
        from datetime import date as date_cls
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)
        meta = DocumentMetadata(
            document_id="doc-date-test",
            department="sales",
            classification=Classification.INTERNAL,
            source_trust="authoritative",
            effective_date=date(2024, 3, 1),
        )
        chunks = chunker.chunk_text("Sentence one. Sentence two.", document_id="doc-date-test", metadata=meta)
        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk.effective_date, date_cls), (
                f"effective_date must be date type for Weaviate range filter, got {type(chunk.effective_date)}"
            )
            assert not isinstance(chunk.effective_date, str), "effective_date must NOT be a string"

    def test_each_chunk_has_required_fields(self) -> None:
        chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)
        meta = DocumentMetadata(
            document_id="doc-test",
            department="sales",
            classification=Classification.INTERNAL,
            source_trust="authoritative",
            effective_date=date(2024, 3, 1),
        )
        chunks = chunker.chunk_text("Hello world. " * 20, document_id="doc-test", metadata=meta)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i
            assert chunk.document_id == "doc-test"
            assert chunk.department == "sales"
            assert chunk.classification == Classification.INTERNAL.value
            assert chunk.model_version == "bge-m3-v1"

    def test_chunk_size_512_default(self) -> None:
        chunker = DocumentChunker()
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 64

    def test_staleness_check_excludes_old_docs(self) -> None:
        from rag.ingestion.metadata import is_stale
        old_date = date.today() - timedelta(days=200)
        fresh_date = date.today() - timedelta(days=10)
        assert is_stale(old_date, threshold_days=180) is True
        assert is_stale(fresh_date, threshold_days=180) is False
        # Boundary: exactly 180th day → INCLUDED
        boundary = date.today() - timedelta(days=180)
        assert is_stale(boundary, threshold_days=180) is False


# ---------------------------------------------------------------------------
# Upload API — Story 3.1 + access control (FR-R5)
# ---------------------------------------------------------------------------

@pytest.fixture()
def regular_claims() -> JWTClaims:
    return JWTClaims(
        sub="regular-1", email="user@aial.local", department="sales",
        roles=("user",), clearance=1, raw={},
    )


class TestDocumentUploadApi:
    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_regular_user_cannot_access_admin_documents(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, regular_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, regular_claims)
        resp = client.get("/v1/admin/documents", headers={"Authorization": "Bearer fake-jwt"})
        assert resp.status_code == 403, "Regular user must be denied — FR-R5 admin-only"

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_invalid_classification_returns_400_not_500(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        resp = client.post(
            "/v1/admin/documents",
            json={
                "filename": "test.pdf", "content_text": "c",
                "department": "sales", "classification": 99,
                "source_trust": "authoritative", "effective_date": "2024-01-01",
            },
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 400, f"Expected 400 for invalid classification, got {resp.status_code}"
        assert "errors" in resp.json()

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_upload_with_missing_metadata_returns_400(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        resp = client.post(
            "/v1/admin/documents",
            json={"filename": "test.pdf", "department": ""},
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 400
        assert "errors" in resp.json() or "detail" in resp.json()

    @patch("aial_shared.auth.fastapi_deps.decode_jwt")
    @patch("aial_shared.auth.fastapi_deps.validate_token_claims")
    @patch("aial_shared.auth.fastapi_deps.CerbosClient")
    def test_valid_upload_returns_202_with_document_id(
        self, mock_cerbos_cls: MagicMock, mock_validate: MagicMock, mock_decode: MagicMock,
        client: TestClient, admin_claims: JWTClaims,
    ) -> None:
        _auth(mock_cerbos_cls, mock_validate, mock_decode, admin_claims)
        resp = client.post(
            "/v1/admin/documents",
            json={
                "filename": "policy.pdf",
                "content_text": "Chính sách bán hàng 2024. " * 20,
                "department": "sales", "classification": 1,
                "source_trust": "authoritative", "effective_date": "2024-01-01",
            },
            headers={"Authorization": "Bearer fake-jwt"},
        )
        assert resp.status_code == 202
        body = resp.json()
        assert "document_id" in body
        assert body.get("status") in ("processing", "indexed")  # in-memory stub completes synchronously
