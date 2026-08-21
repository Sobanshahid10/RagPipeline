"""
Unit tests for Day 7 Agentic Query Layer:
1. Semantic Cache Hit (< 15ms, source: "cache")
2. Query Expansion (original first + alternatives)
3. Strategy Router Classification ("What is Alice's department?" -> MULTI_HOP_GRAPH)
4. Pipeline Orchestration (full flow with chunks, route, query_variants, hyde_used)
"""

from __future__ import annotations

import json
from time import perf_counter
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.agentic.cache import SemanticCache
from app.agentic.expander import expand_query
from app.agentic.hyde import generate_hyde_embedding
from app.agentic.pipeline import process_query
from app.agentic.router import (
    ROUTE_ANALYTICAL_SQL,
    ROUTE_FACTUAL_VECTOR,
    ROUTE_GREETING_DIRECT,
    ROUTE_MULTI_HOP_GRAPH,
    classify_route,
)


class MockRedisPipeline:
    def __init__(self, redis_instance: MockRedis) -> None:
        self.redis = redis_instance
        self.ops = []

    def set(self, key: str, value: str, ex: int | None = None) -> MockRedisPipeline:
        self.ops.append((key, value))
        return self

    async def execute(self) -> list[Any]:
        for key, val in self.ops:
            self.redis.keys[key] = val
        return [True] * len(self.ops)


class MockRedis:
    """In-memory async mock Redis client for semantic cache testing."""

    def __init__(self) -> None:
        self.hashes: dict[str, dict[str, str]] = {}
        self.keys: dict[str, str] = {}

    async def hgetall(self, name: str) -> dict[str, str]:
        return self.hashes.get(name, {})

    async def hset(self, name: str, key: str, value: str) -> int:
        if name not in self.hashes:
            self.hashes[name] = {}
        self.hashes[name][key] = value
        return 1

    async def hdel(self, name: str, *keys: str) -> int:
        count = 0
        if name in self.hashes:
            for k in keys:
                if k in self.hashes[name]:
                    del self.hashes[name][k]
                    count += 1
        return count

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.keys[key] = value
        return True

    async def get(self, key: str) -> str | None:
        return self.keys.get(key)

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self.keys.get(k) for k in keys]

    def pipeline(self) -> MockRedisPipeline:
        return MockRedisPipeline(self)


# ============================================================================
# Test 1: Semantic Cache Hit (< 15ms latency and source: "cache")
# ============================================================================
@pytest.mark.asyncio
async def test_semantic_cache_hit_and_latency(monkeypatch):
    """
    Test 1: Send the same query twice.
    Confirm the second query is a cache hit returning source: 'cache' in under 15ms.
    """
    mock_redis = MockRedis()
    cache = SemanticCache(redis_client=mock_redis, threshold=0.96)

    dummy_embedding = [0.1] * 1536
    mock_embedder = AsyncMock()
    mock_embedder.embed_text = AsyncMock(return_value=dummy_embedding)

    # First query: Cache Miss -> Populated
    res1 = await process_query(
        query="What is the refund policy?",
        tenant_id="tenant-test",
        user_id="user-123",
        redis_client=mock_redis,
        embedder=mock_embedder,
        cache=cache,
    )
    assert res1["hyde_used"] is True
    assert "chunks" in res1

    # Store answer in semantic cache
    await cache.set("What is the refund policy?", dummy_embedding, "Refunds are processed within 14 days.")

    # Second query: Cache HIT -> returns source: "cache" in < 15ms
    t0 = perf_counter()
    res2 = await process_query(
        query="What is the refund policy?",
        tenant_id="tenant-test",
        user_id="user-123",
        redis_client=mock_redis,
        embedder=mock_embedder,
        cache=cache,
    )
    duration_ms = (perf_counter() - t0) * 1000

    assert res2.get("source") == "cache"
    assert res2.get("answer") == "Refunds are processed within 14 days."
    assert res2.get("latency_ms") < 15.0
    assert duration_ms < 15.0


# ============================================================================
# Test 2: Query Expansion (original first + alternatives)
# ============================================================================
@pytest.mark.asyncio
async def test_query_expansion():
    """
    Test 2: Verify expand_query() returns a list with the original query first,
    followed by the 3 alternative variations.
    """
    # Mock LLM returning JSON array of alternative search phrases
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=json.dumps([
                    "employee annual leave rules",
                    "holiday entitlement for staff",
                    "vacation policy details",
                ])
            )
        )
    ]
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)

    query = "annual leave policy"
    expanded = await expand_query(query, llm_client=mock_llm)

    assert isinstance(expanded, list)
    assert len(expanded) == 4
    # Verify original query is always first
    assert expanded[0] == query
    assert "employee annual leave rules" in expanded
    assert "holiday entitlement for staff" in expanded
    assert "vacation policy details" in expanded


