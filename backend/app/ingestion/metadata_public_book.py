"""Add conservative provenance and section metadata to public-book chunks."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SECTION_NUMBER = re.compile(r"^(\d+)\.")
SUBSECTION_NUMBER = re.compile(r"^1\.(\d+)\b")


def section_owner(path: list[str]) -> str:
    """Classify the *section*, not every person mentioned in its text."""
    if len(path) < 2:
        return "general"
    section = SECTION_NUMBER.match(path[1])
    if not section:
        raise ValueError(f"Unnumbered top-level book section: {path[1]}")
    number = int(section.group(1))
    if number == 1:
        if len(path) < 3:
            return "general"
        subsection = SUBSECTION_NUMBER.match(path[2])
        if not subsection:
            raise ValueError(f"Unrecognized identity subsection: {path[2]}")
        return {1: "umar", 2: "soban", 3: "shared"}.get(int(subsection.group(1)), "general")
    if number in {2, 3, 4}:
        return "umar"
    if number in {5, 6}:
        return "soban"
    if number == 7:
        return "shared"
    if number in {8, 9}:
        return "general"
    raise ValueError(f"Section {number} has no reviewed section-owner rule")


def add_public_book_metadata(chunks_artifact: dict[str, Any]) -> dict[str, Any]:
    """Wrap each unchanged chunk with fields for filtering, audit, and citation."""
    if chunks_artifact.get("source_name") != "PUBLIC_KNOWLEDGE_BOOK.md":
        raise ValueError("Expected public knowledge book chunks")
    chunks = chunks_artifact.get("chunks")
    if not isinstance(chunks, list) or len(chunks) != chunks_artifact.get("chunk_count"):
        raise ValueError("Chunk list does not match its manifest")
    if len({chunk.get("id") for chunk in chunks}) != len(chunks):
        raise ValueError("Chunk IDs are missing or duplicated")

    source_hash = chunks_artifact["source_sha256"]
    document_id = "public-book-" + source_hash[:16]
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        if chunk["source_name"] != chunks_artifact["source_name"] or chunk["source_sha256"] != source_hash:
            raise ValueError(f"Chunk {chunk['id']} belongs to a different source version")
        if chunk["character_count"] != len(chunk["content"]):
            raise ValueError(f"Character count mismatch in chunk {chunk['id']}")
        start, end = chunk["start_line"], chunk["end_line"]
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start:
            raise ValueError(f"Invalid source line span in chunk {chunk['id']}")
        heading_path = chunk["heading_path"]
        if not isinstance(heading_path, list) or not heading_path:
            raise ValueError(f"Missing heading path in chunk {chunk['id']}")

        citation = f"{chunks_artifact['source_name']}:L{start}"
        if end != start:
            citation += f"-L{end}"
        metadata: dict[str, Any] = {
            "schema_version": 1,
            "corpus_id": "public_knowledge_book",
            "access_scope": "public_book",
            "document_id": document_id,
            "document_title": heading_path[0],
            "source_name": chunks_artifact["source_name"],
            "source_sha256": source_hash,
            "content_sha256": hashlib.sha256(chunk["content"].encode("utf-8")).hexdigest(),
            "citation_label": citation,
            "source_line_start": start,
            "source_line_end": end,
            "heading_path": heading_path,
            "section_title": heading_path[-1],
            "section_owner": section_owner(heading_path),
            "unit_type": chunk["unit_type"],
            "source_block_index": chunk["source_block_index"],
            "part_index": chunk["part_index"],
            "part_count": chunk["part_count"],
            "character_count": chunk["character_count"],
            "normalization_version": chunks_artifact["normalization_version"],
            "chunking_version": chunks_artifact["chunking_version"],
        }
        if chunk["unit_type"] == "table":
            metadata["table_row_index"] = chunk["table_row_index"]
            metadata["table_header_lines"] = chunk["table_header_lines"]
        if chunk["unit_type"] == "list":
            metadata["list_marker"] = chunk["list_marker"]
        records.append({"id": chunk["id"], "content": chunk["content"], "metadata": metadata})

    owners = Counter(record["metadata"]["section_owner"] for record in records)
    return {
        "source_name": chunks_artifact["source_name"],
        "source_sha256": source_hash,
        "metadata_schema_version": 1,
        "record_count": len(records),
        "section_owner_counts": dict(sorted(owners.items())),
        "records": records,
    }


def main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Add metadata to public-book chunks")
    parser.add_argument("--input", type=Path, default=root / "storage" / "knowledge" / "public_book_chunks.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage" / "knowledge" / "public_book_records.json")
    args = parser.parse_args()

    artifact = json.loads(args.input.read_text(encoding="utf-8"))
    actual_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if actual_hash != artifact.get("source_sha256"):
        raise ValueError("Chunk input is stale: source SHA-256 changed. Re-run steps one through three.")
    records = add_public_book_metadata(artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in records.items() if key != "records"}, indent=2))
    print(f"Saved metadata-enriched records to {args.output}")


if __name__ == "__main__":
    main()
