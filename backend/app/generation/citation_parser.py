"""Citation tag extraction and source metadata resolution."""

from __future__ import annotations

import re
from typing import Any

CITATION_PATTERN = re.compile(r"\[SOURCE:([^:\]\s]+):(\d+)\]")


def extract_citations(text: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Resolve valid citation tags against retrieved chunks, preserving stream order."""
    chunk_lookup = {str(chunk.get("id")): chunk for chunk in chunks if chunk.get("id") is not None}
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in CITATION_PATTERN.finditer(text):
        chunk_id = match.group(1)
        cited_page = int(match.group(2))
        chunk = chunk_lookup.get(chunk_id)
        key = (chunk_id, cited_page)
        if chunk is None or key in seen:
            continue
        seen.add(key)
        citations.append({
            "chunk_id": chunk_id,
            "document_id": str(chunk.get("document_id", "")),
            "page_number": cited_page,
            "bounding_box": chunk.get("bounding_box") or {},
            "source_filename": chunk.get("source_filename") or chunk.get("filename") or "",
            "excerpt": str(chunk.get("content", ""))[:200],
        })
    return citations
