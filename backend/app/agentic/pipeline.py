"""Measured hybrid retrieval; no unscoped answer caching or unused expansion."""

import re
from time import perf_counter
from typing import Any
from app.retrieval import engine


async def process_query(
    query: str,
    tenant_id: str,
    user_id: str,
    redis_client=None,
    llm_client=None,
    embedder=None,
    cache=None,
    bypass_cache=False,
    document_ids=None,
) -> dict[str, Any]:
    started = perf_counter()
    if not query.strip():
        return {"chunks": [], "route": "HYBRID", "hyde_used": False, "latency_ms": 0}
    if re.fullmatch(
        r"(?:hi|hello|hey)(?: there)?[,.! ]*(?:how are you[?!]*)?",
        query.strip(),
        re.IGNORECASE,
    ):
        return {
            "answer": "Hello! Ask a question about your selected documents.",
            "source": "direct",
            "route": "GREETING_DIRECT",
            "chunks": [],
            "query_variants": [query.strip()],
            "hyde_used": False,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        }
    chunks = await engine.retrieve(query.strip(), tenant_id, document_ids=document_ids)
    return {
        "chunks": chunks,
        "route": "HYBRID",
        "query_variants": [query.strip()],
        "hyde_used": False,
        "latency_ms": round((perf_counter() - started) * 1000, 2),
    }
