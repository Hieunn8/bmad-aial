"""Tests for the canonical Weaviate schema bootstrap contract.

Validates naming conventions, collection structure, embedding compatibility,
and idempotent bootstrap behaviour — all without requiring a live Weaviate instance.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, patch

import pytest
from weaviate_schema.schema import (
    BGE_MODEL_VERSION,
    EMBEDDING_DIMS,
    SCHEMA_COLLECTIONS,
    get_collection_names,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_embedding_dims_is_1024(self) -> None:
        assert EMBEDDING_DIMS == 1024

    def test_model_version_contains_bge_m3(self) -> None:
        assert "bge-m3" in BGE_MODEL_VERSION.lower()

    def test_model_version_is_string(self) -> None:
        assert isinstance(BGE_MODEL_VERSION, str)
        assert BGE_MODEL_VERSION  # non-empty


# ---------------------------------------------------------------------------
# Collection inventory
# ---------------------------------------------------------------------------


REQUIRED_COLLECTIONS = {"QueryResultCache", "DocumentChunk"}


class TestCollectionInventory:
    def test_required_collections_present(self) -> None:
        names = get_collection_names()
        assert REQUIRED_COLLECTIONS <= names, (
            f"Missing collections: {REQUIRED_COLLECTIONS - names}"
        )

    def test_schema_collections_is_list(self) -> None:
        assert isinstance(SCHEMA_COLLECTIONS, list)
        assert len(SCHEMA_COLLECTIONS) >= 2


# ---------------------------------------------------------------------------
# Naming conventions (AC2, AC3)
# ---------------------------------------------------------------------------


_PASCAL_RE = re.compile(r"^[A-Z][a-zA-Z0-9]+$")
_CAMEL_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")


class TestNamingConventions:
    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_collection_name_is_pascal_case(self, collection: dict) -> None:
        name = collection["class"]
        assert _PASCAL_RE.match(name), f"Collection '{name}' must be PascalCase"

    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_collection_name_is_singular(self, collection: dict) -> None:
        name = collection["class"]
        assert not name.endswith("s") or name.endswith("ss"), (
            f"Collection '{name}' should use singular form"
        )

    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_all_properties_are_camel_case(self, collection: dict) -> None:
        for prop in collection.get("properties", []):
            prop_name = prop["name"]
            assert _CAMEL_RE.match(prop_name), (
                f"Property '{prop_name}' in '{collection['class']}' must be camelCase"
            )


# ---------------------------------------------------------------------------
# Vectorizer config (AC3)
# ---------------------------------------------------------------------------


class TestVectorizerConfig:
    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_vectorizer_is_none(self, collection: dict) -> None:
        assert collection.get("vectorizer") == "none", (
            f"Collection '{collection['class']}' must use vectorizer='none' "
            f"(vectors provided by application via bge-m3)"
        )

    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_vector_index_uses_cosine_distance(self, collection: dict) -> None:
        index_cfg = collection.get("vectorIndexConfig", {})
        assert index_cfg.get("distance") == "cosine", (
            f"Collection '{collection['class']}' must use cosine distance"
        )


# ---------------------------------------------------------------------------
# model_version property (AC3)
# ---------------------------------------------------------------------------


class TestModelVersionProperty:
    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_model_version_property_exists(self, collection: dict) -> None:
        prop_names = {p["name"] for p in collection.get("properties", [])}
        assert "modelVersion" in prop_names, (
            f"Collection '{collection['class']}' must have 'modelVersion' property"
        )

    @pytest.mark.parametrize("collection", SCHEMA_COLLECTIONS)
    def test_model_version_property_is_text(self, collection: dict) -> None:
        props = {p["name"]: p for p in collection.get("properties", [])}
        mv_prop = props.get("modelVersion", {})
        assert mv_prop.get("dataType") == ["text"], (
            f"modelVersion in '{collection['class']}' must have dataType=['text']"
        )


# ---------------------------------------------------------------------------
# QueryResultCache specific (AC2, AC4)
# ---------------------------------------------------------------------------


class TestQueryResultCacheCollection:
    @pytest.fixture()
    def collection(self) -> dict:
        return next(c for c in SCHEMA_COLLECTIONS if c["class"] == "QueryResultCache")

    def test_has_query_text_property(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "queryText" in names

    def test_has_query_hash_property(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "queryHash" in names

    def test_has_department_id_for_tenant_isolation(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "departmentId" in names


# ---------------------------------------------------------------------------
# DocumentChunk specific (AC2, AC4)
# ---------------------------------------------------------------------------


class TestDocumentChunkCollection:
    @pytest.fixture()
    def collection(self) -> dict:
        return next(c for c in SCHEMA_COLLECTIONS if c["class"] == "DocumentChunk")

    def test_has_chunk_text_property(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "chunkText" in names

    def test_has_document_id_property(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "documentId" in names

    def test_has_clearance_level_for_access_control(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "clearanceLevel" in names

    def test_has_department_id_for_access_control(self, collection: dict) -> None:
        names = {p["name"] for p in collection["properties"]}
        assert "departmentId" in names

    def test_clearance_level_is_int(self, collection: dict) -> None:
        props = {p["name"]: p for p in collection["properties"]}
        assert props["clearanceLevel"]["dataType"] == ["int"]

    def test_has_effective_date_for_staleness_filtering(self, collection: dict) -> None:
        props = {p["name"]: p for p in collection["properties"]}
        assert props["effectiveDate"]["dataType"] == ["date"]

    def test_has_source_trust_for_rag_metadata(self, collection: dict) -> None:
        props = {p["name"]: p for p in collection["properties"]}
        assert props["sourceTrust"]["dataType"] == ["text"]


# ---------------------------------------------------------------------------
# Idempotent bootstrap (AC5)
# ---------------------------------------------------------------------------


class TestIdempotentBootstrap:
    def test_bootstrap_skips_existing_collections(self) -> None:
        """bootstrap_schema must not POST to Weaviate for already-existing collections."""
        from weaviate_schema.schema import bootstrap_schema

        mock_get = MagicMock()
        mock_get.return_value.json.return_value = {
            "classes": [{"class": c["class"]} for c in SCHEMA_COLLECTIONS]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post = MagicMock()

        with patch("weaviate_schema.schema.requests.get", mock_get), \
             patch("weaviate_schema.schema.requests.post", mock_post):
            bootstrap_schema("http://localhost:8081")

        mock_post.assert_not_called()

    def test_bootstrap_creates_missing_collections(self) -> None:
        """bootstrap_schema POSTs only missing collections."""
        from weaviate_schema.schema import bootstrap_schema

        mock_get = MagicMock()
        mock_get.return_value.json.return_value = {"classes": []}
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post = MagicMock()
        mock_post.return_value.raise_for_status = MagicMock()

        with patch("weaviate_schema.schema.requests.get", mock_get), \
             patch("weaviate_schema.schema.requests.post", mock_post):
            bootstrap_schema("http://localhost:8081")

        assert mock_post.call_count == len(SCHEMA_COLLECTIONS)

    def test_bootstrap_partial_existing(self) -> None:
        """bootstrap_schema creates only the one missing collection when one exists."""
        from weaviate_schema.schema import bootstrap_schema

        mock_get = MagicMock()
        mock_get.return_value.json.return_value = {
            "classes": [{"class": "QueryResultCache"}]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post = MagicMock()
        mock_post.return_value.raise_for_status = MagicMock()

        with patch("weaviate_schema.schema.requests.get", mock_get), \
             patch("weaviate_schema.schema.requests.post", mock_post):
            bootstrap_schema("http://localhost:8081")

        assert mock_post.call_count == 1
        posted_class = mock_post.call_args[1]["json"]["class"]
        assert posted_class == "DocumentChunk"

    def test_bootstrap_adds_missing_properties_to_existing_collection(self) -> None:
        from weaviate_schema.schema import bootstrap_schema

        query_cache_schema = next(
            collection for collection in SCHEMA_COLLECTIONS if collection["class"] == "QueryResultCache"
        )
        mock_get = MagicMock()
        mock_get.return_value.json.return_value = {
            "classes": [
                {
                    "class": "DocumentChunk",
                    "properties": [
                        {"name": "chunkText"},
                        {"name": "chunkIndex"},
                        {"name": "documentId"},
                    ],
                },
                {
                    "class": "QueryResultCache",
                    "properties": [*query_cache_schema["properties"]],
                },
            ]
        }
        mock_get.return_value.raise_for_status = MagicMock()
        mock_post = MagicMock()
        mock_post.return_value.raise_for_status = MagicMock()

        with patch("weaviate_schema.schema.requests.get", mock_get), patch(
            "weaviate_schema.schema.requests.post", mock_post
        ):
            bootstrap_schema("http://localhost:8081")

        posted_urls = [call_args.args[0] for call_args in mock_post.call_args_list]
        assert any(url.endswith("/v1/schema/DocumentChunk/properties") for url in posted_urls)
