"""Canonical Weaviate schema bootstrap contract for AIAL.

This module is the single source of truth for all Weaviate collection definitions.
Epic 2A owns this contract. Epic 3 consumes it — never forks it.

Embedding lock:  bge-m3 (BAAI), 1024 dimensions (ADR-003)
Vectorizer:      none — application provides vectors externally
Distance metric: cosine
"""

from __future__ import annotations

import requests

# ---------------------------------------------------------------------------
# Embedding model constants (ADR-003)
# ---------------------------------------------------------------------------

BGE_MODEL_VERSION = "bge-m3-v1"
EMBEDDING_DIMS = 1024

# ---------------------------------------------------------------------------
# Collection definitions
# ---------------------------------------------------------------------------

SCHEMA_COLLECTIONS: list[dict] = [
    {
        "class": "QueryResultCache",
        "description": "Semantic query result cache — Epic 2A.",
        "vectorizer": "none",
        "vectorIndexConfig": {
            "distance": "cosine",
        },
        "properties": [
            {
                "name": "queryText",
                "dataType": ["text"],
                "description": "Original natural language query string",
            },
            {
                "name": "queryHash",
                "dataType": ["text"],
                "description": "SHA-256 hex digest of the canonical query for exact-match cache lookup",
            },
            {
                "name": "sqlGenerated",
                "dataType": ["text"],
                "description": "SQL generated from the query (may be empty for cache misses)",
            },
            {
                "name": "resultJson",
                "dataType": ["text"],
                "description": "Serialized Oracle query result (JSON)",
            },
            {
                "name": "modelVersion",
                "dataType": ["text"],
                "description": f"Embedding model version used to produce the query vector, e.g. '{BGE_MODEL_VERSION}'",
            },
            {
                "name": "sessionId",
                "dataType": ["text"],
                "description": "Session identifier (for multi-turn context)",
            },
            {
                "name": "userId",
                "dataType": ["text"],
                "description": "Keycloak sub of the user who ran the query",
            },
            {
                "name": "departmentId",
                "dataType": ["text"],
                "description": "Department identifier for tenant isolation and VPD alignment",
            },
        ],
    },
    {
        "class": "DocumentChunk",
        "description": "RAG document chunks — Epic 3. Independently searchable pieces of business documents.",
        "vectorizer": "none",
        "vectorIndexConfig": {
            "distance": "cosine",
        },
        "properties": [
            {
                "name": "chunkText",
                "dataType": ["text"],
                "description": "Text content of the document chunk",
            },
            {
                "name": "chunkIndex",
                "dataType": ["int"],
                "description": "Zero-based position of this chunk within its source document",
            },
            {
                "name": "documentId",
                "dataType": ["text"],
                "description": "Stable identifier for the parent document",
            },
            {
                "name": "documentTitle",
                "dataType": ["text"],
                "description": "Human-readable title of the source document",
            },
            {
                "name": "sourceUrl",
                "dataType": ["text"],
                "description": "URL or file path of the source document",
            },
            {
                "name": "modelVersion",
                "dataType": ["text"],
                "description": f"Embedding model version used to produce the chunk vector, e.g. '{BGE_MODEL_VERSION}'",
            },
            {
                "name": "departmentId",
                "dataType": ["text"],
                "description": "Department that owns this document (access control)",
            },
            {
                "name": "clearanceLevel",
                "dataType": ["int"],
                "description": "Minimum clearance level required to access this chunk",
            },
            {
                "name": "classification",
                "dataType": ["int"],
                "description": "Document classification level used for retrieval policy filtering",
            },
            {
                "name": "effectiveDate",
                "dataType": ["date"],
                "description": "Business effective date used for staleness filtering",
            },
            {
                "name": "sourceTrust",
                "dataType": ["text"],
                "description": "Trust label of the source document",
            },
            {
                "name": "pageNumber",
                "dataType": ["int"],
                "description": "Logical page number of the source chunk",
            },
            {
                "name": "uploadedBy",
                "dataType": ["text"],
                "description": "User identifier that uploaded the source document",
            },
        ],
    },
]


def get_collection_names() -> set[str]:
    """Return the set of collection names defined in this schema contract."""
    return {c["class"] for c in SCHEMA_COLLECTIONS}


def bootstrap_schema(weaviate_base_url: str, *, timeout: float = 10.0) -> None:
    """Create missing Weaviate collections from SCHEMA_COLLECTIONS.

    Idempotent: already-existing collections are silently skipped.
    Raises requests.HTTPError on unexpected Weaviate API errors.
    """
    schema_url = f"{weaviate_base_url.rstrip('/')}/v1/schema"

    response = requests.get(schema_url, timeout=timeout)
    response.raise_for_status()
    classes = response.json().get("classes", [])
    existing = {c["class"] for c in classes}
    existing_properties = {
        c["class"]: {prop["name"] for prop in c.get("properties", [])}
        for c in classes
        if isinstance(c, dict) and "properties" in c
    }

    for collection in SCHEMA_COLLECTIONS:
        if collection["class"] in existing:
            known_properties = existing_properties.get(collection["class"])
            if known_properties is None:
                continue
            for prop in collection.get("properties", []):
                if prop["name"] in known_properties:
                    continue
                prop_url = f"{schema_url}/{collection['class']}/properties"
                resp = requests.post(prop_url, json=prop, timeout=timeout)
                resp.raise_for_status()
            continue
        resp = requests.post(schema_url, json=collection, timeout=timeout)
        resp.raise_for_status()
