"""Celery task: rag.document.sync_index — Story 3.1.

acks_late=True, reject_on_worker_lost=True ensures at-least-once delivery
and prevents silent loss if a worker dies mid-ingestion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

logger = logging.getLogger(__name__)


class IngestStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    PARTIAL_FAILED = "partial_failed"


@dataclass
class IngestJob:
    """In-process job record (PostgreSQL-backed in Epic 5A)."""

    document_id: str
    total_chunks: int
    processed_chunks: int = 0
    failed_chunks: int = 0
    status: IngestStatus = IngestStatus.PENDING
    error: str | None = None

    @property
    def progress_percent(self) -> int:
        if self.total_chunks == 0:
            return 100
        return int(self.processed_chunks * 100 / self.total_chunks)


# In-memory job registry (replaced by PostgreSQL ReindexJob table in Epic 5A)
_jobs: dict[str, IngestJob] = {}


def enqueue_sync_index(document_id: str, chunks: list[str]) -> IngestJob:
    """Simulate enqueuing rag.document.sync_index Celery task.

    Real impl: celery_app.send_task('rag.document.sync_index', ...)
    with acks_late=True, reject_on_worker_lost=True.
    """
    job = IngestJob(document_id=document_id, total_chunks=len(chunks))
    _jobs[document_id] = job
    logger.info("Enqueued rag.document.sync_index for document_id=%s chunks=%d", document_id, len(chunks))
    # Simulate immediate success for walking skeleton
    job.processed_chunks = len(chunks)
    job.status = IngestStatus.INDEXED
    return job


def get_job(document_id: str) -> IngestJob | None:
    return _jobs.get(document_id)


def enqueue_reindex(document_id: str, chunk_ids: list[str]) -> IngestJob:
    """Simulate re-index sub-tasks on queue rag.reindex (Story 3.5)."""
    job = IngestJob(document_id=document_id, total_chunks=len(chunk_ids))
    _jobs[document_id] = job
    logger.info("Enqueued reindex for document_id=%s chunks=%d", document_id, len(chunk_ids))
    job.processed_chunks = len(chunk_ids)
    job.status = IngestStatus.INDEXED
    return job
