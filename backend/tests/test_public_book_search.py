import hashlib

import pytest

from backend.app.ingestion.embed_public_book import DIMENSIONS, INPUT_TEMPLATE_VERSION, MODEL_ID
from backend.app.ingestion.index_public_book import build_index
from backend.app.retrieval.public_book_search import search_public_book, search_public_book_sqlite
from backend.tests.test_index_public_book import artifacts


class FixedModel:
    model_hash = "test-weight-hash"

    def embed(self, text):
        return [1.0] + [0.0] * (DIMENSIONS - 1), 4, 1


def test_sqlite_search_returns_evidence_and_citation(tmp_path):
    source, records, embeddings = artifacts()
    path = tmp_path / "index.sqlite3"
    build_index(records, embeddings, source, path)
    result = search_public_book_sqlite(
        "What does Umar study?", model=FixedModel(), source_bytes=source,
        database_path=path, top_k=1,
    )
    assert result["hits"][0]["content"] == records["records"][0]["content"]
    assert result["hits"][0]["citation"] == "PUBLIC_KNOWLEDGE_BOOK.md:L1"
    assert result["hits"][0]["score"] == 1.0
    with pytest.raises(ValueError, match="stale"):
        search_public_book_sqlite(
            "What does Umar study?", model=FixedModel(), source_bytes=b"changed",
            database_path=path,
        )


class FakePg:
    def __init__(self, source_hash):
        self.source_hash = source_hash
        self.fetch_called = False

    async def fetchrow(self, query):
        return {
            "source_sha256": self.source_hash,
            "model": MODEL_ID,
            "model_sha256": "test-weight-hash",
            "input_template_version": INPUT_TEMPLATE_VERSION,
            "dimensions": DIMENSIONS,
            "record_count": 1,
        }

    async def fetch(self, query, *args):
        self.fetch_called = True
        assert len(args) == 4
        return [{
            "id": "one", "content": "Umar studies artificial intelligence.",
            "metadata": '{"citation_label":"PUBLIC_KNOWLEDGE_BOOK.md:L1"}',
            "cosine_distance": 0.0,
        }]


@pytest.mark.asyncio
async def test_postgres_search_checks_manifest_and_returns_hit():
    source = b"book"
    db = FakePg(hashlib.sha256(source).hexdigest())
    result = await search_public_book(
        "What does Umar study?", model=FixedModel(), source_bytes=source,
        connection=db, top_k=1,
    )
    assert db.fetch_called
    assert result["hits"][0]["score"] == 1.0
    assert result["hits"][0]["citation"] == "PUBLIC_KNOWLEDGE_BOOK.md:L1"


@pytest.mark.asyncio
async def test_blank_question_rejected_before_database():
    with pytest.raises(ValueError, match="blank"):
        await search_public_book("  ", model=FixedModel(), source_bytes=b"book", connection=FakePg("x"))
