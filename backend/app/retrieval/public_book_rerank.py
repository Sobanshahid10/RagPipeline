"""Step-eight public-book candidate expansion, reranking, and optional filtering.

This is a transparent rank-fusion baseline, not a learned cross-encoder or an
answerability classifier. It preserves cited source text for later stages.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import asyncpg
from huggingface_hub import snapshot_download

from backend.app.ingestion.embed_public_book import MODEL_ID, LocalMiniLM
from backend.app.ingestion.index_public_book_pg import DEFAULT_URL
from backend.app.retrieval.public_book_search import search_public_book, search_public_book_sqlite

CANDIDATE_K = 40
RRF_K = 40
DENSE_WEIGHT = 1.5
LEXICAL_WEIGHT = 1.0
OWNERS = {"umar", "soban", "shared", "general"}
STOPWORDS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "between", "book", "by",
    "current", "did", "do", "does", "for", "from", "give", "has", "have", "her",
    "his", "how", "in", "into", "is", "it", "of", "on", "or", "our", "report",
    "said", "say", "she", "source", "that", "the", "their", "this", "to", "was",
    "were", "what", "when", "where", "which", "who", "why", "with", "would",
    # The book's repeated section prefix contains both names in every chunk.
    "omer", "omar", "umar", "umer", "soban", "muhammad",
}


def lexical_terms(question: str) -> list[str]:
    """Extract safe, useful tokens for OR-based full-text candidate retrieval."""
    terms = []
    seen = set()
    for term in re.findall(r"[a-z0-9]+", question.casefold()):
        if (term not in STOPWORDS and len(term) > 2 and term not in seen):
            terms.append(term)
            seen.add(term)
    return terms[:24]


def _owner_allowed(metadata: dict[str, Any], owner: str | None) -> bool:
    # Headings identify the section, not every person mentioned in a passage.
    return owner is None or metadata.get("section_owner") in {owner, "shared", "general"}


def rerank_candidates(
    dense_hits: list[dict[str, Any]],
    lexical_hits: list[dict[str, Any]],
    *,
    top_k: int = 5,
    owner: str | None = None,
) -> list[dict[str, Any]]:
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    if owner is not None and owner not in OWNERS:
        raise ValueError("owner must be umar, soban, shared, or general")
    candidates: dict[str, dict[str, Any]] = {}
    dense_ids: list[str] = []
    for rank, hit in enumerate(dense_hits, start=1):
        if not _owner_allowed(hit["metadata"], owner):
            continue
        record_id = hit["id"]
        if record_id in candidates:
            continue
        candidates[record_id] = {
            **hit, "dense_rank": rank, "dense_score": hit["score"],
            "lexical_rank": None,
        }
        dense_ids.append(record_id)
    for rank, hit in enumerate(lexical_hits, start=1):
        if not _owner_allowed(hit["metadata"], owner):
            continue
        record_id = hit["id"]
        if record_id in candidates:
            candidates[record_id]["lexical_rank"] = rank
        else:
            candidates[record_id] = {
                **hit, "dense_rank": None, "dense_score": None,
                "lexical_rank": rank,
            }
    for item in candidates.values():
        dense_rank = item["dense_rank"]
        lexical_rank = item["lexical_rank"]
        item["rerank_score"] = round(
            (DENSE_WEIGHT / (RRF_K + dense_rank) if dense_rank else 0.0)
            + (LEXICAL_WEIGHT / (RRF_K + lexical_rank) if lexical_rank else 0.0),
            8,
        )

    fused = sorted(candidates, key=lambda record_id: (
        -candidates[record_id]["rerank_score"],
        candidates[record_id]["dense_rank"] or 999,
        record_id,
    ))
    # Preserve a little semantic coverage so a noisy OR match cannot crowd out
    # all high-ranked dense evidence. The remaining places follow fused rank.
    guard_count = 2 if top_k >= 5 else 1 if top_k >= 3 else 0
    chosen = list(dict.fromkeys(dense_ids[:guard_count] + fused))[:top_k]
    chosen.sort(key=lambda record_id: (
        -candidates[record_id]["rerank_score"],
        candidates[record_id]["dense_rank"] or 999,
        record_id,
    ))
    result = []
    for rank, record_id in enumerate(chosen, start=1):
        item = candidates[record_id].copy()
        item["rank"] = rank
        item["selection"] = "dense_guard" if record_id in dense_ids[:guard_count] else "fused"
        result.append(item)
    return result


def _sqlite_lexical_hits(database_path: Path, terms: list[str]) -> list[dict[str, Any]]:
    if not terms:
        return []
    expression = " OR ".join(f'"{term}"' for term in terms)
    with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.content, c.metadata_json
            FROM chunks_fts JOIN chunks c ON c.ordinal = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY bm25(chunks_fts), c.ordinal
            LIMIT ?
            """,
            (expression, CANDIDATE_K),
        ).fetchall()
    return [
        {
            "id": record_id, "content": content,
            "metadata": (metadata := json.loads(metadata_json)),
            "citation": metadata["citation_label"],
        }
        for record_id, content, metadata_json in rows
    ]


