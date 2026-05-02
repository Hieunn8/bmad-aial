"""Document chunker — Story 3.1.

SentenceSplitter(chunk_size=512, chunk_overlap=64) with Vietnamese-aware separators.
Each chunk carries required Weaviate metadata.
`effective_date` stored as `date` type (not str) — required for range filtering (Story 3.4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from rag.ingestion.metadata import DocumentMetadata

_MODEL_VERSION = "bge-m3-v1"
_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64

# Vietnamese-aware sentence separators (used by _split_sentences below)
_SENTENCE_ENDS = re.compile(
    r"(?<=[.!?])\s+|(?<=\n)\s*|(?<=\。)\s*|(?<=！)\s*|(?<=？)\s*",
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-level segments using Vietnamese-aware boundaries."""
    parts = _SENTENCE_ENDS.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


@dataclass
class DocumentChunk:
    chunk_index: int
    document_id: str
    chunk_text: str
    department: str = ""
    classification: int = 0
    source_trust: str = "authoritative"
    effective_date: date | None = None   # date type — NOT str (required for Weaviate range filter)
    model_version: str = _MODEL_VERSION
    page_number: int = 0


class DocumentChunker:
    def __init__(self, chunk_size: int = _CHUNK_SIZE, chunk_overlap: int = _CHUNK_OVERLAP) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(
        self,
        text: str,
        *,
        document_id: str,
        metadata: DocumentMetadata | None = None,
        page_number: int = 0,
    ) -> list[DocumentChunk]:
        """Split text into overlapping sentence-aware chunks of at most chunk_size tokens."""
        sentences = _split_sentences(text)
        if not sentences:
            return []

        chunks: list[DocumentChunk] = []
        current_tokens: list[str] = []
        chunk_idx = 0

        for sentence in sentences:
            sentence_tokens = sentence.split()
            if not sentence_tokens:
                continue

            # If a single sentence exceeds chunk_size, split it by token windows
            if len(sentence_tokens) > self.chunk_size:
                if current_tokens:
                    chunks.append(self._make_chunk(
                        " ".join(current_tokens), chunk_idx, document_id, metadata, page_number
                    ))
                    chunk_idx += 1
                    current_tokens = current_tokens[-self.chunk_overlap :]
                # Slide a window through the oversized sentence
                pos = 0
                while pos < len(sentence_tokens):
                    window = sentence_tokens[pos: pos + self.chunk_size]
                    chunks.append(self._make_chunk(
                        " ".join(window), chunk_idx, document_id, metadata, page_number
                    ))
                    chunk_idx += 1
                    pos += self.chunk_size - self.chunk_overlap
                # Seed overlap from last window
                current_tokens = sentence_tokens[-(self.chunk_overlap):]
                continue

            if current_tokens and (len(current_tokens) + len(sentence_tokens)) > self.chunk_size:
                chunks.append(self._make_chunk(
                    " ".join(current_tokens), chunk_idx, document_id, metadata, page_number
                ))
                chunk_idx += 1
                current_tokens = current_tokens[-self.chunk_overlap :]

            current_tokens.extend(sentence_tokens)

        if current_tokens:
            chunks.append(self._make_chunk(
                " ".join(current_tokens), chunk_idx, document_id, metadata, page_number
            ))

        return chunks

    def _make_chunk(
        self,
        text: str,
        idx: int,
        document_id: str,
        metadata: DocumentMetadata | None,
        page_number: int,
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            chunk_index=idx,
            document_id=document_id,
            chunk_text=text,
            page_number=page_number,
        )
        if metadata:
            chunk.department = metadata.department
            chunk.classification = int(metadata.classification)
            chunk.source_trust = metadata.source_trust
            chunk.effective_date = metadata.effective_date  # date type preserved, not serialized
        return chunk
