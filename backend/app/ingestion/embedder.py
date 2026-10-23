"""
Embedding Generation & Redis Caching Module.

Provides single-text and batch embedding generation with:
1. Fast SHA-256 Redis vector caching (< 5ms hit latency, 30-day TTL)
2. OpenAI `text-embedding-3-small` (1536-dim) vector generation
3. Strict provider validation; failures never create synthetic index vectors
"""

import os
import json
import hashlib
import logging
from typing import List, Optional, Any
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Cache prefix and TTL
CACHE_PREFIX = "emb:"
DEFAULT_TTL = settings.EMBEDDING_CACHE_TTL  # 2,592,000 seconds (30 days)
EMBEDDING_DIM = settings.EMBEDDING_DIM  # 1536 dimensions


def embedding_identity() -> str:
    if settings.GEMINI_API_KEY:
        return f"gemini:{settings.EMBEDDING_MODEL}:{EMBEDDING_DIM}:v2"
    if settings.OPENAI_API_KEY:
        return f"openai:{settings.OPENAI_EMBEDDING_MODEL}:{EMBEDDING_DIM}:v2"
    raise RuntimeError(
        "An embedding provider must be configured before indexing or querying documents"
    )


def compute_cache_key(text: str) -> str:
    digest = hashlib.sha256(f"{embedding_identity()}:{text}".encode()).hexdigest()
    return f"emb:v2:{digest}"


def _validate_embeddings(vectors, count):
    import math

    if len(vectors) != count or any(
        len(vector) != EMBEDDING_DIM
        or any(type(x) not in (int, float) or not math.isfinite(x) for x in vector)
        or not any(vector)
        for vector in vectors
    ):
        raise RuntimeError("Embedding provider returned invalid vectors")
    return vectors


async def _fetch_gemini_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch 1536-dimensional embeddings from the current Gemini model."""
    try:
        import httpx

        model = settings.EMBEDDING_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
        requests = [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": t}]},
                "embedContentConfig": {"outputDimensionality": EMBEDDING_DIM},
            }
            for t in texts
        ]
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                url,
                json={"requests": requests},
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = [emb["values"] for emb in data.get("embeddings", [])]
            if len(embeddings) == len(texts) and all(
                len(emb) == EMBEDDING_DIM for emb in embeddings
            ):
                return embeddings
            raise RuntimeError(
                "Embedding provider returned invalid vector dimensions or count"
            )
    except Exception as err:
        raise RuntimeError(
            "Gemini embeddings unavailable; indexing was stopped"
        ) from err


async def _fetch_openai_embeddings(texts: List[str]) -> List[List[float]]:
    """Fetch embeddings in batch from OpenAI API."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await client.embeddings.create(
            input=texts, model=settings.OPENAI_EMBEDDING_MODEL, dimensions=EMBEDDING_DIM
        )
        return [data.embedding for data in response.data]
    except Exception as err:
        raise RuntimeError(
            "OpenAI embeddings unavailable; indexing was stopped"
        ) from err


async def embed_batch(
    texts: List[str], redis_client: Optional[Any] = None
) -> List[List[float]]:
    """
    Generate embeddings for a batch of text strings with Redis caching.

    - Checks Redis cache for each text using SHA-256 prefix key.
    - Collects cache misses and queries Gemini / OpenAI API in a single batch request.
    - Caches newly computed vectors in Redis with a 30-day TTL.
    - Returns all embeddings in the original input order.
    """
    if not texts:
        return []
    embedding_identity()
    if len(texts) > 32:
        combined = []
        for offset in range(0, len(texts), 32):
            combined.extend(
                await embed_batch(texts[offset : offset + 32], redis_client)
            )
        return combined

    results: List[Optional[List[float]]] = [None] * len(texts)
    keys = [compute_cache_key(t) for t in texts]
    miss_indices: List[int] = []
    miss_texts: List[str] = []

    # 1. Query Redis Cache
    if redis_client is not None:
        try:
            cached_values = await redis_client.mget(keys)
            for idx, raw_val in enumerate(cached_values):
                if raw_val is not None:
                    if isinstance(raw_val, bytes):
                        raw_val = raw_val.decode("utf-8")
                    results[idx] = _validate_embeddings([json.loads(raw_val)], 1)[0]
                else:
                    miss_indices.append(idx)
                    miss_texts.append(texts[idx])
        except Exception as redis_err:
            logger.warning(f"Redis cache lookup failed: {redis_err}. Bypassing cache.")
            miss_indices = list(range(len(texts)))
            miss_texts = list(texts)
    else:
        miss_indices = list(range(len(texts)))
        miss_texts = list(texts)

    # 2. Generate embeddings for cache misses
    if miss_texts:
        if settings.GEMINI_API_KEY:
            new_embeddings = await _fetch_gemini_embeddings(miss_texts)
        elif settings.OPENAI_API_KEY:
            new_embeddings = await _fetch_openai_embeddings(miss_texts)
        else:
            raise RuntimeError("No embedding provider configured")
        _validate_embeddings(new_embeddings, len(miss_texts))

        # 3. Store new embeddings in results and Redis
        cache_pipe = redis_client.pipeline() if redis_client is not None else None
        for i, emb in enumerate(new_embeddings):
            orig_idx = miss_indices[i]
            results[orig_idx] = emb

            if cache_pipe is not None:
                try:
                    cache_pipe.set(keys[orig_idx], json.dumps(emb), ex=DEFAULT_TTL)
                except Exception:
                    pass

        if cache_pipe is not None:
            try:
                await cache_pipe.execute()
            except Exception as pipe_err:
                logger.warning(f"Failed to batch write embeddings to Redis: {pipe_err}")

    return [r for r in results if r is not None]


async def embed_text(text: str, redis_client: Optional[Any] = None) -> List[float]:
    """
    Generate embedding vector for a single text string with Redis caching.
    """
    embeddings = await embed_batch([text], redis_client=redis_client)
    if not embeddings:
        raise RuntimeError("No embedding returned")
    return embeddings[0]