async def _pg_lexical_hits(connection: Any, terms: list[str], source_hash: str) -> list[dict[str, Any]]:
    if not terms:
        return []
    # Terms contain only [a-z0-9] and are sent as a bound parameter.
    expression = " | ".join(terms)
    rows = await connection.fetch(
        """
        SELECT id, content, metadata
        FROM public_book_chunks
        WHERE source_sha256 = $1
          AND to_tsvector('english', content) @@ to_tsquery('english', $2)
        ORDER BY ts_rank_cd(to_tsvector('english', content), to_tsquery('english', $2)) DESC,
                 ordinal
        LIMIT $3
        """,
        source_hash, expression, CANDIDATE_K,
    )
    result = []
    for row in rows:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        result.append({
            "id": row["id"], "content": row["content"],
            "metadata": metadata, "citation": metadata["citation_label"],
        })
    return result


def rerank_public_book_sqlite(
    question: str, *, model: LocalMiniLM, source_bytes: bytes, database_path: Path,
    top_k: int = 5, owner: str | None = None,
) -> dict[str, Any]:
    dense = search_public_book_sqlite(
        question, model=model, source_bytes=source_bytes,
        database_path=database_path, top_k=CANDIDATE_K,
    )
    terms = lexical_terms(question)
    lexical = _sqlite_lexical_hits(database_path, terms)
    hits = rerank_candidates(dense["hits"], lexical, top_k=top_k, owner=owner)
    return {
        "question": question, "method": "dense + FTS5 RRF",
        "model": MODEL_ID, "source_sha256": dense["source_sha256"],
        "lexical_terms": terms, "dense_candidates": len(dense["hits"]),
        "lexical_candidates": len(lexical), "owner_filter": owner,
        "top_k": top_k, "hits": hits,
    }


async def rerank_public_book_pg(
    question: str, *, model: LocalMiniLM, source_bytes: bytes, connection: Any,
    top_k: int = 5, owner: str | None = None,
) -> dict[str, Any]:
    dense = await search_public_book(
        question, model=model, source_bytes=source_bytes,
        connection=connection, top_k=CANDIDATE_K,
    )
    terms = lexical_terms(question)
    lexical = await _pg_lexical_hits(connection, terms, dense["source_sha256"])
    hits = rerank_candidates(dense["hits"], lexical, top_k=top_k, owner=owner)
    return {
        "question": question, "method": "dense + PostgreSQL FTS RRF",
        "model": MODEL_ID, "source_sha256": dense["source_sha256"],
        "lexical_terms": terms, "dense_candidates": len(dense["hits"]),
        "lexical_candidates": len(lexical), "owner_filter": owner,
        "top_k": top_k, "hits": hits,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Rerank and optionally filter public-book evidence")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--owner", choices=sorted(OWNERS))
    parser.add_argument("--store", choices=("postgres", "sqlite"), default="postgres")
    parser.add_argument("--database-url", default=DEFAULT_URL)
    parser.add_argument("--sqlite-path", type=Path, default=root / "storage/knowledge/public_book_index.sqlite3")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    args = parser.parse_args()
    model = LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))
    source_bytes = args.source.read_bytes()
    if args.store == "sqlite":
        result = rerank_public_book_sqlite(
            args.question, model=model, source_bytes=source_bytes,
            database_path=args.sqlite_path, top_k=args.top_k, owner=args.owner,
        )
    else:
        async def run() -> dict[str, Any]:
            connection = await asyncpg.connect(args.database_url)
            try:
                return await rerank_public_book_pg(
                    args.question, model=model, source_bytes=source_bytes,
                    connection=connection, top_k=args.top_k, owner=args.owner,
                )
            finally:
                await connection.close()
        result = asyncio.run(run())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
