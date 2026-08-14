from app.ingestion.chunking import split_into_sentences, sentence_aware_chunking, count_tokens

def test_split_into_sentences():
    text = "Enterprise RAG requires evaluation. Fast retrieval is essential! Do you agree?"
    sentences = split_into_sentences(text)
    assert len(sentences) == 3
    assert sentences[0] == "Enterprise RAG requires evaluation."
    assert sentences[1] == "Fast retrieval is essential!"
    assert sentences[2] == "Do you agree?"

def test_sentence_aware_chunking():
    paragraph = (
        "Retrieval-Augmented Generation (RAG) combines document retrieval with language generation. "
        "Dense vector search provides semantic proximity lookup. "
        "BM25 provides exact keyword matching for product numbers and codes. "
        "Reciprocal Rank Fusion merges both lists effectively. "
        "Cross-encoder reranking provides maximum accuracy for final generation context."
    )
    chunks = sentence_aware_chunking(paragraph, chunk_size=35, overlap=10, contextual_summary="RAG Architecture Overview")
    
    assert len(chunks) >= 2
    assert "RAG Architecture Overview" in chunks[0]["content"]
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[0]["token_count"] > 0

def test_count_tokens():
    text = "Production AI systems require evaluation pipelines."
    tok_count = count_tokens(text)
    assert tok_count > 0
