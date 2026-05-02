"""Tests for Story 3.3 — Hybrid Answer Composition with Citations."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from rag.composition.rrf import reciprocal_rank_fusion
from rag.composition.nodes import (
    HybridResult,
    SqlResult,
    RagChunk,
    merge_results,
    compose_answer,
    format_citations,
)


class TestReciprocalRankFusion:
    def test_rrf_merges_two_ranked_lists(self) -> None:
        sql_results = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.7}]
        rag_results = [{"id": "b", "score": 0.8}, {"id": "c", "score": 0.6}]
        merged = reciprocal_rank_fusion(sql_results, rag_results, k=60)
        assert len(merged) > 0
        ids = [r["id"] for r in merged]
        assert "b" in ids  # in both lists, should rank high

    def test_rrf_k60_default(self) -> None:
        results = reciprocal_rank_fusion(
            [{"id": "x", "score": 1.0}],
            [{"id": "x", "score": 0.5}],
        )
        assert results[0]["id"] == "x"
        # RRF score = 1/(60+1) + 1/(60+1) for item ranked 1st in both
        assert results[0]["rrf_score"] > 0

    def test_rrf_empty_list_handled(self) -> None:
        result = reciprocal_rank_fusion([], [{"id": "a", "score": 0.5}])
        assert result[0]["id"] == "a"


class TestMergeResultsNode:
    def test_merge_combines_sql_and_rag(self) -> None:
        sql = SqlResult(data=[{"dept": "sales", "revenue": 100}], trace_id="t1")
        rag = [RagChunk(chunk_text="Policy doc text", document_id="doc-1",
                        source_name="Chính sách bán hàng", page_number=1,
                        department="sales", score=0.7)]
        merged = merge_results(sql_result=sql, rag_chunks=rag)
        assert isinstance(merged, HybridResult)
        assert merged.sql_result is sql
        assert len(merged.rag_chunks) == 1

    def test_merge_applies_rrf_and_produces_merged_ranking(self) -> None:
        sql = SqlResult(data=[{"v": 1}, {"v": 2}], trace_id="t1")
        rag = [
            RagChunk(chunk_text="chunk a", document_id="d1", source_name="doc", page_number=1, department="sales", score=0.9),
            RagChunk(chunk_text="chunk b", document_id="d2", source_name="doc", page_number=2, department="sales", score=0.7),
        ]
        merged = merge_results(sql_result=sql, rag_chunks=rag)
        assert len(merged.merged_ranking) > 0, "merge_results must produce a merged_ranking via RRF"
        assert all("rrf_score" in item or "score" in item for item in merged.merged_ranking)

    def test_merge_with_only_sql(self) -> None:
        sql = SqlResult(data=[{"v": 1}], trace_id="t1")
        merged = merge_results(sql_result=sql, rag_chunks=[])
        assert merged.sql_result is sql
        assert merged.rag_chunks == []
        assert len(merged.merged_ranking) > 0

    def test_merge_with_only_rag(self) -> None:
        rag = [RagChunk(chunk_text="text", document_id="d", source_name="doc",
                        page_number=1, department="sales", score=0.8)]
        merged = merge_results(sql_result=None, rag_chunks=rag)
        assert merged.sql_result is None
        assert len(merged.merged_ranking) > 0


class TestComposeAnswerNode:
    def test_compose_answer_references_sql_source(self) -> None:
        sql = SqlResult(data=[{"revenue": 45.2}], trace_id="t1", table_name="sales_summary")
        hybrid = HybridResult(sql_result=sql, rag_chunks=[])
        answer = compose_answer(hybrid)
        assert "sales_summary" in answer, "Answer must reference the source table, not just count strings"
        assert "[1]" in answer, "Answer must include citation marker"

    def test_compose_answer_references_document_source(self) -> None:
        rag = [RagChunk(chunk_text="Doanh thu giảm do mùa vụ cuối năm",
                        document_id="d-1", source_name="Báo cáo Q4",
                        page_number=2, department="sales", score=0.75)]
        hybrid = HybridResult(sql_result=None, rag_chunks=rag)
        answer = compose_answer(hybrid)
        assert "Báo cáo Q4" in answer, "Answer must reference the document source name"
        assert "Doanh thu giảm" in answer, "Answer must include chunk content"

    def test_compose_answer_empty_returns_helpful_message(self) -> None:
        hybrid = HybridResult(sql_result=None, rag_chunks=[])
        answer = compose_answer(hybrid)
        assert isinstance(answer, str)
        assert len(answer) > 0


class TestFormatCitationsNode:
    def test_sql_citations_have_correct_type(self) -> None:
        sql = SqlResult(data=[{"v": 1}], trace_id="t1",
                        table_name="sales_summary", timestamp="2024-01-01")
        hybrid = HybridResult(sql_result=sql, rag_chunks=[])
        citations = format_citations(hybrid)
        sql_cits = [c for c in citations if c["type"] == "sql"]
        assert len(sql_cits) >= 1
        assert sql_cits[0]["citationNumber"] >= 1

    def test_document_citations_have_correct_type(self) -> None:
        rag = [RagChunk(chunk_text="t", document_id="d-1",
                        source_name="Policy", page_number=3, department="sales", score=0.8)]
        hybrid = HybridResult(sql_result=None, rag_chunks=rag)
        citations = format_citations(hybrid)
        doc_cits = [c for c in citations if c["type"] == "document"]
        assert len(doc_cits) >= 1
        assert "page" in doc_cits[0]

    def test_citation_numbers_use_object_not_array_index(self) -> None:
        rag = [
            RagChunk(chunk_text="t1", document_id="d-1", source_name="Doc A",
                     page_number=1, department="sales", score=0.9, citation_number=5),
            RagChunk(chunk_text="t2", document_id="d-2", source_name="Doc B",
                     page_number=2, department="sales", score=0.8, citation_number=7),
        ]
        hybrid = HybridResult(sql_result=None, rag_chunks=rag)
        citations = format_citations(hybrid)
        numbers = [c["citationNumber"] for c in citations]
        assert 5 in numbers
        assert 7 in numbers
        assert 0 not in numbers  # NOT array index
