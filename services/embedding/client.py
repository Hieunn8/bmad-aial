"""Shared embedding client contract for AIAL.

This is the single source of truth for the embedding model configuration.
Epic 2A and Epic 3 consume this contract — do not fork or redefine.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

BGE_MODEL_NAME = "BAAI/bge-m3"
DIMS = 1024


@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    model: str
    dimensions: int


class EmbeddingClient:
    """Stub embedding client — real implementation in Epic 2A."""

    def __init__(self, model_name: str = BGE_MODEL_NAME, dims: int = DIMS) -> None:
        self._model_name = model_name
        self._dims = dims

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dims

    async def embed(self, text: str) -> EmbeddingResult:
        raise NotImplementedError("Stub — real implementation in Epic 2A")

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        raise NotImplementedError("Stub — real implementation in Epic 2A")


class DeterministicEmbeddingClient(EmbeddingClient):
    """Local deterministic embedding client.

    This is not a semantic foundation model embedding. It uses a hashing-based
    bag-of-tokens representation so local RAG can index and retrieve documents
    without requiring external model downloads or API calls.
    """

    async def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(
            vector=_hash_embed(text, dims=self.dimensions),
            model=self.model_name,
            dimensions=self.dimensions,
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        return [await self.embed(text) for text in texts]


def get_embedding_client() -> EmbeddingClient:
    return DeterministicEmbeddingClient()


def _hash_embed(text: str, *, dims: int) -> list[float]:
    tokens = [token.casefold() for token in text.split() if token.strip()]
    if not tokens:
        return [0.0] * dims

    vector = [0.0] * dims
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        index_a = int.from_bytes(digest[:4], "big") % dims
        index_b = int.from_bytes(digest[4:8], "big") % dims
        weight_a = ((digest[8] / 255.0) * 2.0) - 1.0
        weight_b = ((digest[9] / 255.0) * 2.0) - 1.0
        vector[index_a] += weight_a if weight_a != 0 else 1.0
        vector[index_b] += weight_b if weight_b != 0 else -1.0

    norm = math.sqrt(sum(component * component for component in vector))
    if norm == 0:
        return vector
    return [component / norm for component in vector]
