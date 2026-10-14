"""Step-nine bounded, source-linked context construction for the public book.

The result contains evidence data only. Prompt instructions and answer generation
belong to later stages.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

import asyncpg
from huggingface_hub import snapshot_download

from backend.app.ingestion.embed_public_book import MODEL_ID, LocalMiniLM
from backend.app.ingestion.index_public_book_pg import DEFAULT_URL
from backend.app.retrieval.public_book_rerank import rerank_public_book_pg, rerank_public_book_sqlite

CONTEXT_FORMAT = "json_sources_v1"
DEFAULT_MAX_BYTES = 4096
DEFAULT_MAX_SOURCES = 5


def _source_text(content: str) -> str:
    """Remove the synthetic section breadcrumb; section metadata stays with the source."""
    if content.startswith("Section: ") and "\n" in content:
        return content.split("\n", 1)[1].strip()
    return content.strip()


def _serialize(sources: list[dict[str, str]]) -> str:
    return json.dumps({"sources": sources}, ensure_ascii=False, separators=(",", ":"))


def build_context(
    reranked: dict[str, Any], *,
    max_context_bytes: int = DEFAULT_MAX_BYTES,
    max_sources: int = DEFAULT_MAX_SOURCES,
) -> dict[str, Any]:
    if max_context_bytes < 128:
        raise ValueError("max_context_bytes must be at least 128")
    if not 1 <= max_sources <= 20:
        raise ValueError("max_sources must be between 1 and 20")
    source_hash = reranked["source_sha256"]
    selected: list[dict[str, str]] = []
    manifest: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    selected_ids: set[str] = set()
    selected_content_hashes: set[str] = set()

    for hit in reranked["hits"]:
        record_id = hit["id"]
        metadata = hit["metadata"]
        if metadata.get("access_scope") != "public_book":
            raise ValueError(f"Non-public source in context candidates: {record_id}")
        if metadata.get("source_name") != "PUBLIC_KNOWLEDGE_BOOK.md":
            raise ValueError(f"Unexpected source document: {record_id}")
        if metadata.get("source_sha256") != source_hash:
            raise ValueError(f"Stale source hash in context candidate: {record_id}")
        content_hash = hashlib.sha256(hit["content"].encode("utf-8")).hexdigest()
        if metadata.get("content_sha256") != content_hash:
            raise ValueError(f"Content hash mismatch in context candidate: {record_id}")
        if hit.get("citation") != metadata.get("citation_label"):
            raise ValueError(f"Citation mismatch in context candidate: {record_id}")
        if record_id in selected_ids:
            skipped.append({"id": record_id, "reason": "duplicate_id"})
            continue
        if content_hash in selected_content_hashes:
            skipped.append({"id": record_id, "reason": "duplicate_text"})
            continue
        if len(selected) >= max_sources:
            skipped.append({"id": record_id, "reason": "source_limit"})
            continue
        body = _source_text(hit["content"])
        if not body:
            skipped.append({"id": record_id, "reason": "empty_text"})
            continue
        source_id = f"S{len(selected) + 1}"
        entry = {
            "source_id": source_id,
            "chunk_id": record_id,
            "citation": hit["citation"],
            "section": metadata.get("section_title", ""),
            "text": body,
        }
        candidate_context = _serialize([*selected, entry])
        if len(candidate_context.encode("utf-8")) > max_context_bytes:
            skipped.append({"id": record_id, "reason": "byte_budget"})
            continue
        selected.append(entry)
        selected_ids.add(record_id)
        selected_content_hashes.add(content_hash)
        manifest.append({
            "source_id": source_id,
            "chunk_id": record_id,
            "citation": hit["citation"],
            "source_line_start": metadata.get("source_line_start"),
            "source_line_end": metadata.get("source_line_end"),
            "section_owner": metadata.get("section_owner"),
            "content_sha256": content_hash,
            "rerank_score": hit.get("rerank_score"),
        })
    context = _serialize(selected)
    return {
        "question": reranked["question"],
        "status": "ready" if selected else "empty",
        "context_format": CONTEXT_FORMAT,
        "source_name": "PUBLIC_KNOWLEDGE_BOOK.md",
        "source_sha256": source_hash,
        "max_context_bytes": max_context_bytes,
        "context_bytes": len(context.encode("utf-8")),
        "max_sources": max_sources,
        "included_count": len(selected),
        "skipped": skipped,
        "source_manifest": manifest,
        "context": context,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Build bounded, cited context from public-book retrieval")
    parser.add_argument("question")
    parser.add_argument("--store", choices=("postgres", "sqlite"), default="postgres")
    parser.add_argument("--owner", choices=("umar", "soban", "shared", "general"))
    parser.add_argument("--database-url", default=DEFAULT_URL)
    parser.add_argument("--sqlite-path", type=Path, default=root / "storage/knowledge/public_book_index.sqlite3")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--max-sources", type=int, default=DEFAULT_MAX_SOURCES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    model = LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))
    source_bytes = args.source.read_bytes()
    if args.store == "sqlite":
        reranked = rerank_public_book_sqlite(
            args.question, model=model, source_bytes=source_bytes,
            database_path=args.sqlite_path, top_k=10, owner=args.owner,
        )
    else:
        async def run() -> dict[str, Any]:
            connection = await asyncpg.connect(args.database_url)
            try:
                return await rerank_public_book_pg(
                    args.question, model=model, source_bytes=source_bytes,
                    connection=connection, top_k=10, owner=args.owner,
                )
            finally:
                await connection.close()
        reranked = asyncio.run(run())
    result = build_context(reranked, max_context_bytes=args.max_bytes, max_sources=args.max_sources)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(json.dumps({
            "output": str(args.output), "status": result["status"],
            "included_count": result["included_count"], "context_bytes": result["context_bytes"],
            "skipped": result["skipped"],
        }, indent=2))
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
