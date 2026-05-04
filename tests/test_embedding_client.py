"""Tests for embedding client contract stub."""

import pytest
from embedding.client import (
    BGE_MODEL_NAME,
    DIMS,
    DeterministicEmbeddingClient,
    EmbeddingClient,
    EmbeddingResult,
    get_embedding_client,
)


class TestEmbeddingConstants:
    def test_model_name_is_bge_m3(self) -> None:
        assert BGE_MODEL_NAME == "BAAI/bge-m3"

    def test_dimensions_is_1024(self) -> None:
        assert DIMS == 1024


class TestEmbeddingClient:
    def test_default_model_name(self) -> None:
        client = EmbeddingClient()
        assert client.model_name == "BAAI/bge-m3"

    def test_default_dimensions(self) -> None:
        client = EmbeddingClient()
        assert client.dimensions == 1024

    def test_custom_model(self) -> None:
        client = EmbeddingClient(model_name="custom/model", dims=768)
        assert client.model_name == "custom/model"
        assert client.dimensions == 768

    @pytest.mark.anyio
    async def test_embed_raises_not_implemented(self) -> None:
        client = EmbeddingClient()
        with pytest.raises(NotImplementedError):
            await client.embed("test text")

    @pytest.mark.anyio
    async def test_embed_batch_raises_not_implemented(self) -> None:
        client = EmbeddingClient()
        with pytest.raises(NotImplementedError):
            await client.embed_batch(["a", "b"])


class TestDeterministicEmbeddingClient:
    @pytest.mark.anyio
    async def test_embed_returns_normalized_vector(self) -> None:
        client = DeterministicEmbeddingClient()
        result = await client.embed("doanh thu thuần theo khu vực")
        assert result.model == BGE_MODEL_NAME
        assert result.dimensions == DIMS
        assert len(result.vector) == DIMS
        assert any(component != 0.0 for component in result.vector)

    @pytest.mark.anyio
    async def test_same_input_produces_same_vector(self) -> None:
        client = DeterministicEmbeddingClient()
        left = await client.embed("policy revenue approval")
        right = await client.embed("policy revenue approval")
        assert left.vector == right.vector

    def test_get_embedding_client_returns_concrete_client(self) -> None:
        client = get_embedding_client()
        assert isinstance(client, DeterministicEmbeddingClient)


class TestEmbeddingResult:
    def test_is_immutable(self) -> None:
        result = EmbeddingResult(vector=[0.1, 0.2], model="test", dimensions=2)
        with pytest.raises(AttributeError):
            result.vector = [0.3]  # type: ignore[misc]

    def test_fields(self) -> None:
        result = EmbeddingResult(vector=[0.1], model="bge-m3", dimensions=1024)
        assert result.model == "bge-m3"
        assert result.dimensions == 1024
