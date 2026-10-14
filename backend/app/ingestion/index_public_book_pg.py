"""Load step-five vectors into a dedicated PostgreSQL/pgvector HNSW index."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import asyncpg

from .embed_public_book import DIMENSIONS, INPUT_TEMPLATE_VERSION, MODEL_ID
from .index_public_book import validate_inputs

DEFAULT_URL = "postgresql://rag_user:rag_password@127.0.0.1:5433/rag_db"

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS public_book_chunks (
    id TEXT PRIMARY KEY,
    ordinal INTEGER NOT NULL UNIQUE,
    source_sha256 CHAR(64) NOT NULL,
    model_sha256 CHAR(64) NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    content TEXT NOT NULL,
    section_owner TEXT NOT NULL,
    section_title TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    metadata JSONB NOT NULL,
    embedding VECTOR(384) NOT NULL
);
CREATE TABLE IF NOT EXISTS public_book_index_manifest (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    source_sha256 CHAR(64) NOT NULL,
    model TEXT NOT NULL,
    model_sha256 CHAR(64) NOT NULL,
    input_template_version INTEGER NOT NULL DEFAULT 1,
    dimensions INTEGER NOT NULL CHECK (dimensions = 384),
    record_count INTEGER NOT NULL
);
ALTER TABLE public_book_index_manifest
    ADD COLUMN IF NOT EXISTS input_template_version INTEGER NOT NULL DEFAULT 1;
CREATE INDEX IF NOT EXISTS idx_public_book_owner ON public_book_chunks(section_owner);
CREATE INDEX IF NOT EXISTS idx_public_book_unit_type ON public_book_chunks(unit_type);
CREATE INDEX IF NOT EXISTS idx_public_book_fts
    ON public_book_chunks USING gin (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_public_book_hnsw
    ON public_book_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
"""


async def build_pg_index(records_artifact: dict, embeddings_artifact: dict, source_bytes: bytes, database_url: str) -> dict:
    pairs = validate_inputs(records_artifact, embeddings_artifact, source_bytes)
    connection = await asyncpg.connect(database_url)
    try:
        async with connection.transaction():
            await connection.execute("SELECT pg_advisory_xact_lock(932684115)")
            await connection.execute(DDL)
            await connection.execute("DELETE FROM public_book_chunks")
            rows = []
            for ordinal, (record, item) in enumerate(pairs, start=1):
                metadata = record["metadata"]
                vector = "[" + ",".join(str(value) for value in item["vector"]) + "]"
                rows.append((
                    record["id"], ordinal, records_artifact["source_sha256"],
                    embeddings_artifact["model_sha256"], metadata["content_sha256"],
                    record["content"], metadata["section_owner"], metadata["section_title"],
                    metadata["unit_type"], json.dumps(metadata, ensure_ascii=False), vector,
                ))
            await connection.executemany(
                """
                INSERT INTO public_book_chunks
                (id, ordinal, source_sha256, model_sha256, content_sha256, content,
                 section_owner, section_title, unit_type, metadata, embedding)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::vector)
                """,
                rows,
            )
            await connection.execute(
                """
                INSERT INTO public_book_index_manifest
                (singleton, source_sha256, model, model_sha256, input_template_version, dimensions, record_count)
                VALUES (TRUE, $1, $2, $3, $4, $5, $6)
                ON CONFLICT (singleton) DO UPDATE SET
                    source_sha256 = EXCLUDED.source_sha256,
                    model = EXCLUDED.model,
                    model_sha256 = EXCLUDED.model_sha256,
                    input_template_version = EXCLUDED.input_template_version,
                    dimensions = EXCLUDED.dimensions,
                    record_count = EXCLUDED.record_count
                """,
                records_artifact["source_sha256"], MODEL_ID,
                embeddings_artifact["model_sha256"], INPUT_TEMPLATE_VERSION, DIMENSIONS, len(pairs),
            )
        count = await connection.fetchval("SELECT count(*) FROM public_book_chunks")
        dimensions = await connection.fetchval("SELECT vector_dims(embedding) FROM public_book_chunks LIMIT 1")
        index_exists = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'public_book_chunks' AND indexname = 'idx_public_book_hnsw')"
        )
        fts_index_exists = await connection.fetchval(
            "SELECT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'public_book_chunks' AND indexname = 'idx_public_book_fts')"
        )
        first_id = pairs[0][0]["id"]
        first_vector = "[" + ",".join(str(value) for value in pairs[0][1]["vector"]) + "]"
        self_distance = await connection.fetchval(
            "SELECT embedding <=> $1::vector FROM public_book_chunks WHERE id = $2", first_vector, first_id
        )
        if count != len(pairs) or dimensions != DIMENSIONS or not index_exists or not fts_index_exists or abs(self_distance) > 0.00001:
            raise ValueError("PostgreSQL vector/index verification failed")
        return {
            "record_count": count, "dimensions": dimensions, "model": MODEL_ID,
            "source_sha256": records_artifact["source_sha256"],
            "hnsw_index": "idx_public_book_hnsw", "text_index": "idx_public_book_fts",
            "self_distance": float(self_distance),
        }
    finally:
        await connection.close()


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Build the public-book pgvector index")
    parser.add_argument("--records", type=Path, default=root / "storage/knowledge/public_book_records.json")
    parser.add_argument("--embeddings", type=Path, default=root / "storage/knowledge/public_book_embeddings.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--database-url", default=DEFAULT_URL)
    args = parser.parse_args()
    result = asyncio.run(build_pg_index(
        json.loads(args.records.read_text(encoding="utf-8")),
        json.loads(args.embeddings.read_text(encoding="utf-8")),
        args.source.read_bytes(),
        args.database_url,
    ))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
