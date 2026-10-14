import json

import pytest

from app.api.public_book import _parse_answer, _retrieval_query


def test_public_book_citations_normalize_common_provider_forms():
    response = {
        "answer": "First claim 【S1】. Second claim [S2, S1].",
        "citations": ["S1", "S2", "S1"],
        "abstained": False,
    }
    parsed = _parse_answer(json.dumps(response), ["S1", "S2"])
    assert parsed["answer"] == "First claim [S1]. Second claim [S2][S1]."
    assert parsed["citations"] == ["S1", "S2"]


def test_public_book_rejects_unretrieved_citation():
    response = {"answer": "Unsupported [S9].", "citations": ["S9"], "abstained": False}
    with pytest.raises(ValueError, match="missing or mismatched"):
        _parse_answer(json.dumps(response), ["S1"])


def test_public_book_repairs_exact_abstention_flag_only():
    response = {
        "answer": "I don't have enough information in the provided public sources to answer that.",
        "citations": [], "abstained": False,
    }
    assert _parse_answer(json.dumps(response), [])['abstained'] is True


def test_public_book_removes_citation_from_exact_abstention():
    response = {
        "answer": "I don't have enough information in the provided public sources to answer that. [S1]",
        "citations": ["S1"], "abstained": False,
    }
    parsed = _parse_answer(json.dumps(response), ["S1"])
    assert parsed["abstained"] is True
    assert parsed["citations"] == []
    assert "[S1]" not in parsed["answer"]


def test_public_book_removes_citation_before_abstention_period():
    response = {
        "answer": "I don't have enough information in the provided public sources to answer that [S1].",
        "citations": ["S1"], "abstained": False,
    }
    parsed = _parse_answer(json.dumps(response), ["S1"])
    assert parsed["abstained"] is True
    assert parsed["citations"] == []


def test_portfolio_opinion_search_keeps_original_question_for_generation():
    expanded, owner = _retrieval_query("What is the worst part of Omer's portfolio?")
    assert "self-reported limits" in expanded
    assert owner == "umar"
    unchanged, owner = _retrieval_query("What is Soban's current city?")
    assert unchanged == "What is Soban's current city?"
    assert owner is None
