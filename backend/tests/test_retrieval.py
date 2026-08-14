from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.reranker import CrossEncoderReranker

def test_reciprocal_rank_fusion():
    bm25_list = [
        {"id": "doc1", "content": "Employee leave policy details"},
        {"id": "doc2", "content": "Company health insurance benefits"}
    ]
    vector_list = [
        {"id": "doc2", "content": "Company health insurance benefits"},
        {"id": "doc3", "content": "Dental coverage plan options"}
    ]

    fused = reciprocal_rank_fusion(bm25_list, vector_list, k=60, top_n=3)
    
    assert len(fused) == 3
    # doc2 appeared in both lists, so its RRF score should be highest
    assert fused[0]["id"] == "doc2"
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]

def test_cross_encoder_reranker():
    candidates = [
        {"id": "doc1", "content": "General employee benefits handbook.", "rrf_score": 0.03},
        {"id": "doc2", "content": "Dental coverage policy limits for employees.", "rrf_score": 0.025}
    ]
    query = "What is the dental coverage limit?"

    reranker = CrossEncoderReranker()
    reranked = reranker.rerank(query, candidates, top_k=1)

    assert len(reranked) == 1
    assert reranked[0]["id"] == "doc2"
    assert "rerank_score" in reranked[0]