# ============================================================================
# Test 3: Router Classification ("What is Alice's department?" -> MULTI_HOP_GRAPH)
# ============================================================================
@pytest.mark.asyncio
async def test_router_classification():
    """
    Test 3: Send 'What is Alice's department?' and confirm route is classified as MULTI_HOP_GRAPH.
    """
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="MULTI_HOP_GRAPH"))]
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)

    route_with_llm = await classify_route("What is Alice's department?", llm_client=mock_llm)
    assert route_with_llm == ROUTE_MULTI_HOP_GRAPH

    # Also test offline / fallback heuristic
    route_heuristic = await classify_route("What is Alice's department?", llm_client=None)
    assert route_heuristic == ROUTE_MULTI_HOP_GRAPH


# ============================================================================
# Test 4: Pipeline Orchestration (full flow)
# ============================================================================
@pytest.mark.asyncio
async def test_pipeline_orchestration(monkeypatch):
    """
    Test 4: Verify process_query() executes the full pre-retrieval flow and returns
    all expected keys: chunks, route, query_variants, hyde_used.
    """
    from app.retrieval import engine

    mock_retrieve = AsyncMock(return_value=[
        {"id": "doc-1", "content": "Refunds take 14 business days.", "score": 0.95}
    ])
    monkeypatch.setattr(engine, "retrieve", mock_retrieve)

    mock_redis = MockRedis()
    cache = SemanticCache(redis_client=mock_redis)

    mock_embedder = AsyncMock()
    mock_embedder.embed_text = AsyncMock(return_value=[0.05] * 1536)

    # Mock LLM for query expansion & HyDE
    mock_llm = AsyncMock()
    mock_llm_response = MagicMock()
    mock_llm_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(["refund procedure", "money back policy"])))
    ]
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_llm_response)

    result = await process_query(
        query="What is the refund policy?",
        tenant_id="tenant-abc",
        user_id="user-456",
        redis_client=mock_redis,
        llm_client=mock_llm,
        embedder=mock_embedder,
        cache=cache,
    )

    # Assert all expected keys exist and have correct types
    assert "chunks" in result
    assert "route" in result
    assert "query_variants" in result
    assert "hyde_used" in result

    assert isinstance(result["chunks"], list)
    assert len(result["chunks"]) == 1
    assert result["chunks"][0]["id"] == "doc-1"
    assert result["route"] == ROUTE_FACTUAL_VECTOR
    assert result["hyde_used"] is True
    assert len(result["query_variants"]) >= 1
    assert result["query_variants"][0] == "What is the refund policy?"


# ============================================================================
# Additional Comprehensive Tests for Agentic Components
# ============================================================================
@pytest.mark.asyncio
async def test_hyde_embedding_generation():
    """Verify generate_hyde_embedding produces embedding from hypothetical text."""
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Employees receive 25 days of paid annual leave each year."))
    ]
    mock_llm.chat.completions.create = AsyncMock(return_value=mock_response)

    mock_embedder = AsyncMock()
    mock_embedder.embed_text = AsyncMock(return_value=[0.123] * 1536)

    emb = await generate_hyde_embedding("leave policy", llm_client=mock_llm, embedder=mock_embedder)
    assert isinstance(emb, list)
    assert len(emb) == 1536
    # Verify embed_text was called with the hypothetical answer text
    mock_embedder.embed_text.assert_awaited_once_with("Employees receive 25 days of paid annual leave each year.")


@pytest.mark.asyncio
async def test_router_all_strategies():
    """Verify all 4 routing strategies classify correctly."""
    assert await classify_route("Hello, how are you?") == ROUTE_GREETING_DIRECT
    assert await classify_route("How many queries were made last week?") == ROUTE_ANALYTICAL_SQL
    assert await classify_route("What rules apply to employees in London hired before 2022?") == ROUTE_MULTI_HOP_GRAPH
    assert await classify_route("What does the refund policy say?") == ROUTE_FACTUAL_VECTOR


@pytest.mark.asyncio
async def test_direct_greeting_skips_retrieval(monkeypatch):
    """Verify GREETING_DIRECT route returns direct answer and skips retrieval."""
    from app.retrieval import engine

    mock_retrieve = AsyncMock()
    monkeypatch.setattr(engine, "retrieve", mock_retrieve)

    mock_redis = MockRedis()
    cache = SemanticCache(redis_client=mock_redis)

    result = await process_query(
        query="Hello there, how are you?",
        tenant_id="tenant-1",
        user_id="user-1",
        redis_client=mock_redis,
        cache=cache,
    )

    assert result["route"] == ROUTE_GREETING_DIRECT
    assert result["source"] == "direct"
    assert "answer" in result
    assert result["chunks"] == []
    assert result["hyde_used"] is False
    mock_retrieve.assert_not_called()
