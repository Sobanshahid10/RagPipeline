"""
Unit and Integration Tests for Vector Search, BM25 Search, and Embeddings (Day 4).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.config import settings
from app.ingestion.embedder import (
    compute_cache_key,
    embed_text,
    embed_batch,
    _generate_fallback_embedding,
    EMBEDDING_DIM
)
from app.retrieval.vector_search import vector_search, _format_vector
from app.retrieval.bm25_search import bm25_search
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import CrossEncoderReranker


class MockRedis:
    """Mock in-memory Redis client for fast unit testing."""

    def __init__(self):
        self.store = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def mget(self, keys: list):
        return [self.store.get(k) for k in keys]

    def pipeline(self):
        return MockRedisPipeline(self)


class MockRedisPipeline:
    def __init__(self, redis: MockRedis):
        self.redis = redis
        self.commands = []

    def set(self, key: str, value: str, ex: int = None):
        self.commands.append((key, value))

    async def execute(self):
        for key, value in self.commands:
            self.redis.store[key] = value
        self.commands.clear()


@pytest.mark.asyncio
async def test_compute_cache_key():
    """Test 1: SHA-256 cache key generation is deterministic and prefixed."""
    key1 = compute_cache_key("annual leave policy")
    key2 = compute_cache_key("annual leave policy")
    key3 = compute_cache_key("dental coverage policy")

    assert key1.startswith("emb:")
    assert len(key1) == 20  # "emb:" (4 chars) + 16 hex chars
    assert key1 == key2
    assert key1 != key3


@pytest.mark.asyncio
async def test_embed_text_fallback_and_caching():
    """Test 2: Single text embedding generation and Redis caching."""
    mock_redis = MockRedis()
    text = "Full-time employees receive 25 days of annual leave."

    # First call: Cache miss -> generate & store in Redis
    emb1 = await embed_text(text, redis_client=mock_redis)
    assert len(emb1) == EMBEDDING_DIM
    assert isinstance(emb1[0], float)

    cache_key = compute_cache_key(text)
    assert cache_key in mock_redis.store

    # Second call: Cache hit -> returns directly from mock Redis
    emb2 = await embed_text(text, redis_client=mock_redis)
    assert emb1 == emb2


@pytest.mark.asyncio
async def test_embed_batch_with_partial_cache():
    """Test 3: Batch embedding with partial cache hits and order preservation."""
    mock_redis = MockRedis()
    texts = [
        "Company health insurance coverage details.",
        "Remote work policy and guidelines.",
        "Equipment reimbursement procedure."
    ]

    # Pre-populate cache for the 2nd text
    key_2 = compute_cache_key(texts[1])
    dummy_vec = [0.05] * EMBEDDING_DIM
    mock_redis.store[key_2] = json.dumps(dummy_vec)

    embeddings = await embed_batch(texts, redis_client=mock_redis)

    assert len(embeddings) == 3
    # Text 1: Newly generated
    assert len(embeddings[0]) == EMBEDDING_DIM
    # Text 2: Loaded from cache
    assert embeddings[1] == dummy_vec
    # Text 3: Newly generated
    assert len(embeddings[2]) == EMBEDDING_DIM

    # All keys should now be in Redis
    assert compute_cache_key(texts[0]) in mock_redis.store
    assert compute_cache_key(texts[2]) in mock_redis.store


@pytest.mark.asyncio
async def test_vector_search_sql_execution():
    """Test 4: pgvector cosine similarity search query format and result mapping."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "document_id": "22222222-2222-2222-2222-222222222222",
            "content": "Annual leave policy allows 25 days of vacation.",
            "contextual_summary": "HR Policy",
            "page_number": 2,
            "bounding_box": json.dumps({"xmin": 0.1, "ymin": 0.2, "xmax": 0.9, "ymax": 0.4}),
            "similarity_score": 0.88452
        }
    ]

    query_vec = [0.01] * EMBEDDING_DIM
    tenant_id = "00000000-0000-0000-0000-000000000001"

    results = await vector_search(query_vec, tenant_id=tenant_id, top_k=5, db_conn=mock_conn)

    assert len(results) == 1
    res = results[0]
    assert res["id"] == "11111111-1111-1111-1111-111111111111"
    assert res["similarity_score"] == 0.88452
    assert res["page_number"] == 2
    assert res["bounding_box"]["xmin"] == 0.1

    # Verify HNSW tune query was executed
    mock_conn.execute.assert_called_once_with(f"SET hnsw.ef_search = {settings.HNSW_EF_SEARCH};")


@pytest.mark.asyncio
async def test_bm25_search_sql_execution():
    """Test 5: BM25 TSVector full-text query execution and ranking."""
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "document_id": "22222222-2222-2222-2222-222222222222",
            "content": "Comprehensive dental coverage includes annual checkups.",
            "contextual_summary": "Dental Benefits",
            "page_number": 4,
            "bounding_box": {"xmin": 0.05, "ymin": 0.1, "xmax": 0.85, "ymax": 0.3},
            "bm25_score": 0.65219
        }
    ]

    tenant_id = "00000000-0000-0000-0000-000000000001"
    results = await bm25_search("dental coverage", tenant_id=tenant_id, top_k=5, db_conn=mock_conn)

    assert len(results) == 1
    res = results[0]
    assert res["id"] == "33333333-3333-3333-3333-333333333333"
    assert res["bm25_score"] == 0.65219
    assert "dental coverage" in res["content"].lower()


@pytest.mark.asyncio
async def test_hybrid_search_and_fusion_integration():
    """Test 6: Verify vector_search & bm25_search outputs integrate with RRF and Reranker."""
    vector_mock_conn = AsyncMock()
    vector_mock_conn.fetch.return_value = [
        {
            "id": "doc-a",
            "document_id": "doc-1",
            "content": "Annual leave policy allows 25 days vacation.",
            "contextual_summary": "HR",
            "page_number": 1,
            "bounding_box": {},
            "similarity_score": 0.89
        },
        {
            "id": "doc-b",
            "document_id": "doc-1",
            "content": "Health insurance covers outpatient clinic visits.",
            "contextual_summary": "Health",
            "page_number": 2,
            "bounding_box": {},
            "similarity_score": 0.72
        }
    ]

    bm25_mock_conn = AsyncMock()
    bm25_mock_conn.fetch.return_value = [
        {
            "id": "doc-b",
            "document_id": "doc-1",
            "content": "Health insurance covers outpatient clinic visits.",
            "contextual_summary": "Health",
            "page_number": 2,
            "bounding_box": {},
            "bm25_score": 0.75
        },
        {
            "id": "doc-c",
            "document_id": "doc-1",
            "content": "Travel allowance claims policy.",
            "contextual_summary": "Travel",
            "page_number": 3,
            "bounding_box": {},
            "bm25_score": 0.50
        }
    ]

    tenant_id = "00000000-0000-0000-0000-000000000001"
    vec_results = await vector_search([0.1] * EMBEDDING_DIM, tenant_id=tenant_id, db_conn=vector_mock_conn)
    bm25_results = await bm25_search("health insurance", tenant_id=tenant_id, db_conn=bm25_mock_conn)

    # Fuse with RRF
    fused = reciprocal_rank_fusion(bm25_results, vec_results, k=60, top_n=3)

    assert len(fused) == 3
    # doc-b appeared in both vector and bm25 top results, so it must rank #1 in RRF
    assert fused[0]["id"] == "doc-b"
    assert "rrf_score" in fused[0]

    # Rerank with CrossEncoder
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank("What does health insurance cover?", fused, top_k=2)
    assert len(reranked) == 2
    assert "rerank_score" in reranked[0]
