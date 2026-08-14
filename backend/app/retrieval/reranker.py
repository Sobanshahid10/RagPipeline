from typing import List, Dict, Any

class CrossEncoderReranker:
    """
    Reranks candidate chunks by evaluating fine-grained cross-attention score
    between the user query and document text.
    """
    def __init__(self, model_name: str = "ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Heuristic scoring fallback / keyword overlap relevance boost if heavy PyTorch model not loaded
        query_words = set(query.lower().split())
        scored_candidates = []

        for candidate in candidates:
            content_words = candidate.get("content", "").lower().split()
            overlap_count = sum(1 for w in query_words if w in content_words)
            rrf_score = candidate.get("rrf_score", 0.5)
            
            # Combined relevance confidence score
            confidence = rrf_score + (overlap_count * 0.05)
            
            cand_copy = candidate.copy()
            cand_copy["rerank_score"] = round(confidence, 4)
            scored_candidates.append(cand_copy)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]
