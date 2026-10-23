"""Opt-in PostgreSQL regressions; use an isolated database, never production."""

import io
import os
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
import pytest_asyncio
from app.api import documents
from app.config import settings
from app.db.tenant import tenant_connection
from app.ingestion import pipeline
from fastapi import HTTPException, UploadFile

ADMIN_URL = os.environ.get("RAG_TEST_ADMIN_URL")
RUNTIME_URL = os.environ.get("RAG_TEST_RUNTIME_URL")
pytestmark = pytest.mark.skipif(
    not ADMIN_URL or not RUNTIME_URL,
    reason="Isolated PostgreSQL test URLs are not configured",
)


@pytest_asyncio.fixture
async def workspace(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DATABASE_URL", RUNTIME_URL)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(documents, "UPLOAD_DIR", tmp_path)
    admin = await asyncpg.connect(ADMIN_URL)
    tenants = [uuid.uuid4(), uuid.uuid4()]
    users = [
        SimpleNamespace(id=uuid.uuid4(), tenant_id=t, roles=["admin"]) for t in tenants
    ]
    for user in users:
        await admin.execute(
            "INSERT INTO tenants(id,name,slug) VALUES($1,$2,$3)",
            user.tenant_id,
            "Test workspace",
            str(user.tenant_id),
        )
        await admin.execute(
            "INSERT INTO users(id,tenant_id,email,hashed_password,roles) VALUES($1,$2,$3,'unused','{admin}')",
            user.id,
            user.tenant_id,
            str(user.id) + "@example.com",
        )
    try:
        yield admin, users, tmp_path
    finally:
        for tenant in tenants:
            await admin.execute("DELETE FROM tenants WHERE id=$1", tenant)
        await admin.close()


@pytest.mark.asyncio
async def test_runtime_role_enforces_rls_and_tenant_dedup(workspace, monkeypatch):
    admin, (alice, bob), tmp_path = workspace
    dispatched = MagicMock()
    monkeypatch.setattr(documents.process_document, "delay", dispatched)
    content = b"Workspace policy grants 25 leave days."
    first = await documents.upload_document(
        UploadFile(filename="policy.txt", file=io.BytesIO(content)), alice
    )
    second = await documents.upload_document(
        UploadFile(filename="policy.txt", file=io.BytesIO(content)), bob
    )
    assert first.document_id != second.document_id
    assert dispatched.call_count == 2
    assert len(await documents.list_documents(alice)) == 1
    assert len(await documents.list_documents(bob)) == 1
    async with tenant_connection(str(alice.tenant_id)) as conn:
        rows = await conn.fetch("SELECT tenant_id FROM documents")
        assert [row["tenant_id"] for row in rows] == [alice.tenant_id]
        assert not await conn.fetchval(
            "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )
    runtime = await asyncpg.connect(RUNTIME_URL)
    try:
        assert await runtime.fetchval("SELECT count(*) FROM documents") == 0
    finally:
        await runtime.close()
    for operation in [
        documents.get_document_status,
        documents.get_document_file,
        documents.delete_document,
    ]:
        with pytest.raises(HTTPException) as error:
            await operation(uuid.UUID(first.document_id), bob)
        assert error.value.status_code == 404
    with pytest.raises(asyncpg.InsufficientPrivilegeError):
        async with tenant_connection(str(bob.tenant_id)) as conn:
            await conn.execute(
                "UPDATE documents SET tenant_id=$1 WHERE id=$2",
                alice.tenant_id,
                uuid.UUID(second.document_id),
            )


@pytest.mark.asyncio
async def test_retry_replaces_partial_chunks_and_publishes_index_only_after_success(
    workspace, monkeypatch
):
    admin, (alice, _), tmp_path = workspace
    monkeypatch.setattr(documents.process_document, "delay", MagicMock())
    result = await documents.upload_document(
        UploadFile(
            filename="policy.txt",
            file=io.BytesIO(b"Employees receive 25 days of leave."),
        ),
        alice,
    )
    monkeypatch.setattr(pipeline, "embedding_identity", lambda: "test-model:v2")
    monkeypatch.setattr(
        pipeline,
        "parse_document",
        lambda path: [
            {
                "content": "Employees receive 25 days of leave.",
                "page_number": 1,
                "bounding_boxes": [{"text": "Wrong region", "xmin": 0.1}],
            }
        ],
    )
    monkeypatch.setattr(pipeline, "mask_pii", lambda text: text)
    monkeypatch.setattr(
        pipeline,
        "embed_batch",
        AsyncMock(side_effect=lambda texts: [[0.1] * 1536 for _ in texts]),
    )
    monkeypatch.setattr(
        pipeline, "extract_triples", AsyncMock(side_effect=RuntimeError("graph down"))
    )
    status = await pipeline.run_pipeline(
        result.document_id,
        str(alice.tenant_id),
        str(tmp_path / f"{result.document_id}.txt"),
        documents.process_document.delay.call_args.args[3],
    )
    assert status["status"] == "indexed"
    doc = await documents.get_document_status(uuid.UUID(result.document_id), alice)
    assert doc.graph_status == "degraded" and doc.chunk_count > 0
    expected = doc.chunk_count
    await documents.retry_document(uuid.UUID(result.document_id), alice)
    await pipeline.run_pipeline(
        result.document_id,
        str(alice.tenant_id),
        str(tmp_path / f"{result.document_id}.txt"),
        documents.process_document.delay.call_args.args[3],
    )
    doc = await documents.get_document_status(uuid.UUID(result.document_id), alice)
    assert doc.chunk_count == expected
    assert await admin.fetchval(
        "SELECT bool_and(bounding_box='{}'::jsonb) FROM chunks WHERE document_id=$1",
        uuid.UUID(result.document_id),
    )
    await documents.delete_document(uuid.UUID(result.document_id), alice)
    assert not (tmp_path / f"{result.document_id}.txt").exists()
    assert (
        await admin.fetchval(
            "SELECT count(*) FROM chunks WHERE document_id=$1",
            uuid.UUID(result.document_id),
        )
        == 0
    )


@pytest.mark.asyncio
async def test_failed_dispatch_retains_original_and_retry_recovers(
    workspace, monkeypatch
):
    admin, (alice, _), tmp_path = workspace
    monkeypatch.setattr(
        documents.process_document,
        "delay",
        MagicMock(side_effect=ConnectionError("offline")),
    )
    with pytest.raises(HTTPException) as error:
        await documents.upload_document(
            UploadFile(filename="policy.txt", file=io.BytesIO(b"Policy content.")),
            alice,
        )
    assert error.value.status_code == 503
    rows = await documents.list_documents(alice)
    assert rows[0].status == "failed" and rows[0].stage == "dispatch"
    monkeypatch.setattr(documents.process_document, "delay", MagicMock())
    await documents.retry_document(uuid.UUID(rows[0].document_id), alice)
    assert (
        await documents.get_document_status(uuid.UUID(rows[0].document_id), alice)
    ).status == "pending"


@pytest.mark.asyncio
async def test_history_deletion_and_audit_are_tenant_scoped(workspace, monkeypatch):
    from app.api import query

    admin, (alice, bob), tmp_path = workspace
    await query._persist_interaction(
        uuid.uuid4(),
        str(alice.tenant_id),
        str(alice.id),
        uuid.uuid4(),
        "Alice question",
        "HYBRID",
        [],
        "Alice answer",
        {},
    )
    await query._persist_interaction(
        uuid.uuid4(),
        str(bob.tenant_id),
        str(bob.id),
        uuid.uuid4(),
        "Bob question",
        "HYBRID",
        [],
        "Bob answer",
        {},
    )
    await query.delete_own_history(alice)
    assert (
        await admin.fetchval(
            "SELECT count(*) FROM query_interactions WHERE user_id=$1", alice.id
        )
        == 0
    )
    assert (
        await admin.fetchval(
            "SELECT count(*) FROM query_interactions WHERE user_id=$1", bob.id
        )
        == 1
    )
    monkeypatch.setattr(documents.process_document, "delay", MagicMock())
    doc = await documents.upload_document(
        UploadFile(filename="audit.txt", file=io.BytesIO(b"Audit policy")), alice
    )
    await documents.delete_document(uuid.UUID(doc.document_id), alice)
    async with tenant_connection(str(alice.tenant_id)) as conn:
        assert await conn.fetchval("SELECT count(*) FROM document_audit_events") == 2
    async with tenant_connection(str(bob.tenant_id)) as conn:
        assert await conn.fetchval("SELECT count(*) FROM document_audit_events") == 0


@pytest.mark.asyncio
async def test_document_scope_reaches_all_three_searches(workspace, monkeypatch):
    from app.retrieval import bm25_search, graph_search, vector_search

    admin, (alice, bob), tmp_path = workspace
    document_ids = [uuid.uuid4(), uuid.uuid4()]
    chunk_ids = [uuid.uuid4(), uuid.uuid4()]
    for index, document_id in enumerate(document_ids):
        await admin.execute(
            """INSERT INTO documents(id,tenant_id,filename,file_type,doc_hash,storage_uri,status)
            VALUES($1,$2,$3,'txt',$4,'unused','indexed')""",
            document_id,
            alice.tenant_id,
            f"{index}.txt",
            str(document_id),
        )
        await admin.execute(
            """INSERT INTO chunks(id,document_id,tenant_id,chunk_index,content,token_count,embedding,sparse_tsv)
            VALUES($1,$2,$3,0,'Alice follows leave policy',5,$4::vector,to_tsvector('english','Alice follows leave policy'))""",
            chunk_ids[index],
            document_id,
            alice.tenant_id,
            str([0.1] * 1536),
        )
        await admin.execute(
            "INSERT INTO entity_triples(tenant_id,source_chunk_id,subject,predicate,object) VALUES($1,$2,'Alice','follows','leave policy')",
            alice.tenant_id,
            chunk_ids[index],
        )
    scope = [str(document_ids[0])]
    lexical = await bm25_search.bm25_search(
        "leave", str(alice.tenant_id), document_ids=scope
    )
    dense = await vector_search.vector_search(
        [0.1] * 1536, str(alice.tenant_id), document_ids=scope
    )
    monkeypatch.setattr(
        graph_search, "extract_query_entities", lambda question: ["Alice"]
    )
    graph = await graph_search.graph_search(
        "Alice", str(alice.tenant_id), document_ids=scope
    )
    for results in [lexical, dense, graph]:
        assert len(results) == 1 and results[0]["document_id"] == scope[0]


@pytest.mark.asyncio
async def test_superseded_job_and_late_dispatch_error_cannot_change_new_attempt(
    workspace, monkeypatch
):
    admin, (alice, _), tmp_path = workspace
    dispatched = MagicMock()
    monkeypatch.setattr(documents.process_document, "delay", dispatched)
    doc = await documents.upload_document(
        UploadFile(filename="versioned.txt", file=io.BytesIO(b"Versioned content.")),
        alice,
    )
    old_job = dispatched.call_args.args[3]
    document_id = uuid.UUID(doc.document_id)
    await admin.execute("UPDATE documents SET status='failed' WHERE id=$1", document_id)
    await documents.retry_document(document_id, alice)
    new_job = dispatched.call_args.args[3]
    assert new_job != old_job
    parse = MagicMock(side_effect=AssertionError("Stale task must not parse"))
    monkeypatch.setattr(pipeline, "parse_document", parse)
    for job in (old_job, None):
        result = await pipeline.run_pipeline(
            doc.document_id,
            str(alice.tenant_id),
            str(tmp_path / f"{doc.document_id}.txt"),
            job,
        )
        assert result["status"] == "superseded"
    parse.assert_not_called()
    monkeypatch.setattr(
        documents.process_document,
        "delay",
        MagicMock(side_effect=ConnectionError("ambiguous publish")),
    )
    with pytest.raises(HTTPException):
        await documents._dispatch(
            doc.document_id, str(alice.tenant_id), "/unused", old_job
        )
    assert (await documents.get_document_status(document_id, alice)).status == "pending"
    await admin.execute(
        "UPDATE documents SET status='processing' WHERE id=$1", document_id
    )
    with pytest.raises(HTTPException):
        await documents._dispatch(
            doc.document_id, str(alice.tenant_id), "/unused", new_job
        )
    assert (
        await documents.get_document_status(document_id, alice)
    ).status == "processing"


@pytest.mark.asyncio
async def test_graph_cannot_traverse_out_of_scope_or_unindexed_bridge(
    workspace, monkeypatch
):
    from app.retrieval import graph_search

    admin, (alice, _), _ = workspace
    doc_ids = [uuid.uuid4(), uuid.uuid4()]
    for index, document_id in enumerate(doc_ids):
        chunk_id = uuid.uuid4()
        await admin.execute(
            """INSERT INTO documents(id,tenant_id,filename,file_type,doc_hash,storage_uri,status)
            VALUES($1,$2,'bridge.txt','txt',$3,'unused','indexed')""",
            document_id,
            alice.tenant_id,
            str(document_id),
        )
        await admin.execute(
            """INSERT INTO chunks(id,document_id,tenant_id,chunk_index,content,token_count)
            VALUES($1,$2,$3,0,'Graph evidence',2)""",
            chunk_id,
            document_id,
            alice.tenant_id,
        )
        await admin.execute(
            """INSERT INTO entity_triples(tenant_id,source_chunk_id,subject,predicate,object)
            VALUES($1,$2,$3,'follows',$4)""",
            alice.tenant_id,
            chunk_id,
            "Alice" if index == 0 else "Bridge",
            "Bridge" if index == 0 else "Policy",
        )
    monkeypatch.setattr(graph_search, "extract_query_entities", lambda q: ["Alice"])
    assert len(await graph_search.graph_search("Alice", str(alice.tenant_id))) == 2
    assert (
        await graph_search.graph_search(
            "Alice", str(alice.tenant_id), document_ids=[str(doc_ids[1])]
        )
        == []
    )
    await admin.execute("UPDATE documents SET status='failed' WHERE id=$1", doc_ids[0])
    assert await graph_search.graph_search("Alice", str(alice.tenant_id)) == []


@pytest.mark.asyncio
async def test_follow_up_history_excludes_other_document_scope(workspace, monkeypatch):
    from app.api import query

    admin, (alice, _), _ = workspace
    session = uuid.uuid4()
    for text, scope in [
        ("Unrelated scoped question", '["other-document"]'),
        ("Relevant all-document question", "[]"),
    ]:
        await query._persist_interaction(
            uuid.uuid4(),
            str(alice.tenant_id),
            str(alice.id),
            session,
            text,
            "HYBRID",
            [],
            "Prior answer",
            {"retrieval_scope": scope},
        )
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock-provider-key")
    prepare = AsyncMock(return_value={"source": "direct", "answer": "Hello"})
    monkeypatch.setattr(query, "process_query", prepare)
    response = await query.query_documents(
        query.QueryRequest(query="Current question", session_id=session), alice
    )
    async for _ in response.body_iterator:
        pass
    retrieval_question = prepare.call_args.args[0]
    assert "Relevant all-document question" in retrieval_question
    assert "Unrelated scoped question" not in retrieval_question
    assert (
        await admin.fetchval(
            "SELECT retrieval_scope FROM query_interactions WHERE raw_query='Current question' AND user_id=$1",
            alice.id,
        )
        == "[]"
    )
