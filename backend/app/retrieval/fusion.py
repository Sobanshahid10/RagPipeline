from typing import List, Dict, Any

def reciprocal_rank_fusion(
    bm25_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    k: int = 60,
    top_n: int = 10
) -> List[Dict[str, Any]]:
    """
    Combines ranked lists from BM25 sparse search and pgvector dense search
    using Reciprocal Rank Fusion (RRF) formula:
    RRF(d) = sum( 1 / (k + rank_i(d)) )
    """
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, Dict[str, Any]] = {}

    # Process BM25 ranked items
    for rank, item in enumerate(bm25_results):
        chunk_id = str(item["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + (rank + 1)))
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = item

    # Process Vector ranked items
    for rank, item in enumerate(vector_results):
        chunk_id = str(item["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + (1.0 / (k + (rank + 1)))
        if chunk_id not in chunk_map:
            chunk_map[chunk_id] = item

    # Sort chunks by fused RRF score descending
    sorted_chunk_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)

    fused_results = []
    for cid in sorted_chunk_ids[:top_n]:
        chunk = chunk_map[cid].copy()
        chunk["rrf_score"] = round(scores[cid], 5)
        fused_results.append(chunk)

    return fused_results
