"""Weaviate-backed document chunk storage and retrieval."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import NAMESPACE_URL, uuid5

import requests
from embedding.client import EmbeddingClient, get_embedding_client
from weaviate_schema.schema import BGE_MODEL_VERSION, bootstrap_schema

from aial_shared.auth.keycloak import JWTClaims
from rag.composition.nodes import RagChunk
from rag.ingestion.chunker import DocumentChunk
from rag.retrieval.policy_filter import PolicyEnforcementService
from rag.retrieval.weaviate_filter import WeaviateFilter, WeaviateFilterBuilder

_DOCUMENT_CHUNK_CLASS = "DocumentChunk"


@dataclass(frozen=True)
class IndexedDocument:
    document_id: str
    filename: str
    chunk_count: int
    indexed_at: str


class WeaviateDocumentStore:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        embedding_client: EmbeddingClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = (base_url or os.getenv("WEAVIATE_URL", "http://localhost:8081")).rstrip("/")
        self._embedding_client = embedding_client or get_embedding_client()
        self._timeout = timeout

    def ensure_schema(self) -> None:
        bootstrap_schema(self._base_url, timeout=self._timeout)

    async def index_document(
        self,
        *,
        document_id: str,
        filename: str,
        source_url: str,
        uploaded_by: str,
        chunks: list[DocumentChunk],
    ) -> IndexedDocument:
        await asyncio.to_thread(self.ensure_schema)
        embeddings = await self._embedding_client.embed_batch([chunk.chunk_text for chunk in chunks])
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            object_id = str(uuid5(NAMESPACE_URL, f"{document_id}:{chunk.chunk_index}"))
            await asyncio.to_thread(self._delete_object, object_id)
            payload = {
                "class": _DOCUMENT_CHUNK_CLASS,
                "id": object_id,
                "properties": {
                    "chunkText": chunk.chunk_text,
                    "chunkIndex": chunk.chunk_index,
                    "documentId": document_id,
                    "documentTitle": filename,
                    "sourceUrl": source_url,
                    "modelVersion": chunk.model_version or BGE_MODEL_VERSION,
                    "departmentId": chunk.department,
                    "clearanceLevel": chunk.classification,
                    "classification": chunk.classification,
                    "effectiveDate": _format_date(chunk.effective_date),
                    "sourceTrust": chunk.source_trust,
                    "pageNumber": chunk.page_number,
                    "uploadedBy": uploaded_by,
                },
                "vector": embedding.vector,
            }
            response = await asyncio.to_thread(
                requests.post,
                f"{self._base_url}/v1/objects",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()

        return IndexedDocument(
            document_id=document_id,
            filename=filename,
            chunk_count=len(chunks),
            indexed_at=datetime.now(UTC).isoformat(),
        )

    async def search(
        self,
        *,
        query: str,
        principal: JWTClaims,
        cerbos_client: object,
        limit: int = 5,
        staleness_threshold_days: int = 180,
        min_score: float = 0.08,
    ) -> list[RagChunk]:
        await asyncio.to_thread(self.ensure_schema)
        decision = PolicyEnforcementService(cerbos_client).enforce(principal)
        if not decision.allowed:
            return []

        weaviate_filter = WeaviateFilterBuilder().build(
            decision,
            staleness_threshold_days=staleness_threshold_days,
        )
        if weaviate_filter is None:
            return []

        embedding = await self._embedding_client.embed(query)
        graphql = {
            "query": _build_graphql_query(
                vector=embedding.vector,
                limit=limit,
                where_filter=weaviate_filter,
            )
        }
        response = await asyncio.to_thread(
            requests.post,
            f"{self._base_url}/v1/graphql",
            json=graphql,
            timeout=self._timeout,
        )
        response.raise_for_status()
        body = response.json()
        items = (
            body.get("data", {})
            .get("Get", {})
            .get(_DOCUMENT_CHUNK_CLASS, [])
        )
        rag_chunks: list[RagChunk] = []
        for index, item in enumerate(items, start=1):
            score = 1.0 - float(item.get("_additional", {}).get("distance", 1.0))
            if score < min_score:
                continue
            rag_chunks.append(
                RagChunk(
                    chunk_text=str(item.get("chunkText", "")),
                    document_id=str(item.get("documentId", "")),
                    source_name=str(item.get("documentTitle", "Untitled document")),
                    page_number=int(item.get("pageNumber", 0) or 0),
                    department=str(item.get("departmentId", "")),
                    score=score,
                    citation_number=index,
                )
            )
        return rag_chunks

    def _delete_object(self, object_id: str) -> None:
        response = requests.delete(
            f"{self._base_url}/v1/objects/{_DOCUMENT_CHUNK_CLASS}/{object_id}",
            timeout=self._timeout,
        )
        if response.status_code not in {200, 204, 404, 422}:
            response.raise_for_status()


def _build_graphql_query(*, vector: list[float], limit: int, where_filter: WeaviateFilter) -> str:
    vector_payload = ", ".join(f"{value:.12f}" for value in vector)
    where_payload = _build_where_filter(where_filter)
    return f"""
    {{
      Get {{
        {_DOCUMENT_CHUNK_CLASS}(
          limit: {limit}
          nearVector: {{
            vector: [{vector_payload}]
          }}
          where: {where_payload}
        ) {{
          chunkText
          documentId
          documentTitle
          departmentId
          pageNumber
          _additional {{
            id
            distance
          }}
        }}
      }}
    }}
    """


def _build_where_filter(where_filter: WeaviateFilter) -> str:
    operands: list[str] = []
    if where_filter.department_filter:
        department_operands = ", ".join(
            (
                "{"
                f'path: ["departmentId"] '
                'operator: Equal '
                f'valueText: "{department}"'
                "}"
            )
            for department in where_filter.department_filter
        )
        operands.append(f"{{operator: Or operands: [{department_operands}]}}")
    operands.append(
        "{"
        'path: ["clearanceLevel"] '
        "operator: LessThanEqual "
        f"valueInt: {where_filter.max_classification}"
        "}"
    )
    if where_filter.effective_date_cutoff:
        operands.append(
            "{"
            'path: ["effectiveDate"] '
            "operator: GreaterThanEqual "
            f'valueDate: "{where_filter.effective_date_cutoff}T00:00:00Z"'
            "}"
        )
    joined = ", ".join(operands)
    return f"{{operator: And operands: [{joined}]}}"


def _format_date(value: date | None) -> str | None:
    if value is None:
        return None
    return f"{value.isoformat()}T00:00:00Z"


_store = WeaviateDocumentStore()


def get_weaviate_document_store() -> WeaviateDocumentStore:
    return _store
