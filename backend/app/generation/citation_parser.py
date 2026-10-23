"""Citation tag extraction and source metadata resolution."""

from __future__ import annotations

import re
from typing import Any

CITATION_PATTERN = re.compile(r"\[SOURCE:([^:\]\s]+):(\d+)\]")


def has_citation_coverage(answer: str, pattern: re.Pattern) -> bool:
    """Require citations on each prose paragraph/list item, allowing Markdown headings.

    This is structural validation only. The evidence auditor must still check every
    claim; punctuation-based sentence splitting is unreliable for technical text.
    """
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+] |\d+\. ))", answer):
        block = block.strip()
        if not block:
            continue
        # A heading is formatting, not an independently supported answer paragraph.
        lines = block.splitlines()
        while lines and re.match(r"^#{1,6}\s", lines[0]):
            lines.pop(0)
        prose = "\n".join(lines).strip()
        if not prose:
            continue
        matches = list(pattern.finditer(prose))
        if not matches or prose[matches[-1].end() :].strip(" \n\r\t.!?*\"')"):
            return False
    return True


def extract_citations(text: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve valid citation tags against retrieved chunks, preserving stream order."""
    chunk_lookup = {
        str(chunk.get("id")): chunk for chunk in chunks if chunk.get("id") is not None
    }
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in CITATION_PATTERN.finditer(text):
        chunk_id = match.group(1)
        cited_page = int(match.group(2))
        chunk = chunk_lookup.get(chunk_id)
        key = (chunk_id, cited_page)
        if (
            chunk is None
            or cited_page != int(chunk.get("page_number") or 1)
            or key in seen
        ):
            continue
        seen.add(key)
        citations.append(
            {
                "chunk_id": chunk_id,
                "document_id": str(chunk.get("document_id", "")),
                "page_number": cited_page,
                "bounding_box": chunk.get("bounding_box") or {},
                "source_filename": chunk.get("source_filename")
                or chunk.get("filename")
                or "",
                "excerpt": str(chunk.get("content", ""))[:200],
            }
        )
    return citations


def validate_answer_citations(answer: str, chunks: list[dict[str, Any]]) -> bool:
    """Reject missing, malformed, unknown and wrong-page citations before publication."""
    matches = list(CITATION_PATTERN.finditer(answer))
    if not matches or len(matches) != answer.count("[SOURCE:"):
        return False
    allowed = {(str(c.get("id")), int(c.get("page_number") or 1)) for c in chunks}
    if any((m.group(1), int(m.group(2))) not in allowed for m in matches):
        return False
    return has_citation_coverage(answer, CITATION_PATTERN)
