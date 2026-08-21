"""
Semantic Vector Cache Module with Redis & Cosine Similarity.

Stores query embeddings and answers in Redis, performing cosine similarity lookups
to serve cached answers in < 15ms for semantically identical or near-identical queries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

CACHE_HASH_KEY = "rag:cache:entries"
CACHE_KEY_PREFIX = "rag:cache:"


class SemanticCache:
    """
    Semantic vector cache using Redis for persistent storage and NumPy for vector similarity.
    """

    def __init__(self, redis_client: Optional[Any] = None, threshold: float = 0.96) -> None:
        self.redis_client = redis_client
        self.threshold = threshold
        self._in_memory_entries: dict[str, dict[str, Any]] = {}

    def _compute_key(self, query: str) -> str:
        return hashlib.sha256(query.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        norm_a = np.linalg.norm(vec_a)
        norm_b = np.linalg.norm(vec_b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

    async def get(self, query_embedding: list[float]) -> str | None:
        """
        Fetch cached entries from Redis hash `rag:cache:entries`, compute cosine similarity,
        and return the best answer if similarity >= threshold.
        """
        if not query_embedding:
            return None

        query_vec = np.array(query_embedding, dtype=np.float32)
        now = time.time()
        entries_data: dict[Any, Any] = {}

        if self.redis_client is not None:
            try:
                entries_data = await self.redis_client.hgetall(CACHE_HASH_KEY)
            except Exception as exc:
                logger.warning("Redis semantic cache fetch failed: %s. Falling back to local store.", exc)
                entries_data = self._in_memory_entries
        else:
            entries_data = self._in_memory_entries

        if not entries_data:
            return None

        best_score = -1.0
        best_answer: str | None = None
        expired_keys: list[Any] = []

        for k, raw_entry in entries_data.items():
            try:
                if isinstance(raw_entry, bytes):
                    raw_entry = raw_entry.decode("utf-8")
                
                entry = json.loads(raw_entry) if isinstance(raw_entry, str) else raw_entry
                expires_at = entry.get("expires_at")
                if expires_at is not None and now > expires_at:
                    expired_keys.append(k)
                    continue

                cached_embedding = entry.get("embedding")
                if not cached_embedding or not isinstance(cached_embedding, list):
                    continue

                cached_vec = np.array(cached_embedding, dtype=np.float32)
                sim = self._cosine_similarity(query_vec, cached_vec)

                if sim > best_score:
                    best_score = sim
                    best_answer = entry.get("answer")
            except Exception as parse_err:
                logger.debug("Failed parsing cache entry: %s", parse_err)
                continue

        # Asynchronously clean up expired hash keys if client is active or in-memory
        for exp_k in expired_keys:
            if isinstance(exp_k, str):
                self._in_memory_entries.pop(exp_k, None)

        if expired_keys and self.redis_client is not None:
            try:
                await self.redis_client.hdel(CACHE_HASH_KEY, *expired_keys)
            except Exception:
                pass

        if best_score >= self.threshold and best_answer is not None:
            logger.debug("Semantic cache hit with similarity score %.4f >= threshold %.4f", best_score, self.threshold)
            return best_answer

        return None

    async def set(
        self,
        query: str,
        embedding: list[float],
        answer: str,
        ttl: int = 3600,
    ) -> None:
        """
        Store `{embedding: list, answer: str}` in Redis with key `rag:cache:{sha256(query)[:12]}`
        and add to hash `rag:cache:entries`.
        """
        if not query or not embedding or not answer:
            return

        key_id = self._compute_key(query)
        full_key = f"{CACHE_KEY_PREFIX}{key_id}"
        payload = {
            "embedding": embedding,
            "answer": answer,
            "expires_at": time.time() + ttl,
        }
        json_payload = json.dumps(payload)

        # Store in local memory map
        self._in_memory_entries[key_id] = payload

        if self.redis_client is not None:
            try:
                # Set specific key with TTL
                await self.redis_client.set(full_key, json_payload, ex=ttl)
                # Set in entries hash
                await self.redis_client.hset(CACHE_HASH_KEY, key_id, json_payload)
            except Exception as exc:
                logger.warning("Failed storing semantic cache in Redis: %s", exc)
