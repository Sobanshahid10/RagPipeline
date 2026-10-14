import pytest

from backend.app.retrieval.public_book_rerank import lexical_terms, rerank_candidates


def hit(record_id, owner, *, score=0.5):
    return {
        "id": record_id,
        "content": f"Evidence {record_id}",
        "metadata": {"section_owner": owner, "citation_label": f"BOOK:L{record_id}"},
        "citation": f"BOOK:L{record_id}",
        "score": score,
    }


def test_lexical_terms_skip_repeated_names_and_keep_distinct_topic_terms():
    terms = lexical_terms("What did Umar and Soban build in Docinsight, and what did AInsight add?")
    assert terms == ["build", "docinsight", "ainsight", "add"]
    assert lexical_terms("What is it?") == []


def test_lexical_candidate_can_recover_a_dense_miss():
    dense = [hit(f"d{i}", "umar", score=1 - i / 100) for i in range(1, 41)]
    lexical = [hit("d6", "umar")] + [hit(f"d{i}", "umar") for i in range(10, 40)]
    result = rerank_candidates(dense, lexical, top_k=5)
    assert "d6" in {item["id"] for item in result}
    assert {"d1", "d2"} <= {item["id"] for item in result}
    assert all(item["citation"] for item in result)


def test_owner_filter_is_explicit_and_keeps_shared_context():
    dense = [hit("s", "soban"), hit("u", "umar"), hit("shared", "shared"), hit("general", "general")]
    result = rerank_candidates(dense, [], owner="umar", top_k=5)
    assert {item["id"] for item in result} == {"u", "shared", "general"}
    assert all(item["metadata"]["section_owner"] != "soban" for item in result)
    with pytest.raises(ValueError, match="owner"):
        rerank_candidates(dense, [], owner="unknown")
