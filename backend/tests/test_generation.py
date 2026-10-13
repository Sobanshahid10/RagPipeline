"""Day 8 grounded generation and citation streaming tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.api import query as query_api
from app.generation.citation_parser import extract_citations
from app.generation.prompt_builder import SYSTEM_PROMPT, build_prompt
from app.generation.streamer import stream_response
from app.generation.streamer import ConfiguredLLMClient


CHUNKS = [{
    "id": "chunk-123",
    "document_id": "doc-456",
    "content": "Employees receive 25 days of annual leave.",
    "page_number": 7,
    "bounding_box": {"xmin": 0.1, "ymin": 0.2, "xmax": 0.9, "ymax": 0.3},
    "source_filename": "handbook.pdf",
}]


def test_prompt_builder_labels_grounding_sources():
    system, user = build_prompt("What is the leave policy?", CHUNKS)
    assert system == SYSTEM_PROMPT
    assert "Answer ONLY based on the provided context" in system
    assert "[SOURCE:{chunk_id}:{page_number}]" in system
    assert "--- Chunk 1 (chunk_id: chunk-123, page: 7) ---" in user
    assert "Question: What is the leave policy?" in user


@pytest.mark.asyncio
async def test_groq_answer_model_override_uses_groq_key_and_model(monkeypatch):
    from app.config import settings
    import httpx

    captured = {}

    def handler(request):
        captured["request"] = request
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text='data: {"choices":[{"delta":{"content":"Grounded answer"}}]}\n\ndata: [DONE]\n\n',
        )

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-groq-key")
    client = ConfiguredLLMClient("openai/gpt-oss-20b")
    assert client.provider == "groq"
    assert [part async for part in client.stream("System", "Question")] == ["Grounded answer"]
    request = captured["request"]
    assert json.loads(request.content)["model"] == "openai/gpt-oss-20b"
    assert request.headers["authorization"] == "Bearer test-groq-key"


@pytest.mark.asyncio
async def test_selected_groq_model_requires_key(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "GROQ_API_KEY", None)
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        _ = [part async for part in ConfiguredLLMClient("openai/gpt-oss-120b").stream("System", "Question")]


def test_query_accepts_current_models_and_rejects_retired_ids():
    assert query_api.QueryRequest(query="Q", model="openai/gpt-oss-120b").model == "openai/gpt-oss-120b"
    assert query_api.QueryRequest(query="Q", model="gemini-3.7-flash").model == "gemini-3.7-flash"
    with pytest.raises(ValidationError):
        query_api.QueryRequest(query="Q", model="gemini-2.0-flash")


def test_citation_parser_resolves_bounding_box_and_ignores_unknown_sources():
    answer = (
        "Employees receive 25 days. [SOURCE:chunk-123:7] "
        "Unknown claim. [SOURCE:missing:2]"
    )
    citations = extract_citations(answer, CHUNKS)
    assert citations == [{
        "chunk_id": "chunk-123",
        "document_id": "doc-456",
        "page_number": 7,
        "bounding_box": CHUNKS[0]["bounding_box"],
        "source_filename": "handbook.pdf",
        "excerpt": CHUNKS[0]["content"][:200],
    }]


@pytest.mark.asyncio
async def test_streamer_emits_tokens_citations_then_done_metadata():
    class FakeLLM:
        async def stream(self, system, user_prompt):
            yield "Employees receive 25 days. "
            yield "[SOURCE:chunk-123:7]"

    events = [event async for event in stream_response(
        "What is the leave policy?", CHUNKS, FakeLLM(), route_used="FACTUAL_VECTOR"
    )]
    assert [event["type"] for event in events] == ["token", "token", "citation", "done"]
    assert events[2]["citation"]["bounding_box"] == CHUNKS[0]["bounding_box"]
    metadata = events[-1]["metadata"]
    assert metadata["route_used"] == "FACTUAL_VECTOR"
    assert metadata["chunks_retrieved"] == 1
    assert metadata["prompt_tokens"] > 0
    assert metadata["completion_tokens"] > 0
    assert metadata["total_latency_ms"] >= metadata["ttft_ms"]


@pytest.mark.asyncio
async def test_query_endpoint_cache_event_and_feedback(monkeypatch):
    monkeypatch.setattr(query_api, "process_query", AsyncMock(return_value={
        "answer": "Cached leave answer",
        "source": "cache",
        "latency_ms": 2.5,
    }))
    persist = AsyncMock()
    monkeypatch.setattr(query_api, "_persist_interaction", persist)
    user = SimpleNamespace(id="11111111-1111-1111-1111-111111111111", tenant_id="22222222-2222-2222-2222-222222222222")

    response = await query_api.query_documents(query_api.QueryRequest(query="leave"), user)
    events = []
    async for event in response.body_iterator:
        # The compatibility response encodes SSE; installed sse-starlette retains dict events.
        if isinstance(event, str):
            data_line = next(line for line in event.splitlines() if line.startswith("data: "))
            events.append(json.loads(data_line[6:]))
        else:
            payload = event.get("data", event) if isinstance(event, dict) else event
            events.append(json.loads(payload) if isinstance(payload, str) else payload)
    assert events[0]["type"] == "done"
    assert events[0]["answer"] == "Cached leave answer"
    assert events[0]["metadata"]["source"] == "cache"
    persist.assert_awaited_once()

    connection = AsyncMock()
    connection.execute.return_value = "UPDATE 1"
    monkeypatch.setattr(query_api.asyncpg, "connect", AsyncMock(return_value=connection))
    interaction_id = events[0]["metadata"]["interaction_id"]
    feedback = await query_api.submit_feedback(
        interaction_id=query_api.uuid.UUID(interaction_id),
        request=query_api.FeedbackRequest(feedback=1),
        current_user=user,
    )
    assert feedback["feedback"] == 1
    connection.close.assert_awaited_once()
