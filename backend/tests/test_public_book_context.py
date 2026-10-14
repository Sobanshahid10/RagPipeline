import hashlib
import json

import pytest

from backend.app.retrieval.public_book_context import build_context

SOURCE_HASH = "a" * 64


def hit(record_id: str, body: str, *, scope: str = "public_book"):
    content = f"Section: Book > Education\n{body}"
    return {
        "id": record_id,
        "content": content,
        "citation": f"PUBLIC_KNOWLEDGE_BOOK.md:L{record_id}",
        "rerank_score": 0.04,
        "metadata": {
            "access_scope": scope,
            "source_name": "PUBLIC_KNOWLEDGE_BOOK.md",
            "source_sha256": SOURCE_HASH,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "citation_label": f"PUBLIC_KNOWLEDGE_BOOK.md:L{record_id}",
            "section_title": "Education",
            "section_owner": "umar",
            "source_line_start": 1,
            "source_line_end": 1,
        },
    }


def reranked(*hits):
    return {"question": "What happened?", "source_sha256": SOURCE_HASH, "hits": list(hits)}


def test_context_is_bounded_and_cited_without_truncating_evidence():
    result = build_context(reranked(hit("1", "A short fact."), hit("2", "B" * 1000), hit("3", "Another fact.")), max_context_bytes=500)
    parsed = json.loads(result["context"])
    assert [source["source_id"] for source in parsed["sources"]] == ["S1", "S2"]
    assert [source["chunk_id"] for source in parsed["sources"]] == ["1", "3"]
    assert parsed["sources"][0]["text"] == "A short fact."
    assert result["context_bytes"] <= 500
    assert {"id": "2", "reason": "byte_budget"} in result["skipped"]
    assert result["source_manifest"][0]["citation"] == "PUBLIC_KNOWLEDGE_BOOK.md:L1"


def test_duplicate_and_source_limit_are_explicit():
    result = build_context(reranked(hit("1", "Same."), hit("1", "Same."), hit("2", "Other.")), max_sources=1)
    assert result["included_count"] == 1
    assert result["skipped"] == [
        {"id": "1", "reason": "duplicate_id"},
        {"id": "2", "reason": "source_limit"},
    ]


def test_nonpublic_or_tampered_evidence_is_rejected():
    with pytest.raises(ValueError, match="Non-public"):
        build_context(reranked(hit("1", "Private fact.", scope="private")))
    altered = hit("1", "Original")
    altered["content"] = "Changed"
    with pytest.raises(ValueError, match="Content hash mismatch"):
        build_context(reranked(altered))
