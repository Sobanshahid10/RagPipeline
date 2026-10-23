"""Behavior regressions for the repository security review. No live providers."""

import io
import json
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.api import documents, public_book
from app.config import Settings, settings
from app.core.dependencies import require_writer
from app.generation.citation_parser import extract_citations, validate_answer_citations
from app.generation.streamer import ConfiguredLLMClient, stream_response
from app.ingestion import embedder, pii
from app.main import app
from fastapi import HTTPException, UploadFile

TENANT = uuid.uuid4()
USER = SimpleNamespace(id=uuid.uuid4(), tenant_id=TENANT, roles=["admin"])
CHUNKS = [
    {"id": "c1", "page_number": 2, "content": "Employees receive 25 days of leave."}
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", ""),
        ("POST", "/upload"),
        ("GET", f"/{uuid.uuid4()}"),
        ("GET", f"/{uuid.uuid4()}/file"),
        ("DELETE", f"/{uuid.uuid4()}"),
        ("POST", f"/{uuid.uuid4()}/retry"),
    ],
)
async def test_documents_require_identity(method, path):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://security-test"
    ) as client:
        response = await client.request(method, "/api/v1/documents" + path)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_cannot_fall_back_to_unscoped_delete():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://security-test"
    ) as client:
        response = await client.delete(
            "/api/v1/documents/" + str(uuid.uuid4()),
            headers={"Authorization": "Bearer invalid"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_viewers_cannot_write():
    with pytest.raises(HTTPException) as error:
        await require_writer(SimpleNamespace(roles=["viewer"]))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_file_lookup_hides_foreign_document(monkeypatch):
    conn = AsyncMock()
    conn.fetchrow.return_value = None

    @asynccontextmanager
    async def scoped(tenant):
        assert tenant == str(TENANT)
        yield conn

    monkeypatch.setattr(documents, "tenant_connection", scoped)
    doc_id = uuid.uuid4()
    with pytest.raises(HTTPException) as error:
        await documents.get_document_file(doc_id, USER)
    assert error.value.status_code == 404
    sql, *args = conn.fetchrow.call_args.args
    assert "tenant_id=$2" in sql and args == [doc_id, TENANT]


@pytest.mark.asyncio
async def test_oversized_upload_is_removed(monkeypatch, tmp_path):
    monkeypatch.setattr(documents, "UPLOAD_DIR", tmp_path)
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 4)
    file = UploadFile(filename="data.txt", file=io.BytesIO(b"large text"))
    with pytest.raises(HTTPException) as error:
        await documents.upload_document(file, USER)
    assert error.value.status_code == 413
    assert not list(tmp_path.iterdir())


@pytest.mark.asyncio
async def test_invalid_document_content_is_rejected(tmp_path):
    with pytest.raises(HTTPException) as error:
        await documents._validate_upload(
            UploadFile(filename="bad.pdf", file=io.BytesIO(b"not a PDF")),
            tmp_path / "bad.pdf",
            "pdf",
        )
    assert error.value.status_code == 415


@pytest.mark.asyncio
async def test_dispatch_failure_is_not_success(monkeypatch):
    conn = AsyncMock()

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    monkeypatch.setattr(documents, "tenant_connection", scoped)
    monkeypatch.setattr(
        documents.process_document,
        "delay",
        MagicMock(side_effect=ConnectionError("private broker address")),
    )
    with pytest.raises(HTTPException) as error:
        await documents._dispatch(
            str(uuid.uuid4()), str(TENANT), "/unused", str(uuid.uuid4())
        )
    assert error.value.status_code == 503
    assert "private broker" not in error.value.detail
    assert "status='failed'" in conn.execute.call_args.args[0]


@pytest.mark.asyncio
async def test_embedding_provider_failure_never_becomes_a_vector(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    real = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real(
            transport=httpx.MockTransport(lambda req: httpx.Response(429))
        ),
    )
    with pytest.raises(RuntimeError, match="indexing was stopped"):
        await embedder.embed_batch(["passage"])


@pytest.mark.asyncio
async def test_no_provider_cannot_index_random_vectors():
    with pytest.raises(RuntimeError, match="provider"):
        await embedder.embed_batch(["passage"])


@pytest.mark.asyncio
async def test_malformed_vectors_are_rejected_before_cache(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        embedder,
        "_fetch_gemini_embeddings",
        AsyncMock(return_value=[[float("nan")] * embedder.EMBEDDING_DIM]),
    )
    cache = AsyncMock()
    cache.mget.return_value = [None]
    with pytest.raises(RuntimeError, match="invalid vectors"):
        await embedder.embed_batch(["passage"], cache)
    cache.pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_embedding_batches_are_bounded(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    fetch = AsyncMock(
        side_effect=lambda texts: [[0.1] * embedder.EMBEDDING_DIM for _ in texts]
    )
    monkeypatch.setattr(embedder, "_fetch_gemini_embeddings", fetch)
    assert len(await embedder.embed_batch([str(i) for i in range(65)])) == 65
    assert [len(call.args[0]) for call in fetch.await_args_list] == [32, 32, 1]


@pytest.mark.asyncio
async def test_required_pii_protection_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "PII_REQUIRED", True)
    monkeypatch.setattr(pii, "_presidio_available", False)
    with pytest.raises(RuntimeError, match="PII protection unavailable"):
        pii.mask_pii("John Smith has an IBAN")


def test_uncited_public_answer_is_rejected():
    with pytest.raises(ValueError, match="inline source citations"):
        public_book._parse_answer(
            json.dumps(
                {"answer": "Unsupported fact", "citations": [], "abstained": False}
            ),
            ["S1"],
        )


def test_wrong_page_citation_cannot_be_resolved():
    assert extract_citations("Fact [SOURCE:c1:999]", CHUNKS) == []
    assert not validate_answer_citations("Fact [SOURCE:c1:999]", CHUNKS)


@pytest.mark.parametrize(
    "answer",
    [
        "Uncited claim.\n\nEmployees receive leave. [SOURCE:c1:2]",
        "- Uncited claim.\n- Employees receive leave. [SOURCE:c1:2]",
        "Employees receive leave. [SOURCE:c1:2]\n\nUncited conclusion.",
    ],
)
def test_each_document_answer_paragraph_requires_citations(answer):
    assert not validate_answer_citations(answer, CHUNKS)


def test_cited_document_paragraphs_allow_headings():
    assert validate_answer_citations(
        "## Leave\nEmployees receive leave. [SOURCE:c1:2]\n\n- Paid leave. [SOURCE:c1:2]",
        CHUNKS,
    )


@pytest.mark.parametrize(
    "raw",
    [
        '{"supported":1}',
        '{"supported":"true"}',
        "[true]",
        '{"supported":false}',
        '{"supported":true,"extra":"ignored"}',
        "not JSON",
    ],
)
def test_evidence_audit_rejects_non_boolean_or_malformed_verdicts(raw):
    from app.generation.evidence import support_is_verified

    assert not support_is_verified(raw)


def test_evidence_audit_accepts_only_explicit_support():
    from app.generation.evidence import support_is_verified

    assert support_is_verified('```json\n{"supported":true}\n```')


def test_public_answer_cannot_hide_uncited_paragraph_before_cited_one():
    with pytest.raises(ValueError, match="paragraph"):
        public_book._parse_answer(
            json.dumps(
                {
                    "answer": "Uncited assertion.\n\nSupported claim [S1].",
                    "citations": ["S1"],
                    "abstained": False,
                }
            ),
            ["S1"],
        )


@pytest.mark.asyncio
async def test_delete_commit_failure_preserves_original(monkeypatch, tmp_path):
    path = tmp_path / "original.txt"
    path.write_text("Original content")
    monkeypatch.setattr(documents, "UPLOAD_DIR", tmp_path)
    conn = AsyncMock()
    conn.fetchval.return_value = True
    conn.fetchrow.return_value = {"storage_uri": str(path), "filename": "original.txt"}

    @asynccontextmanager
    async def failed_commit(tenant):
        yield conn
        raise RuntimeError("commit failed")

    monkeypatch.setattr(documents, "tenant_connection", failed_commit)
    with pytest.raises(RuntimeError, match="commit failed"):
        await documents.delete_document(uuid.uuid4(), USER)
    assert path.read_text() == "Original content"


@pytest.mark.asyncio
async def test_unsupported_answer_never_reaches_user():
    class Model:
        async def stream(self, *args):
            yield "Employees receive 99 days. [SOURCE:c1:2]"

        async def verify(self, *args):
            return False

    emitted = []
    with pytest.raises(RuntimeError, match="source support"):
        async for event in stream_response("leave", CHUNKS, Model()):
            emitted.append(event)
    assert emitted == []


@pytest.mark.asyncio
async def test_partial_provider_failure_never_emits_a_draft():
    class Model:
        async def stream(self, *args):
            yield "An unfinished answer"
            raise RuntimeError("interrupted")

    emitted = []
    with pytest.raises(RuntimeError):
        async for event in stream_response("leave", CHUNKS, Model()):
            emitted.append(event)
    assert emitted == []


@pytest.mark.asyncio
async def test_gemini_failure_never_switches_models_or_provider(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-gemini")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-groq")
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(503)

    real = httpx.AsyncClient
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(RuntimeError):
        _ = [
            part
            async for part in ConfiguredLLMClient("gemini-3.7-flash").stream(
                "system", "question"
            )
        ]
    assert len(requests) == 1 and "/gemini-3.7-flash:" in requests[0]


@pytest.mark.asyncio
async def test_retry_refuses_active_document(monkeypatch):
    conn = AsyncMock()
    conn.fetchval.return_value = False

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    monkeypatch.setattr(documents, "tenant_connection", scoped)
    with pytest.raises(HTTPException) as error:
        await documents.retry_document(uuid.uuid4(), USER)
    assert error.value.status_code == 409
    conn.fetchrow.assert_not_called()


def test_production_rejects_known_or_missing_secret():
    with pytest.raises(ValueError, match="unique JWT_SECRET"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            JWT_SECRET="super_secret_jwt_key_change_in_production_2026",
            CORS_ORIGINS=["https://example.com"],
        )


@pytest.mark.asyncio
async def test_forwarded_header_cannot_evade_rate_limit():
    from app.core.security_middleware import RateLimitingMiddleware
    from fastapi import FastAPI

    limited = FastAPI()
    limited.add_middleware(RateLimitingMiddleware, requests_per_minute=2)

    @limited.get("/limited")
    async def endpoint():
        return {"ok": True}

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=limited), base_url="http://test"
    ) as client:
        statuses = [
            (
                await client.get(
                    "/limited", headers={"X-Forwarded-For": f"192.0.2.{i}"}
                )
            ).status_code
            for i in range(3)
        ]
    assert statuses == [200, 200, 429]


