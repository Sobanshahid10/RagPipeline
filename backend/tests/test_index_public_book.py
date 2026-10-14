import hashlib
import sqlite3

import pytest

from backend.app.ingestion.embed_public_book import DIMENSIONS, INPUT_TEMPLATE_VERSION, MODEL_ID
from backend.app.ingestion.index_public_book import build_index


def artifacts():
    source = b"book"
    source_hash = hashlib.sha256(source).hexdigest()
    content = "Umar studies artificial intelligence."
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    metadata = {
        "source_sha256": source_hash, "content_sha256": content_hash,
        "section_owner": "umar", "section_title": "Education", "unit_type": "paragraph",
        "citation_label": "PUBLIC_KNOWLEDGE_BOOK.md:L1",
    }
    records = {
        "source_sha256": source_hash, "record_count": 1,
        "records": [{"id": "one", "content": content, "metadata": metadata}],
    }
    embeddings = {
        "status": "complete", "source_sha256": source_hash, "model": MODEL_ID,
        "model_sha256": "test-weight-hash", "input_template_version": INPUT_TEMPLATE_VERSION,
        "dimensions": DIMENSIONS, "record_count": 1,
        "records": [{"id": "one", "content_sha256": content_hash, "vector": [1.0] + [0.0] * (DIMENSIONS - 1)}],
    }
    return source, records, embeddings


def test_builds_queryable_local_index(tmp_path):
    source, records, embeddings = artifacts()
    path = tmp_path / "index.sqlite3"
    result = build_index(records, embeddings, source, path)
    assert result["record_count"] == 1
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT input_template_version, dimensions, record_count FROM manifest").fetchone() == (INPUT_TEMPLATE_VERSION, DIMENSIONS, 1)
        assert db.execute("SELECT id, section_owner, length(embedding) FROM chunks").fetchone() == ("one", "umar", DIMENSIONS * 4)
        assert db.execute("SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH 'artificial'").fetchall() == [(1,)]


def test_rejects_stale_or_invalid_vectors_without_overwriting(tmp_path):
    source, records, embeddings = artifacts()
    path = tmp_path / "index.sqlite3"
    build_index(records, embeddings, source, path)
    before = path.read_bytes()
    embeddings["records"][0]["vector"] = [0.0] * DIMENSIONS
    with pytest.raises(ValueError, match="Non-unit"):
        build_index(records, embeddings, source, path)
    assert path.read_bytes() == before
