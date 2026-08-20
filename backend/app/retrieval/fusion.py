"""Rank fusion for heterogeneous retrieval result sets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def reciprocal_rank_fusion(
    result_sets: Mapping[str, Sequence[dict[str, Any]]] | Sequence[dict[str, Any]],
    vector_results: Sequence[dict[str, Any]] | None = None,
    k: int = 60,
    top_n: int = 50,
) -> list[dict[str, Any]]:
    """Fuse ranked result lists with Reciprocal Rank Fusion.

    The preferred input is ``{"bm25": [...], "vector": [...], "graph": [...]}``.
    The legacy two-list form remains supported for callers built before Day 6.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    if top_n < 0:
        raise ValueError("top_n must be non-negative")

    ranked_sets = (
        result_sets.values()
        if isinstance(result_sets, Mapping)
        else (result_sets, vector_results or ())
    )
    scores: dict[str, float] = {}
    chunks: dict[str, dict[str, Any]] = {}

    for ranked_list in ranked_sets:
        seen_in_source: set[str] = set()
        for rank, item in enumerate(ranked_list):
            if "id" not in item:
                continue
            chunk_id = str(item["id"])
            if chunk_id in seen_in_source:
                continue
            seen_in_source.add(chunk_id)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
            chunks.setdefault(chunk_id, dict(item))

    ordered_ids = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    fused: list[dict[str, Any]] = []
    for chunk_id in ordered_ids[:top_n]:
        chunk = chunks[chunk_id].copy()
        chunk["rrf_score"] = scores[chunk_id]
        fused.append(chunk)
    return fused
