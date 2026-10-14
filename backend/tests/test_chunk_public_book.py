"""Checks that public-book chunks remain bounded, source-linked, and complete."""

from __future__ import annotations

import re
from pathlib import Path

from app.ingestion.chunk_public_book import _split_oversize, chunk_normalized_book
from app.ingestion.markdown_book import parse_markdown_book
from app.ingestion.normalize_book import normalize_parsed_book


ROOT = Path(__file__).resolve().parents[2]


def _book_chunks():
    source = ROOT / "PUBLIC_KNOWLEDGE_BOOK.md"
    normalized = normalize_parsed_book(parse_markdown_book(source))
    return source, normalized, chunk_normalized_book(normalized)


def test_public_book_chunks_cover_each_unit_without_mixing_sections():
    source, normalized, artifact = _book_chunks()
    chunks = artifact["chunks"]
    assert artifact["source_unit_count"] == 177
    assert len(chunks) == artifact["chunk_count"]
    assert len({chunk["id"] for chunk in chunks}) == len(chunks)
    assert all(chunk["character_count"] == len(chunk["content"]) <= 1800 for chunk in chunks)
    assert all(chunk["content"].startswith("Section: " + " > ".join(chunk["heading_path"])) for chunk in chunks)
    assert all(chunk["source_sha256"] == normalized["source_sha256"] for chunk in chunks)

    nonempty = {i for i, block in enumerate(normalized["blocks"]) if block["type"] not in {"blank", "heading"}}
    assert {chunk["source_block_index"] for chunk in chunks} == nonempty

    # Every public source URL survives chunking.
    urls = re.findall(r"\[[^\]]+\]\((https?://[^)\s]+)\)", source.read_text(encoding="utf-8"))
    assert urls and all(any(url in chunk["content"] for chunk in chunks) for url in urls)


def test_table_rows_keep_header_meaning_and_exact_line_reference():
    _, _, artifact = _book_chunks()
    work = next(chunk for chunk in artifact["chunks"] if chunk["unit_type"] == "table" and chunk["start_line"] == 41)
    assert work["end_line"] == 41
    assert work["table_header_lines"] == [39, 40]
    assert "Period: June 2026–present" in work["content"]
    assert "Role: Agentic AI Developer Intern, Techohub, Lahore" in work["content"]
    assert work["heading_path"][-1] == "2.2 Work and practical experience"


def test_oversized_future_unit_splits_without_losing_words():
    text = ("A first sentence with a date 6 October 2025. " * 15).strip()
    parts = _split_oversize(text, 180)
    assert len(parts) > 1
    assert all(len(part) <= 180 for part in parts)
    assert re.sub(r"\s+", " ", " ".join(parts)) == text


def test_repeat_run_has_stable_chunk_ids():
    _, normalized, first = _book_chunks()
    second = chunk_normalized_book(normalized)
    assert [chunk["id"] for chunk in first["chunks"]] == [chunk["id"] for chunk in second["chunks"]]
