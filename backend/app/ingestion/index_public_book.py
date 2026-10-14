"""Store validated public-book embeddings in a local, reproducible SQLite index.

Vectors are stored as float32 blobs and searched exactly at this corpus size.
FTS5 and B-tree indexes support later text and metadata filtering. This is a
learning-track store, separate from the application's 1536-dim pgvector table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any

import numpy as np

from .embed_public_book import DIMENSIONS, INPUT_TEMPLATE_VERSION, MODEL_ID

SCHEMA_VERSION = 2


def validate_inputs(
    records_artifact: dict[str, Any], embeddings_artifact: dict[str, Any], source_bytes: bytes
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    if records_artifact.get("source_sha256") != source_hash or embeddings_artifact.get("source_sha256") != source_hash:
        raise ValueError("Source book has changed; rerun earlier steps")
    if embeddings_artifact.get("status") != "complete":
        raise ValueError("Embedding artifact is incomplete")
    if embeddings_artifact.get("model") != MODEL_ID or embeddings_artifact.get("dimensions") != DIMENSIONS:
        raise ValueError("Embedding model or dimension does not match this index")
    if embeddings_artifact.get("input_template_version") != INPUT_TEMPLATE_VERSION:
        raise ValueError("Embedding recipe version does not match this index")
    records = records_artifact.get("records")
    embeddings = embeddings_artifact.get("records")
    if not isinstance(records, list) or not isinstance(embeddings, list):
        raise ValueError("Missing records")
    if len(records) != len(embeddings) or len(records) != records_artifact.get("record_count") or len(records) != embeddings_artifact.get("record_count"):
        raise ValueError("Record counts disagree")
    if len({record["id"] for record in records}) != len(records):
        raise ValueError("Duplicate record IDs")
    for record, item in zip(records, embeddings, strict=True):
        if record["id"] != item["id"]:
            raise ValueError("Record ID/order mismatch")
        content_hash = hashlib.sha256(record["content"].encode("utf-8")).hexdigest()
        if record["metadata"]["content_sha256"] != content_hash or item["content_sha256"] != content_hash:
            raise ValueError(f"Content hash mismatch for {record['id']}")
        values = item["vector"]
        if len(values) != DIMENSIONS or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
            raise ValueError(f"Invalid vector for {record['id']}")
        if not 0.98 <= math.sqrt(sum(v * v for v in values)) <= 1.02:
            raise ValueError(f"Non-unit vector for {record['id']}")
    return list(zip(records, embeddings, strict=True))


def build_index(
    records_artifact: dict[str, Any], embeddings_artifact: dict[str, Any], source_bytes: bytes, output: Path
) -> dict[str, Any]:
    pairs = validate_inputs(records_artifact, embeddings_artifact, source_bytes)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE manifest (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    schema_version INTEGER NOT NULL,
                    source_sha256 TEXT NOT NULL,
                    model TEXT NOT NULL,
                    model_sha256 TEXT NOT NULL,
                    input_template_version INTEGER NOT NULL,
                    dimensions INTEGER NOT NULL CHECK(dimensions = 384),
                    record_count INTEGER NOT NULL
                );
                CREATE TABLE chunks (
                    ordinal INTEGER PRIMARY KEY,
                    id TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    section_owner TEXT NOT NULL,
                    section_title TEXT NOT NULL,
                    unit_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    embedding BLOB NOT NULL CHECK(length(embedding) = 1536)
                );
                CREATE INDEX idx_chunks_owner ON chunks(section_owner);
                CREATE INDEX idx_chunks_unit_type ON chunks(unit_type);
                CREATE INDEX idx_chunks_section ON chunks(section_title);
                CREATE VIRTUAL TABLE chunks_fts USING fts5(content, content='chunks', content_rowid='ordinal');
                """
            )
            connection.execute(
                "INSERT INTO manifest VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (
                    SCHEMA_VERSION,
                    records_artifact["source_sha256"],
                    embeddings_artifact["model"],
                    embeddings_artifact["model_sha256"],
                    INPUT_TEMPLATE_VERSION,
                    DIMENSIONS,
                    len(pairs),
                ),
            )
            for ordinal, (record, item) in enumerate(pairs, start=1):
                metadata = record["metadata"]
                vector = np.asarray(item["vector"], dtype="<f4")
                connection.execute(
                    "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        ordinal, record["id"], record["content"], metadata["content_sha256"],
                        metadata["section_owner"], metadata["section_title"], metadata["unit_type"],
                        json.dumps(metadata, ensure_ascii=False, separators=(",", ":")), vector.tobytes(),
                    ),
                )
            connection.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')")
            connection.commit()
            count = connection.execute("SELECT count(*) FROM chunks").fetchone()[0]
            fts_count = connection.execute("SELECT count(*) FROM chunks_fts").fetchone()[0]
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            indexes = {row[1] for row in connection.execute("PRAGMA index_list(chunks)")}
            if count != len(pairs) or fts_count != count or integrity != "ok":
                raise ValueError("SQLite index verification failed")
            if not {"idx_chunks_owner", "idx_chunks_unit_type", "idx_chunks_section"} <= indexes:
                raise ValueError("Missing metadata indexes")
        finally:
            connection.close()
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "path": str(output), "record_count": count, "dimensions": DIMENSIONS,
        "source_sha256": records_artifact["source_sha256"], "model": MODEL_ID,
        "vector_search": "exact cosine scan", "text_index": "FTS5",
    }


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Build the local public-book index")
    parser.add_argument("--records", type=Path, default=root / "storage/knowledge/public_book_records.json")
    parser.add_argument("--embeddings", type=Path, default=root / "storage/knowledge/public_book_embeddings.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage/knowledge/public_book_index.sqlite3")
    args = parser.parse_args()
    result = build_index(
        json.loads(args.records.read_text(encoding="utf-8")),
        json.loads(args.embeddings.read_text(encoding="utf-8")),
        args.source.read_bytes(),
        args.output,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
