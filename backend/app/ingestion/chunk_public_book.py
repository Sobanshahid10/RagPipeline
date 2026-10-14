"""Section-aware chunks for the normalized public book; no embedding or indexing."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_MAX_CHARS = 1800


def _context(heading_path: list[str]) -> str:
    return "Section: " + " > ".join(heading_path) + "\n"


def _split_oversize(text: str, available: int) -> list[str]:
    """Prefer sentence boundaries, then whitespace; never split a word or URL."""
    if available < 120:
        raise ValueError("Chunk budget leaves too little room after the section heading")
    parts: list[str] = []
    remaining = text.strip()
    while len(remaining) > available:
        window = remaining[: available + 1]
        lower = available // 2
        sentence_ends = [match.end() for match in re.finditer(r"[.!?](?:\s+|$)|\n", window)]
        candidates = [point for point in sentence_ends if lower <= point <= available]
        if candidates:
            cut = max(candidates)
        else:
            cut = max(window.rfind(" ", 0, available + 1), window.rfind("\n", 0, available + 1))
        if cut <= 0:
            raise ValueError("A single word or URL exceeds the chunk limit; increase --max-chars")
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        parts.append(remaining)
    if re.sub(r"\s+", " ", " ".join(parts)).strip() != re.sub(r"\s+", " ", text).strip():
        raise AssertionError("Splitting lost or changed source words")
    return parts


def _units(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for block_index, block in enumerate(normalized["blocks"]):
        kind = block["type"]
        if kind in {"blank", "heading"}:
            continue
        common = {
            "type": kind,
            "heading_path": block["heading_path"],
            "block_index": block_index,
        }
        if kind == "table":
            table = block["table"]
            for row_index, row in enumerate(table["rows"]):
                text = "; ".join(f"{column}: {row[column]}" for column in table["columns"])
                units.append({
                    **common,
                    "text": text,
                    "start_line": block["start_line"] + 2 + row_index,
                    "end_line": block["start_line"] + 2 + row_index,
                    "table_row_index": row_index,
                    "table_header_lines": [block["start_line"], block["start_line"] + 1],
                })
        else:
            units.append({
                **common,
                "text": block["text"],
                "start_line": block["start_line"],
                "end_line": block["end_line"],
                **({"list_marker": block["list_marker"]} if kind == "list" else {}),
            })
    return units


def chunk_normalized_book(normalized: dict[str, Any], *, max_chars: int = DEFAULT_MAX_CHARS) -> dict[str, Any]:
    """Make source-linked chunks from prose blocks and individual table rows."""
    if max_chars < 300:
        raise ValueError("--max-chars must be at least 300")
    if normalized.get("source_name") != "PUBLIC_KNOWLEDGE_BOOK.md":
        raise ValueError("This learning-stage chunker accepts the public knowledge book only")
    if len(normalized.get("blocks", [])) != normalized.get("block_count"):
        raise ValueError("Normalized block count does not match its manifest")

    units = _units(normalized)
    chunks: list[dict[str, Any]] = []
    for unit in units:
        prefix = _context(unit["heading_path"])
        parts = _split_oversize(unit["text"], max_chars - len(prefix))
        for part_index, part in enumerate(parts):
            content = prefix + part
            if len(content) > max_chars:
                raise AssertionError("Chunk exceeds the character budget")
            identity = f"{normalized['source_sha256']}:{unit['block_index']}:{unit.get('table_row_index', -1)}:{part_index}"
            chunk_id = "pubbook-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            chunks.append({
                "id": chunk_id,
                "index": len(chunks),
                "content": content,
                "character_count": len(content),
                "source_name": normalized["source_name"],
                "source_sha256": normalized["source_sha256"],
                "start_line": unit["start_line"],
                "end_line": unit["end_line"],
                "heading_path": unit["heading_path"],
                "source_block_index": unit["block_index"],
                "unit_type": unit["type"],
                "part_index": part_index,
                "part_count": len(parts),
                **({"table_row_index": unit["table_row_index"], "table_header_lines": unit["table_header_lines"]}
                   if unit["type"] == "table" else {}),
                **({"list_marker": unit["list_marker"]} if unit["type"] == "list" else {}),
            })

    if not chunks or len({chunk["id"] for chunk in chunks}) != len(chunks):
        raise AssertionError("No chunks were made, or chunk IDs collided")
    if {unit["block_index"] for unit in units} != {chunk["source_block_index"] for chunk in chunks}:
        raise AssertionError("A non-heading source block was omitted")

    lengths = sorted(chunk["character_count"] for chunk in chunks)
    counts = Counter(chunk["unit_type"] for chunk in chunks)
    return {
        "source_name": normalized["source_name"],
        "source_sha256": normalized["source_sha256"],
        "normalization_version": normalized["normalization_version"],
        "chunking_version": 1,
        "max_characters": max_chars,
        "size_unit": "characters, including the section prefix; not model tokens",
        "source_unit_count": len(units),
        "chunk_count": len(chunks),
        "chunk_types": dict(sorted(counts.items())),
        "character_stats": {
            "min": lengths[0],
            "median": lengths[len(lengths) // 2],
            "p95": lengths[min(len(lengths) - 1, int(0.95 * len(lengths)))],
            "max": lengths[-1],
        },
        "chunks": chunks,
    }


def main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Chunk the normalized public knowledge book")
    parser.add_argument("--input", type=Path, default=root / "storage" / "knowledge" / "public_book_normalized.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage" / "knowledge" / "public_book_chunks.json")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()

    normalized = json.loads(args.input.read_text(encoding="utf-8"))
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != normalized.get("source_sha256"):
        raise ValueError("Normalized input is stale: source SHA-256 changed. Re-run steps one and two.")
    result = chunk_normalized_book(normalized, max_chars=args.max_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "chunks"}, indent=2, ensure_ascii=False))
    print(f"Saved chunks to {args.output}")


if __name__ == "__main__":
    main()
