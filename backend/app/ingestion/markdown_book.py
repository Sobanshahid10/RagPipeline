"""Lossless loading and structural parsing for the public Markdown knowledge book.

This module deliberately does not clean, chunk, embed, or index text. Every source
line is retained in exactly one block, including blank lines and Markdown markup.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*(?:\r?\n)?$")
LIST_ITEM = re.compile(r"^[ \t]*(?P<marker>[-+*]|\d+[.)])[ \t]+")
TABLE_DIVIDER = re.compile(r"^:?-{3,}:?$")
FENCE = re.compile(r"^[ \t]*(`{3,}|~{3,})")


def _newline_style(data: bytes) -> str:
    crlf = data.count(b"\r\n")
    lf = data.count(b"\n") - crlf
    if crlf and lf:
        return "mixed"
    if crlf:
        return "CRLF"
    return "LF" if lf else "none"


def _cells(line: str) -> list[str]:
    """Split a pipe row while keeping escaped pipes inside a cell."""
    body = line.rstrip("\r\n").strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith(r"\|"):
        body = body[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", body)]


def _table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or not lines[index].lstrip().startswith("|"):
        return False
    first = _cells(lines[index])
    second = _cells(lines[index + 1])
    return bool(first) and len(first) == len(second) and all(TABLE_DIVIDER.fullmatch(cell) for cell in second)


def _kind(lines: list[str], index: int) -> str:
    line = lines[index]
    if not line.strip():
        return "blank"
    if HEADING.match(line):
        return "heading"
    if FENCE.match(line):
        return "code_fence"
    if _table_start(lines, index):
        return "table"
    if LIST_ITEM.match(line):
        return "list"
    return "paragraph"


def parse_markdown_book(path: str | Path, *, source_name: str | None = None) -> dict[str, Any]:
    """Load UTF-8 Markdown and return ordered blocks with one-based line spans."""
    source = Path(path)
    if source.suffix.lower() != ".md":
        raise ValueError("This loader accepts Markdown (.md) only")
    data = source.read_bytes()
    if not data:
        raise ValueError("The source document is empty")
    if b"\x00" in data:
        raise ValueError("The source contains a NUL byte; check its encoding or format")
    text = data.decode("utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8", errors="strict")
    lines = text.splitlines(keepends=True)
    blocks: list[dict[str, Any]] = []
    headings: list[str] = []
    index = 0

    while index < len(lines):
        start = index
        kind = _kind(lines, index)
        extra: dict[str, Any] = {}

        if kind == "heading":
            match = HEADING.match(lines[index])
            assert match is not None
            level, title = len(match.group(1)), match.group(2).strip()
            headings = headings[: level - 1] + [title]
            extra = {"level": level, "title": title}
            index += 1
        elif kind == "blank":
            while index < len(lines) and not lines[index].strip():
                index += 1
        elif kind == "code_fence":
            opening = FENCE.match(lines[index])
            assert opening is not None
            marker = opening.group(1)
            index += 1
            close = re.compile(r"^[ \t]*" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*(?:\r?\n)?$")
            while index < len(lines) and not close.match(lines[index]):
                index += 1
            if index >= len(lines):
                raise ValueError(f"Unclosed code fence at line {start + 1}")
            index += 1
            extra = {"fence": marker[0]}
        elif kind == "table":
            header = _cells(lines[index])
            index += 2  # Header and Markdown alignment rule.
            rows: list[list[str]] = []
            while index < len(lines) and lines[index].lstrip().startswith("|"):
                cells = _cells(lines[index])
                if len(cells) != len(header):
                    raise ValueError(f"Table at line {start + 1} has {len(header)} columns; line {index + 1} has {len(cells)}")
                rows.append(cells)
                index += 1
            extra = {"columns": header, "rows": rows}
        elif kind == "list":
            item = LIST_ITEM.match(lines[index])
            assert item is not None
            extra = {"list_marker": item.group("marker")}
            index += 1
            while index < len(lines) and lines[index].strip():
                if LIST_ITEM.match(lines[index]) or HEADING.match(lines[index]) or _table_start(lines, index) or FENCE.match(lines[index]):
                    break
                index += 1
        else:
            index += 1
            while index < len(lines) and lines[index].strip():
                if _kind(lines, index) != "paragraph":
                    break
                index += 1

        blocks.append({
            "type": kind,
            "start_line": start + 1,
            "end_line": index,
            "heading_path": headings.copy(),
            "raw_markdown": "".join(lines[start:index]),
            **extra,
        })

    if "".join(block["raw_markdown"] for block in blocks) != text:
        raise AssertionError("Parsing lost or reordered source text")

    counts = Counter(block["type"] for block in blocks)
    return {
        "source_name": source_name or source.name,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "format": "markdown",
        "encoding": "utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8",
        "newline_style": _newline_style(data),
        "line_count": len(lines),
        "block_count": len(blocks),
        "block_types": dict(sorted(counts.items())),
        "blocks": blocks,
    }


def main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Load and structurally parse a Markdown knowledge book")
    parser.add_argument("--input", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage" / "knowledge" / "public_book_parsed.json")
    args = parser.parse_args()
    parsed = parse_markdown_book(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in parsed.items() if key != "blocks"}, indent=2))
    print(f"Saved parsed document to {args.output}")


if __name__ == "__main__":
    main()
