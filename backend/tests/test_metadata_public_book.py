"""Checks metadata integrity without pretending it verifies source claims."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.ingestion.chunk_public_book import chunk_normalized_book
from app.ingestion.markdown_book import parse_markdown_book
from app.ingestion.metadata_public_book import add_public_book_metadata, section_owner
from app.ingestion.normalize_book import normalize_parsed_book


ROOT = Path(__file__).resolve().parents[2]


def _artifacts():
    normalized = normalize_parsed_book(parse_markdown_book(ROOT / "PUBLIC_KNOWLEDGE_BOOK.md"))
    chunks = chunk_normalized_book(normalized)
    return chunks, add_public_book_metadata(chunks)


def test_metadata_preserves_chunk_identity_and_text():
    chunks, enriched = _artifacts()
    assert enriched["record_count"] == chunks["chunk_count"] == 177
    assert [record["id"] for record in enriched["records"]] == [chunk["id"] for chunk in chunks["chunks"]]
    assert [record["content"] for record in enriched["records"]] == [chunk["content"] for chunk in chunks["chunks"]]
    assert all(record["metadata"]["content_sha256"] == hashlib.sha256(record["content"].encode()).hexdigest()
               for record in enriched["records"])
    assert all(record["metadata"]["source_sha256"] == chunks["source_sha256"] for record in enriched["records"])


def test_section_owner_is_structural_and_citations_point_to_source():
    _, enriched = _artifacts()
    by_line = {record["metadata"]["source_line_start"]: record for record in enriched["records"]}

    work = by_line[41]["metadata"]
    assert work["section_owner"] == "umar"
    assert work["citation_label"] == "PUBLIC_KNOWLEDGE_BOOK.md:L41"
    assert work["table_header_lines"] == [39, 40]
    assert by_line[18]["metadata"]["section_owner"] == "soban"
    assert by_line[270]["metadata"]["section_owner"] == "shared"
    assert section_owner(["Book", "9. Source catalog"]) == "general"


def test_rejects_mixed_source_versions():
    chunks, _ = _artifacts()
    chunks["chunks"][0]["source_sha256"] = "different"
    with pytest.raises(ValueError, match="different source version"):
        add_public_book_metadata(chunks)
