"""Step-seven dense retrieval from the dedicated public-book pgvector table."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np
from huggingface_hub import snapshot_download

from backend.app.ingestion.embed_public_book import DIMENSIONS, INPUT_TEMPLATE_VERSION, MODEL_ID, LocalMiniLM, validate_vector
from backend.app.ingestion.index_public_book_pg import DEFAULT_URL


def _vector_literal(values: list[float]) -> str:
    validate_vector(values, record_id="question")
    return "[" + ",".join(str(value) for value in values) + "]"


async def search_public_book(
    question: str,
    *,
    model: LocalMiniLM,
    source_bytes: bytes,
    connection: Any,
    top_k: int = 5,
) -> dict[str, Any]:
    if not question.strip():
        raise ValueError("Question must not be blank")
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")

    manifest = await connection.fetchrow(
        """
        SELECT source_sha256, model, model_sha256, input_template_version, dimensions, record_count
        FROM public_book_index_manifest WHERE singleton = TRUE
        """
    )
    if manifest is None:
        raise ValueError("Public-book index manifest is missing; run step six")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if manifest["source_sha256"].strip() != source_hash:
        raise ValueError("Indexed public book is stale; rebuild earlier steps")
    if manifest["model"] != MODEL_ID or manifest["model_sha256"].strip() != model.model_hash:
        raise ValueError("Question embedder differs from indexed model weights")
    if manifest["input_template_version"] != INPUT_TEMPLATE_VERSION:
        raise ValueError("Question embedder differs from indexed embedding recipe")
    if manifest["dimensions"] != DIMENSIONS:
        raise ValueError("Indexed vector dimension differs from question embedder")

    query_vector, token_count, window_count = model.embed(question)
    vector_literal = _vector_literal(query_vector)
    rows = await connection.fetch(
        """
        SELECT id, content, metadata, source_sha256, model_sha256,
               embedding <=> $1::vector AS cosine_distance
        FROM public_book_chunks
        WHERE source_sha256 = $2 AND model_sha256 = $3
        ORDER BY embedding <=> $1::vector, ordinal
        LIMIT $4
        """,
        vector_literal, source_hash, model.model_hash, top_k,
    )
    if len(rows) > manifest["record_count"]:
        raise ValueError("Retrieved more rows than the index manifest allows")
    hits = []
    for rank, row in enumerate(rows, start=1):
        metadata = row["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        distance = float(row["cosine_distance"])
        if not -0.00001 <= distance <= 2.00001:
            raise ValueError("Invalid cosine distance returned by pgvector")
        hits.append({
            "rank": rank,
            "id": row["id"],
            "score": round(1.0 - distance, 6),
            "cosine_distance": round(distance, 6),
            "content": row["content"],
            "citation": metadata["citation_label"],
            "metadata": metadata,
        })
    return {
        "question": question,
        "model": MODEL_ID,
        "dimensions": DIMENSIONS,
        "source_sha256": source_hash,
        "query_token_count": token_count,
        "query_window_count": window_count,
        "top_k": top_k,
        "hits": hits,
    }


def search_public_book_sqlite(
    question: str, *, model: LocalMiniLM, source_bytes: bytes, database_path: Path, top_k: int = 5
) -> dict[str, Any]:
    """Exact cosine retrieval from the step-six local fallback artifact."""
    if not question.strip():
        raise ValueError("Question must not be blank")
    if not 1 <= top_k <= 50:
        raise ValueError("top_k must be between 1 and 50")
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as connection:
        manifest = connection.execute(
            "SELECT source_sha256, model, model_sha256, input_template_version, dimensions, record_count FROM manifest WHERE singleton = 1"
        ).fetchone()
        if manifest is None:
            raise ValueError("Public-book index manifest is missing")
        if manifest[0] != source_hash:
            raise ValueError("Indexed public book is stale; rebuild earlier steps")
        if manifest[1] != MODEL_ID or manifest[2] != model.model_hash:
            raise ValueError("Question embedder differs from indexed model weights")
        if manifest[3] != INPUT_TEMPLATE_VERSION:
            raise ValueError("Question embedder differs from indexed embedding recipe")
        if manifest[4] != DIMENSIONS:
            raise ValueError("Indexed vector dimension differs from question embedder")
        query_vector, token_count, window_count = model.embed(question)
        query = np.asarray(validate_vector(query_vector, record_id="question"), dtype=np.float32)
        rows = connection.execute(
            "SELECT ordinal, id, content, metadata_json, embedding FROM chunks ORDER BY ordinal"
        ).fetchall()
        if len(rows) != manifest[5]:
            raise ValueError("Index row count differs from manifest")
        scored = []
        for ordinal, record_id, content, metadata_json, embedding in rows:
            vector = np.frombuffer(embedding, dtype="<f4")
            if len(vector) != DIMENSIONS or not np.isfinite(vector).all():
                raise ValueError(f"Invalid stored vector for {record_id}")
            score = float(np.dot(query, vector))
            scored.append((score, ordinal, record_id, content, metadata_json))
        scored.sort(key=lambda item: (-item[0], item[1]))
        hits = []
        for rank, (score, _, record_id, content, metadata_json) in enumerate(scored[:top_k], start=1):
            metadata = json.loads(metadata_json)
            hits.append({
                "rank": rank, "id": record_id, "score": round(score, 6),
                "cosine_distance": round(1.0 - score, 6),
                "content": content, "citation": metadata["citation_label"], "metadata": metadata,
            })
        return {
            "question": question, "model": MODEL_ID, "dimensions": DIMENSIONS,
            "source_sha256": source_hash, "query_token_count": token_count,
            "query_window_count": window_count, "top_k": top_k, "hits": hits,
        }


async def run_cli(question: str, *, top_k: int, database_url: str, source_path: Path) -> dict[str, Any]:
    model_path = Path(snapshot_download(MODEL_ID, local_files_only=True))
    model = LocalMiniLM(model_path)
    connection = await asyncpg.connect(database_url)
    try:
        return await search_public_book(
            question, model=model, source_bytes=source_path.read_bytes(),
            connection=connection, top_k=top_k,
        )
    finally:
        await connection.close()


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Retrieve cited public-book chunks using local MiniLM and pgvector")
    parser.add_argument("question")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--database-url", default=DEFAULT_URL)
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--store", choices=("postgres", "sqlite"), default="postgres")
    parser.add_argument("--sqlite-path", type=Path, default=root / "storage/knowledge/public_book_index.sqlite3")
    args = parser.parse_args()
    if args.store == "sqlite":
        model_path = Path(snapshot_download(MODEL_ID, local_files_only=True))
        result = search_public_book_sqlite(
            args.question, model=LocalMiniLM(model_path), source_bytes=args.source.read_bytes(),
            database_path=args.sqlite_path, top_k=args.top_k,
        )
    else:
        result = asyncio.run(run_cli(args.question, top_k=args.top_k, database_url=args.database_url, source_path=args.source))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