@pytest.mark.asyncio
async def test_changed_embedding_model_requires_reindex_before_search(monkeypatch):
    from app.retrieval import engine

    conn = AsyncMock()
    conn.fetchval.return_value = True

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    monkeypatch.setattr(engine, "tenant_connection", scoped)
    monkeypatch.setattr(engine.embedder, "embedding_identity", lambda: "new-model")
    embed = AsyncMock()
    monkeypatch.setattr(engine.embedder, "embed_text", embed)
    with pytest.raises(RuntimeError, match="reindexing"):
        await engine.retrieve("leave policy", str(TENANT))
    embed.assert_not_awaited()


@pytest.mark.parametrize("kind", ["expired", "missing_expiry", "wrong_key", "unsigned"])
def test_jwt_claims_and_signatures_fail_closed(kind):
    from datetime import datetime, timezone

    import jwt
    from app.core.security import decode_access_token

    now = int(datetime.now(timezone.utc).timestamp())
    payload = {"sub": str(USER.id), "iat": now, "exp": now + 60}
    key = settings.JWT_SECRET
    algorithm = "HS256"
    if kind == "expired":
        payload["exp"] = now - 1
    if kind == "missing_expiry":
        payload.pop("exp")
    if kind == "wrong_key":
        key = "a different signing key with sufficient length"
    if kind == "unsigned":
        key = ""
        algorithm = "none"
    token = jwt.encode(payload, key, algorithm=algorithm)
    with pytest.raises(HTTPException) as error:
        decode_access_token(token)
    assert error.value.status_code == 401
