"""
Pre-Retrieval Orchestration Pipeline Module.

Orchestrates semantic caching, strategy routing, parallel query expansion,
HyDE embedding generation, and tri-hybrid retrieval execution.
"""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
from typing import Any, Optional

from app.agentic.cache import SemanticCache
from app.agentic.expander import expand_query
from app.agentic.hyde import generate_hyde_embedding
from app.agentic.router import ROUTE_GREETING_DIRECT, classify_route
from app.config import settings
from app.retrieval import engine

logger = logging.getLogger(__name__)

# Module-level default semantic cache
_global_cache: Optional[SemanticCache] = None


def get_default_cache(redis_client: Optional[Any] = None) -> SemanticCache:
    """Get or initialize default SemanticCache instance."""
    global _global_cache
    if redis_client is not None:
        return SemanticCache(redis_client=redis_client)
    if _global_cache is None:
        try:
            import redis.asyncio as aioredis
            r_client = aioredis.from_url(settings.REDIS_URL)
            _global_cache = SemanticCache(redis_client=r_client)
        except Exception as exc:
            logger.debug("Redis unavailable for global cache: %s. Using in-memory fallback.", exc)
            _global_cache = SemanticCache(redis_client=None)
    return _global_cache


async def _generate_direct_greeting(query: str, llm_client: Optional[Any] = None) -> str:
    """Generate a friendly direct response for greeting queries without document retrieval."""
    if llm_client is not None:
        try:
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                resp = await llm_client.chat.completions.create(
                    model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "You are a helpful and polite enterprise AI assistant."},
                        {"role": "user", "content": query},
                    ],
                    max_tokens=60,
                )
                return resp.choices[0].message.content.strip()
            elif callable(llm_client):
                res = await llm_client(query)
                return str(res).strip()
        except Exception as exc:
            logger.debug("Direct LLM greeting failed: %s", exc)

    return "Hello! I am your AI assistant. How can I help you today?"


async def process_query(
    query: str,
    tenant_id: str,
    user_id: str,
    redis_client: Optional[Any] = None,
    llm_client: Optional[Any] = None,
    embedder: Optional[Any] = None,
    cache: Optional[SemanticCache] = None,
) -> dict[str, Any]:
    """
    Execute the end-to-end agentic pre-retrieval pipeline:
    1. Generate query embedding.
    2. Check SemanticCache -> if HIT: return {answer, source: 'cache', latency_ms}.
    3. Classify route via router.classify_route().
    4. If route == GREETING_DIRECT: return direct LLM response and skip retrieval.
    5. In parallel via asyncio.gather():
       - Expand query via expand_query().
       - Generate HyDE embedding via generate_hyde_embedding().
    6. Run retrieval.engine.retrieve() with query context.
    7. Return {chunks, route, query_variants, hyde_used: True/False, latency_ms}.
    """
    started = perf_counter()
    cleaned_query = query.strip()
    if not cleaned_query:
        return {
            "chunks": [],
            "route": "FACTUAL_VECTOR",
            "query_variants": [],
            "hyde_used": False,
            "latency_ms": 0.0,
        }

    # Initialize or inject semantic cache
    semantic_cache = cache or get_default_cache(redis_client=redis_client)

    # 1. Generate query embedding
    if embedder is not None:
        if hasattr(embedder, "embed_text"):
            query_embedding_res = embedder.embed_text(cleaned_query)
            query_embedding = await query_embedding_res if hasattr(query_embedding_res, "__await__") else query_embedding_res
        elif callable(embedder):
            query_embedding_res = embedder(cleaned_query)
            query_embedding = await query_embedding_res if hasattr(query_embedding_res, "__await__") else query_embedding_res
        else:
            from app.ingestion import embedder as app_embedder
            query_embedding = await app_embedder.embed_text(cleaned_query, redis_client=redis_client)
    else:
        from app.ingestion import embedder as app_embedder
        query_embedding = await app_embedder.embed_text(cleaned_query, redis_client=redis_client)

    # 2. Check Semantic Cache
    cached_answer = await semantic_cache.get(query_embedding)
    if cached_answer is not None:
        latency_ms = round((perf_counter() - started) * 1000, 2)
        logger.info("Semantic cache HIT for tenant=%s query='%s' (%.2f ms)", tenant_id, cleaned_query, latency_ms)
        return {
            "answer": cached_answer,
            "source": "cache",
            "latency_ms": latency_ms,
        }

    # 3. Classify route
    route = await classify_route(cleaned_query, llm_client=llm_client)

    # 4. Handle GREETING_DIRECT
    if route == ROUTE_GREETING_DIRECT:
        direct_answer = await _generate_direct_greeting(cleaned_query, llm_client=llm_client)
        latency_ms = round((perf_counter() - started) * 1000, 2)
        logger.info("Direct greeting routed for tenant=%s query='%s' (%.2f ms)", tenant_id, cleaned_query, latency_ms)
        return {
            "answer": direct_answer,
            "source": "direct",
            "route": route,
            "chunks": [],
            "query_variants": [cleaned_query],
            "hyde_used": False,
            "latency_ms": latency_ms,
        }

    # 5. Expand query & Generate HyDE embedding in parallel
    expansion_task = expand_query(cleaned_query, llm_client=llm_client)
    hyde_task = generate_hyde_embedding(cleaned_query, llm_client=llm_client, embedder=embedder)

    query_variants, hyde_embedding = await asyncio.gather(expansion_task, hyde_task)

    # 6. Run retrieval engine
    try:
        chunks = await engine.retrieve(cleaned_query, tenant_id)
    except Exception as ret_err:
        logger.error("Retrieval engine execution failed: %s", ret_err, exc_info=True)
        chunks = []

    latency_ms = round((perf_counter() - started) * 1000, 2)
    logger.info(
        "Agentic pipeline finished tenant=%s route=%s variants=%d chunks=%d (%.2f ms)",
        tenant_id,
        route,
        len(query_variants),
        len(chunks),
        latency_ms,
    )

    return {
        "chunks": chunks,
        "route": route,
        "query_variants": query_variants,
        "hyde_used": True,
        "latency_ms": latency_ms,
    }
