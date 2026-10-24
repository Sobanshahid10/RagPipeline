import asyncio

import pytest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

from app.ingestion import pipeline


@pytest.mark.asyncio
async def test_search_is_ready_before_slow_graph_extraction_finishes(monkeypatch, tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("The service uses PostgreSQL.")
    conn = AsyncMock()
    conn.fetchval.return_value = True
    conn.fetchrow.return_value = {"status": "pending", "storage_uri": str(path), "job_id": "job"}

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    updates = []
    persisted = False
    graph_started = asyncio.Event()
    finish_graph = asyncio.Event()

    async def persist(*args):
        nonlocal persisted
        persisted = True

    async def status(doc_id, state, **metadata):
        if state == "indexed":
            assert persisted
        updates.append((state, metadata))

    async def graph(*args):
        graph_started.set()
        await finish_graph.wait()
        return [[]]

    monkeypatch.setattr(pipeline, "tenant_connection", scoped)
    monkeypatch.setattr(pipeline.settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(pipeline, "embedding_identity", lambda: "test-embedding")
    monkeypatch.setattr(pipeline, "parse_document", lambda path: [{"content": "The service uses PostgreSQL.", "page_number": 1}])
    monkeypatch.setattr(pipeline, "mask_pii", lambda text: text)
    monkeypatch.setattr(pipeline, "generate_contextual_summary", AsyncMock(return_value="Summary"))
    monkeypatch.setattr(pipeline, "semantic_chunk", lambda *args, **kwargs: [{"content": "A", "token_count": 1}])
    monkeypatch.setattr(pipeline, "embed_batch", AsyncMock(return_value=[[1.0]]))
    monkeypatch.setattr(pipeline, "_persist_chunks", persist)
    monkeypatch.setattr(pipeline, "_update_document_status", status)
    monkeypatch.setattr(pipeline, "_extract_graph_batch", graph)
    task = asyncio.create_task(pipeline.run_pipeline("doc", "tenant", str(path), "job"))
    try:
        await asyncio.wait_for(graph_started.wait(), timeout=1)
        assert updates[-1][0] == "indexed"
        assert updates[-1][1]["graph_status"] == "processing"
        assert not task.done()
    finally:
        finish_graph.set()
        await task
    assert updates[-1][1]["graph_status"] == "complete"


@pytest.mark.asyncio
async def test_graph_timeout_cancels_slow_call_without_losing_other_results(monkeypatch):
    cancelled = asyncio.Event()

    async def extract(chunk_id, content, tenant_id):
        if chunk_id == "slow":
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
        return [{"subject": "A", "predicate": "uses", "object": "B"}]

    monkeypatch.setattr(pipeline, "extract_triples", extract)
    monkeypatch.setattr(pipeline.settings, "GRAPH_EXTRACTION_TIMEOUT_SECONDS", 0.02)
    result = await asyncio.wait_for(
        pipeline._extract_graph_batch(
            [{"id": "fast", "content": "A uses B"}, {"id": "slow", "content": "Slow"}],
            "tenant",
        ),
        timeout=1,
    )

    assert result[0] == [{"subject": "A", "predicate": "uses", "object": "B"}]
    assert isinstance(result[1], TimeoutError)
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_graph_failure_does_not_discard_successful_chunk(monkeypatch):
    async def extract(chunk_id, content, tenant_id):
        if chunk_id == "failed":
            raise RuntimeError("Provider unavailable")
        return []

    monkeypatch.setattr(pipeline, "extract_triples", extract)
    result = await pipeline._extract_graph_batch(
        [{"id": "failed", "content": "A"}, {"id": "empty", "content": "B"}],
        "tenant",
    )
    assert isinstance(result[0], RuntimeError)
    assert result[1] == []
