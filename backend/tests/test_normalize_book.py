"""Checks that stage-two cleaning improves readability without changing evidence."""

from __future__ import annotations

import re
from pathlib import Path

from app.ingestion.markdown_book import parse_markdown_book
from app.ingestion.normalize_book import clean_inline, normalize_parsed_book


ROOT = Path(__file__).resolve().parents[2]


def test_public_book_keeps_provenance_links_and_claim_qualifiers():
    parsed = parse_markdown_book(ROOT / "PUBLIC_KNOWLEDGE_BOOK.md")
    cleaned = normalize_parsed_book(parsed)

    assert cleaned["source_sha256"] == parsed["source_sha256"]
    assert len(cleaned["blocks"]) == len(parsed["blocks"])
    assert [(b["start_line"], b["end_line"], b["type"]) for b in cleaned["blocks"]] == [
        (b["start_line"], b["end_line"], b["type"]) for b in parsed["blocks"]
    ]

    text = "\n".join(block["text"] for block in cleaned["blocks"])
    for important in (
        "Omer, Omar, Umar, and Umer",
        "3.85/4.0",
        "94.40% accuracy and 94.38% macro-F1",
        "does not prove that a scheduler ran continuously in production",
        "independently_verified",
    ):
        assert important in text

    source_urls = re.findall(r"\[[^\]]+\]\((https?://[^)\s]+)\)", (ROOT / "PUBLIC_KNOWLEDGE_BOOK.md").read_text())
    assert source_urls
    assert all(url in text for url in source_urls)
    assert "**" not in text

    work = next(block for block in cleaned["blocks"] if block["type"] == "table" and block["heading_path"][-1] == "2.2 Work and practical experience")
    assert work["table"]["rows"][0]["Period"] == "June 2026–present"
    assert "Agentic AI Developer Intern" in work["table"]["rows"][0]["Role"]
    assert work["heading_path"][-1] == "2.2 Work and practical experience"


def test_cleaning_does_not_canonicalize_names_or_numbers():
    original = "**Omer / Omar / Umar / Umer** — 3.85/4.0; [GitHub](https://github.com/omerfarooq223)"
    assert clean_inline(original) == (
        "Omer / Omar / Umar / Umer — 3.85/4.0; GitHub (https://github.com/omerfarooq223)"
    )


def test_code_fence_spacing_is_preserved(tmp_path):
    source = tmp_path / "sample.md"
    source.write_text("# Example\n\n```python\nx =  1\n```\n", encoding="utf-8")
    cleaned = normalize_parsed_book(parse_markdown_book(source))
    code = next(block["text"] for block in cleaned["blocks"] if block["type"] == "code_fence")
    assert "x =  1" in code
