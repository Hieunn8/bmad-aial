"""LangGraph hybrid composition nodes — Story 3.3.

Node decomposition: merge_results_node → compose_answer_node → format_citations_node
SQL + RAG run in PARALLEL via asyncio.gather() (in route handler).
Citations use CitationRef contract from Epic 2B — no rebuild.

merge_results_node: applies Reciprocal Rank Fusion (RRF, k=60) to rank chunks.
compose_answer_node: produces source-grounded claims, not just counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rag.composition.rrf import reciprocal_rank_fusion


@dataclass
class SqlResult:
    data: list[dict[str, Any]]
    trace_id: str
    table_name: str = "oracle_query"
    timestamp: str = ""


@dataclass
class RagChunk:
    chunk_text: str
    document_id: str
    source_name: str
    page_number: int
    department: str
    score: float
    citation_number: int = 0


@dataclass
class HybridResult:
    sql_result: SqlResult | None
    rag_chunks: list[RagChunk] = field(default_factory=list)
    merged_ranking: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# merge_results_node — applies RRF (Story 3.3 AC)
# ---------------------------------------------------------------------------

def merge_results(
    *,
    sql_result: SqlResult | None,
    rag_chunks: list[RagChunk],
) -> HybridResult:
    """Merge SQL + RAG using Reciprocal Rank Fusion (k=60). Idempotent.

    SQL rows are treated as a ranked list (rank by position).
    RAG chunks are ranked by their vector similarity score.
    RRF produces a single merged ranking that is stored in `merged_ranking`.
    """
    sql_list: list[dict[str, Any]] = []
    if sql_result:
        for i, row in enumerate(sql_result.data):
            sql_list.append({"id": f"sql:{i}", "score": 1.0 / (i + 1), "source": "sql", "data": row})

    rag_list: list[dict[str, Any]] = sorted(
        [{"id": f"rag:{c.document_id}:{c.page_number}", "score": c.score,
          "source": "rag", "chunk": c} for c in rag_chunks],
        key=lambda x: x["score"],
        reverse=True,
    )

    if sql_list and rag_list:
        merged = reciprocal_rank_fusion(sql_list, rag_list, k=60)
    elif sql_list:
        merged = sql_list
    elif rag_list:
        merged = rag_list
    else:
        merged = []

    return HybridResult(sql_result=sql_result, rag_chunks=rag_chunks, merged_ranking=merged)


# ---------------------------------------------------------------------------
# compose_answer_node — source-grounded claims
# ---------------------------------------------------------------------------

def compose_answer(hybrid: HybridResult) -> str:
    """Compose plain-Vietnamese answer with source-grounded claims.

    Each claim references its source (Oracle table or document).
    Real LLM compose_response node in Epic 4+ replaces this rule-based stub.
    """
    if not hybrid.sql_result and not hybrid.rag_chunks:
        return "Không tìm thấy dữ liệu phù hợp với yêu cầu của bạn."

    parts: list[str] = []

    if hybrid.sql_result and hybrid.sql_result.data:
        table = hybrid.sql_result.table_name
        row_count = len(hybrid.sql_result.data)
        first_row = hybrid.sql_result.data[0]
        sample = ", ".join(f"{k}={v}" for k, v in list(first_row.items())[:3])
        parts.append(f"Dữ liệu từ {table}: {row_count} bản ghi [{sample}] [1]")

    for i, chunk in enumerate(hybrid.rag_chunks[:3], start=2):
        preview = chunk.chunk_text[:80].replace("\n", " ")
        parts.append(f"Tài liệu {chunk.source_name} (trang {chunk.page_number}): {preview}… [{i}]")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# format_citations_node — CitationRef contract from Epic 2B
# ---------------------------------------------------------------------------

def format_citations(hybrid: HybridResult) -> list[dict[str, Any]]:
    """Format citation objects using CitationRef contract from Epic 2B.

    SQL sources → type="sql"; document sources → type="document".
    citationNumber comes from the CitationRef object — NOT from array index.
    """
    citations: list[dict[str, Any]] = []
    next_number = 1

    if hybrid.sql_result:
        citations.append({
            "citationNumber": next_number,
            "type": "sql",
            "label": hybrid.sql_result.table_name,
            "details": {
                "sourceName": hybrid.sql_result.table_name,
                "tableOrDocRef": hybrid.sql_result.table_name,
                "freshnessTimestamp": hybrid.sql_result.timestamp or "unknown",
            },
        })
        next_number += 1

    for chunk in hybrid.rag_chunks:
        citation_number = chunk.citation_number if chunk.citation_number > 0 else next_number
        citations.append({
            "citationNumber": citation_number,
            "type": "document",
            "label": chunk.source_name,
            "page": chunk.page_number,
            "department": chunk.department,
            "details": {
                "sourceName": chunk.source_name,
                "tableOrDocRef": f"{chunk.source_name}, trang {chunk.page_number}",
                "freshnessTimestamp": "Xem metadata tài liệu",
            },
        })
        next_number = max(next_number, citation_number) + 1

    return citations
