"""Shared embedding client contract for AIAL.

This is the single source of truth for the embedding model configuration.
Epic 2A and Epic 3 consume this contract — do not fork or redefine.
"""

from __future__ import annotations

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
