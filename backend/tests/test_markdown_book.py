"""Checks that stage-one parsing preserves source content and useful structure."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app.ingestion.markdown_book import parse_markdown_book


ROOT = Path(__file__).resolve().parents[2]


def test_public_book_parses_without_losing_or_reordering_text():
    source = ROOT / "PUBLIC_KNOWLEDGE_BOOK.md"
    parsed = parse_markdown_book(source)
    blocks = parsed["blocks"]

    assert parsed["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert "".join(block["raw_markdown"] for block in blocks) == source.read_text(encoding="utf-8")
    assert [block["start_line"] for block in blocks] == sorted(block["start_line"] for block in blocks)
    assert blocks[-1]["end_line"] == parsed["line_count"]

    work = next(block for block in blocks if block["type"] == "table" and block["heading_path"][-1] == "2.2 Work and practical experience")
    assert work["columns"] == ["Period", "Role", "Work described by the sources"]
    assert len(work["rows"]) == 5
    assert work["heading_path"][-1] == "2.2 Work and practical experience"

    # Project entries remain separate items, rather than one huge list block.
    projects = [block for block in blocks if block["type"] == "list" and block["list_marker"] == "1."]
    assert any("DocuStratum Studio" in block["raw_markdown"] for block in projects)


def test_preserves_crlf_unicode_escaped_pipe_and_fenced_code(tmp_path):
    source = tmp_path / "example.md"
    original = "# Café\r\n\r\n| A | B |\r\n| --- | --- |\r\n| x\\|y | z |\r\n\r\n```python\r\nprint(1)\r\n```\r\n"
    source.write_bytes(original.encode("utf-8"))

    parsed = parse_markdown_book(source)
    assert parsed["newline_style"] == "CRLF"
    assert "".join(block["raw_markdown"] for block in parsed["blocks"]) == original
    table = next(block for block in parsed["blocks"] if block["type"] == "table")
    assert table["rows"] == [[r"x\|y", "z"]]
    assert any(block["type"] == "code_fence" for block in parsed["blocks"])


def test_rejects_unreadable_or_malformed_sources(tmp_path):
    invalid = tmp_path / "invalid.md"
    invalid.write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        parse_markdown_book(invalid)

    malformed = tmp_path / "malformed.md"
    malformed.write_text("| A | B |\n| --- | --- |\n| one |\n", encoding="utf-8")
    with pytest.raises(ValueError, match="columns"):
        parse_markdown_book(malformed)

    unclosed = tmp_path / "unclosed.md"
    unclosed.write_text("```python\nprint(1)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unclosed code fence"):
        parse_markdown_book(unclosed)
