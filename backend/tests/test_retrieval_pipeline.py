"""Day 6 retrieval pipeline tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api import retrieval as retrieval_api
from app.retrieval import engine
from app.retrieval.compressor import compress_context
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import CrossEncoderReranker


def test_three_way_rrf_rewards_consensus():
    shared = {"id": "shared", "content": "UK leave policy", "bounding_box": {}}
    fused = reciprocal_rank_fusion(
        {
            "bm25": [{"id": "keyword", "content": "leave"}, shared],
            "vector": [shared, {"id": "dense", "content": "holiday"}],
            "graph": [shared],
        },
        top_n=10,
    )
    assert fused[0]["id"] == "shared"
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


def test_reranker_fallback_limits_candidates_and_adds_score():
    reranker = CrossEncoderReranker()
    reranker._load_attempted = True  # force the deterministic offline path
    candidates = [
        {"id": "general", "content": "General benefits", "rrf_score": 0.04},
        {"id": "dental", "content": "Dental coverage limit", "rrf_score": 0.03},
    ]
    results = reranker.rerank("dental coverage", candidates, top_k=1)
    assert results[0]["id"] == "dental"
    assert isinstance(results[0]["rerank_score"], float)


def test_compression_preserves_source_metadata():
    class FakeCompressor:
        def compress_prompt(self, context, question, ratio):
            return {"compressed_prompt": "compressed policy context"}

    chunks = [{
        "id": "chunk-1",
        "content": "A long policy context.",
        "bounding_box": {"xmin": 0.1},
        "page_number": 4,
        "rrf_score": 0.05,
        "rerank_score": 0.9,
    }]
    result = compress_context(chunks, "policy", prompt_compressor=FakeCompressor())
    assert result[0]["content"] == "compressed policy context"
    assert result[0]["id"] == "chunk-1"
    assert result[0]["bounding_box"] == {"xmin": 0.1}
    assert result[0]["page_number"] == 4


@pytest.mark.asyncio
async def test_engine_runs_all_retrievers_and_returns_five(monkeypatch):
    awaitable_embedding = AsyncMock(return_value=[0.1, 0.2])
    bm25 = AsyncMock(return_value=[{"id": "shared", "content": "policy"}])
    vector = AsyncMock(return_value=[{"id": "shared", "content": "policy"}])
    graph = AsyncMock(return_value=[{"id": "shared", "content": "policy"}])
    monkeypatch.setattr(engine.embedder, "embed_text", awaitable_embedding)
    monkeypatch.setattr(engine.bm25_search, "bm25_search", bm25)
    monkeypatch.setattr(engine.vector_search, "vector_search", vector)
    monkeypatch.setattr(engine.graph_search, "graph_search", graph)
    monkeypatch.setattr(
        engine._reranker,
        "rerank",
        lambda query, candidates, top_k: [dict(candidates[0], rerank_score=1.0)],
    )
    monkeypatch.setattr(engine, "compress_context", lambda chunks, query, ratio: chunks)

    result = await engine.retrieve("leave policy", "tenant-1")
    assert len(result) == 1
    assert result[0]["id"] == "shared"
    assert result[0]["rrf_score"] > 0
    bm25.assert_awaited_once()
    vector.assert_awaited_once()
    graph.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_api_uses_authenticated_tenant(monkeypatch):
    mocked_retrieve = AsyncMock(return_value=[{"id": "result-1"}])
    monkeypatch.setattr(retrieval_api, "retrieve", mocked_retrieve)
    user = SimpleNamespace(tenant_id="tenant-a")
    result = await retrieval_api.search(retrieval_api.SearchRequest(query="policy"), user)
    assert result == [{"id": "result-1"}]
    mocked_retrieve.assert_awaited_once_with("policy", "tenant-a")
