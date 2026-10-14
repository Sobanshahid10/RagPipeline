"""Conservative cleaning of parsed public-book blocks; no chunking or indexing."""

from __future__ import annotations

import hashlib
import html
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


LINK = re.compile(r"(?<!!)\[([^\]]+)\]\((https?://[^)\s]+)\)")
INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
BOLD_STAR = re.compile(r"\*\*(.+?)\*\*")
BOLD_UNDERSCORE = re.compile(r"(?<!\w)__(.+?)__(?!\w)")
ITALIC_STAR = re.compile(r"(?<!\*)\*([^*\n]+)\*(?!\*)")


def clean_inline(value: str) -> str:
    """Make Markdown prose readable without changing names, numbers, or claims."""
    value = unicodedata.normalize("NFC", html.unescape(value))
    value = value.replace("\u00a0", " ").replace("\u200b", "")
    value = LINK.sub(lambda match: f"{match.group(1)} ({match.group(2)})", value)
    value = INLINE_CODE.sub(r"\1", value)
    value = BOLD_STAR.sub(r"\1", value)
    value = BOLD_UNDERSCORE.sub(r"\1", value)
    value = ITALIC_STAR.sub(r"\1", value)
    value = value.replace(r"\|", "|")
    return re.sub(r"[ \t]+", " ", value).strip()


def _prose(raw: str) -> str:
    """Preserve intentional line boundaries while removing Markdown-only whitespace."""
    lines = raw.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    return "\n".join(clean_inline(line) for line in lines).strip()


def normalize_parsed_book(parsed: dict[str, Any]) -> dict[str, Any]:
    """Add plain, readable text to each parsed block while keeping provenance."""
    if parsed.get("format") != "markdown" or not isinstance(parsed.get("blocks"), list):
        raise ValueError("Expected the output of the Markdown book parser")
    if len(parsed["blocks"]) != parsed.get("block_count"):
        raise ValueError("Parsed block count does not match its manifest")

    cleaned: list[dict[str, Any]] = []
    for source_block in parsed["blocks"]:
        kind = source_block["type"]
        block: dict[str, Any] = {
            "type": kind,
            "start_line": source_block["start_line"],
            "end_line": source_block["end_line"],
            "heading_path": [clean_inline(title) for title in source_block["heading_path"]],
        }
        raw = source_block["raw_markdown"]

        if kind == "blank":
            text = ""
        elif kind == "heading":
            text = clean_inline(source_block["title"])
            block["level"] = source_block["level"]
        elif kind == "list":
            marker = source_block["list_marker"]
            first_line, _, rest = raw.partition("\n")
            match = re.match(r"^[ \t]*" + re.escape(marker) + r"[ \t]+", first_line)
            if not match:
                raise ValueError(f"List marker mismatch at line {block['start_line']}")
            text = _prose(first_line[match.end():] + ("\n" + rest if rest else ""))
            block["list_marker"] = marker
        elif kind == "table":
            columns = [clean_inline(column) for column in source_block["columns"]]
            if len(columns) != len(set(columns)):
                raise ValueError(f"Duplicate table column at line {block['start_line']}")
            rows = []
            for source_row in source_block["rows"]:
                if len(source_row) != len(columns):
                    raise ValueError(f"Table width changed at line {block['start_line']}")
                rows.append(dict(zip(columns, (clean_inline(cell) for cell in source_row))))
            block["table"] = {"columns": columns, "rows": rows}
            text = "\n".join("; ".join(f"{column}: {row[column]}" for column in columns) for row in rows)
        elif kind == "code_fence":
            # Code is not prose. Keep its internal spacing and punctuation intact.
            text = raw.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        else:
            text = _prose(raw)

        if kind != "blank" and not text:
            raise ValueError(f"Cleaning erased a {kind} block at line {block['start_line']}")

        # Every Markdown URL remains present in the cleaned representation.
        for url in LINK.findall(raw):
            if url[1] not in text:
                raise ValueError(f"Cleaning lost a link at line {block['start_line']}: {url[1]}")

        block["text"] = text
        cleaned.append(block)

    counts = Counter(block["type"] for block in cleaned)
    return {
        "source_name": parsed["source_name"],
        "source_sha256": parsed["source_sha256"],
        "normalization_version": 1,
        "normalization_rules": [
            "Unicode NFC; UTF-8 text",
            "CRLF/CR to LF in cleaned text; source line locations retained",
            "HTML entities decoded; non-breaking spaces changed to spaces; zero-width spaces removed",
            "Markdown link labels and URLs retained; inline code and emphasis markers simplified",
            "List markers moved to a separate field; table cells paired with their column names",
            "Names, numbers, dates, attribution, and uncertainty wording not rewritten",
        ],
        "block_count": len(cleaned),
        "block_types": dict(sorted(counts.items())),
        "blocks": cleaned,
    }


def main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Clean and normalize a parsed Markdown knowledge book")
    parser.add_argument("--input", type=Path, default=root / "storage" / "knowledge" / "public_book_parsed.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage" / "knowledge" / "public_book_normalized.json")
    args = parser.parse_args()

    parsed = json.loads(args.input.read_text(encoding="utf-8"))
    actual_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
    if actual_hash != parsed.get("source_sha256"):
        raise ValueError("Parsed input is stale: source SHA-256 does not match. Run step one again.")
    cleaned = normalize_parsed_book(parsed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in cleaned.items() if key != "blocks"}, indent=2, ensure_ascii=False))
    print(f"Saved normalized document to {args.output}")


if __name__ == "__main__":
    main()
