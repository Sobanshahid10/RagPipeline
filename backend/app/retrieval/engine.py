"""Day 6 tri-hybrid retrieval orchestrator."""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any

from app.config import settings
from app.ingestion import embedder
from app.retrieval import bm25_search, fusion, graph_search, vector_search
from app.retrieval.compressor import compress_context
from app.retrieval.reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)
_reranker = CrossEncoderReranker()


async def retrieve(query: str, tenant_id: str) -> list[dict[str, Any]]:
    """Run dense, lexical, and graph retrieval through fusion and compression."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    started = perf_counter()
    redis_client: Any | None = None
    try:
        try:
            import redis.asyncio as aioredis

            redis_client = aioredis.from_url(settings.REDIS_URL)
        except Exception as exc:
            logger.debug("Redis embedding cache unavailable: %s", exc)

        embedding = await embedder.embed_text(cleaned_query, redis_client=redis_client)
        embedded_at = perf_counter()

        bm25_results, vector_results, graph_results = await asyncio.gather(
            bm25_search.bm25_search(cleaned_query, tenant_id, top_k=20),
            vector_search.vector_search(embedding, tenant_id, top_k=20),
            graph_search.graph_search(cleaned_query, tenant_id, max_hops=3, top_k=15),
        )
        searched_at = perf_counter()

        fused = fusion.reciprocal_rank_fusion(
            {"bm25": bm25_results, "vector": vector_results, "graph": graph_results},
            k=60,
            top_n=50,
        )
        fused_at = perf_counter()

        reranked = await asyncio.to_thread(_reranker.rerank, cleaned_query, fused[:40], 5)
        reranked_at = perf_counter()
        compressed = await asyncio.to_thread(compress_context, reranked, cleaned_query, 0.5)
        finished = perf_counter()

        logger.info(
            "retrieval tenant=%s embedding_ms=%.1f search_ms=%.1f fusion_ms=%.1f "
            "rerank_ms=%.1f compression_ms=%.1f total_ms=%.1f",
            tenant_id,
            (embedded_at - started) * 1000,
            (searched_at - embedded_at) * 1000,
            (fused_at - searched_at) * 1000,
            (reranked_at - fused_at) * 1000,
            (finished - reranked_at) * 1000,
            (finished - started) * 1000,
        )
        return compressed[:5]
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass
