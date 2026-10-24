import json
import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.api import query
from app.config import settings
from app.generation.citation_parser import normalize_citation_format, validate_answer_citations
from app.generation.errors import AnswerFailure
from app.generation.streamer import ConfiguredLLMClient, stream_response


CHUNKS = [{"id": "chunk-1", "page_number": 1, "content": "The service uses PostgreSQL."}]


@pytest.mark.asyncio
async def test_one_correction_is_reverified_and_failed_draft_is_never_emitted():
    class Model:
        calls = 0
        verify = AsyncMock(side_effect=[False, True])

        async def stream(self, *args):
            self.calls += 1
            if self.calls == 1:
                yield "Uses an invented database. [SOURCE:chunk-1:1]"
            else:
                yield "Uses PostgreSQL. [SOURCE:chunk-1:1]"

    model = Model()
    events = [event async for event in stream_response("Database?", CHUNKS, model)]
    assert model.calls == 2
    assert model.verify.await_count == 2
    assert "invented" not in "".join(e.get("content", "") for e in events)
    assert events[-1]["metadata"]["correction_attempts"] == 1


def test_normalizing_format_never_authorizes_unknown_sources_or_wrong_pages():
    valid = normalize_citation_format("Uses PostgreSQL. [ SOURCE:chunk-1:1 ]")
    assert validate_answer_citations(valid, CHUNKS)
    for citation in ["【 SOURCE:unknown:1 】", "[ SOURCE:chunk-1:9 ]"]:
        assert not validate_answer_citations(normalize_citation_format("Claim. " + citation), CHUNKS)


@pytest.mark.asyncio
async def test_spaced_citations_are_validated_and_audited_before_delivery():
    audit = AsyncMock(return_value=True)

    class Model:
        verify = audit

        async def stream(self, *args):
            yield "Uses PostgreSQL. [ SOURCE:chunk-1:1 ]"

    events = [event async for event in stream_response("Database?", CHUNKS, Model())]
    assert events[0]["content"] == "Uses PostgreSQL. [SOURCE:chunk-1:1]"
    assert events[-1]["metadata"]["validation"] == "citations_and_support"
    assert audit.await_args.args[0] == events[0]["content"]


@pytest.mark.asyncio
async def test_audit_provider_failure_is_distinct_from_an_unsupported_answer():
    class Model:
        async def stream(self, *args):
            yield "Uses PostgreSQL. [SOURCE:chunk-1:1]"

        async def verify(self, *args):
            raise AnswerFailure("provider_timeout", "Provider timed out.", retryable=True)

    emitted = []
    with pytest.raises(AnswerFailure) as error:
        async for event in stream_response("Database?", CHUNKS, Model()):
            emitted.append(event)
    assert error.value.code == "verification_provider_timeout"
    assert emitted == []


@pytest.mark.asyncio
async def test_provider_outage_error_never_exposes_response_body(monkeypatch):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(503, text="private provider payload"))),
    )
    with pytest.raises(AnswerFailure) as error:
        _ = [part async for part in ConfiguredLLMClient("openai/gpt-oss-120b").stream("system", "question")]
    assert error.value.code == "provider_unavailable"
    assert "private provider payload" not in str(error.value)


@pytest.mark.asyncio
async def test_failed_answer_is_not_persisted_as_a_success(monkeypatch):
    conn = AsyncMock()
    conn.fetch.return_value = []

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    class Model:
        model = "openai/gpt-oss-120b"
        provider = "groq"

        async def stream(self, *args):
            yield "Uses PostgreSQL. [SOURCE:chunk-1:1]"

        async def verify(self, *args):
            return False

    monkeypatch.setattr(settings, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(query, "tenant_connection", scoped)
    monkeypatch.setattr(query, "ConfiguredLLMClient", lambda *args: Model())
    monkeypatch.setattr(query, "process_query", AsyncMock(return_value={"chunks": CHUNKS}))
    persist = AsyncMock()
    monkeypatch.setattr(query, "_persist_interaction", persist)
    response = await query.query_documents(
        query.QueryRequest(query="Database?", model="openai/gpt-oss-120b"),
        SimpleNamespace(id="11111111-1111-4111-8111-111111111111", tenant_id="22222222-2222-4222-8222-222222222222"),
    )
    events = []
    async for event in response.body_iterator:
        if isinstance(event, str):
            events.append(json.loads(next(line[6:] for line in event.splitlines() if line.startswith("data: "))))
        else:
            events.append(json.loads(event["data"]))
    assert events == [{"type": "error", "code": "source_support_failed", "retryable": False, "message": "The answer did not pass the source support check and was withheld. Try a narrower question or inspect the source document."}]
    persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_answer_deadline_ends_a_provider_that_never_finishes(monkeypatch):
    conn = AsyncMock()
    conn.fetch.return_value = []

    @asynccontextmanager
    async def scoped(tenant):
        yield conn

    class Model:
        model = "gemini-3.8-flash"
        provider = "gemini"

        async def stream(self, *args):
            await asyncio.Event().wait()
            yield "unreachable"

    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ANSWER_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setattr(query, "tenant_connection", scoped)
    monkeypatch.setattr(query, "ConfiguredLLMClient", lambda *args: Model())
    monkeypatch.setattr(query, "process_query", AsyncMock(return_value={"chunks": CHUNKS}))
    persist = AsyncMock()
    monkeypatch.setattr(query, "_persist_interaction", persist)
    response = await query.query_documents(
        query.QueryRequest(query="Database?", model="gemini-3.8-flash"),
        SimpleNamespace(id="11111111-1111-4111-8111-111111111111", tenant_id="22222222-2222-4222-8222-222222222222"),
    )

    async def consume():
        return [event async for event in response.body_iterator]

    events = await asyncio.wait_for(consume(), timeout=1)
    event = events[-1]
    if isinstance(event, str):
        payload = json.loads(next(line[6:] for line in event.splitlines() if line.startswith("data: ")))
    else:
        payload = json.loads(event["data"])
    assert payload["type"] == "error"
    assert payload["code"] == "answer_timeout"
    persist.assert_not_awaited()


def test_detailed_audit_requires_consistent_boolean_and_claims():
    from app.generation.evidence import parse_support_audit

    assert parse_support_audit('{"supported":true,"unsupported_claims":[]}') == (True, [])
    assert parse_support_audit('{"supported":false,"unsupported_claims":["Wrong threshold"]}') == (False, ["Wrong threshold"])
    for raw in ['{"supported":1,"unsupported_claims":[]}',
                '{"supported":true,"unsupported_claims":["Wrong threshold"]}',
                '{"supported":false,"unsupported_claims":[]}',
                '{"supported":true,"extra":"ignore evidence"}', 'not JSON']:
        with pytest.raises(ValueError):
            parse_support_audit(raw)


@pytest.mark.asyncio
async def test_correction_receives_specific_audit_mismatch_and_is_rechecked():
    class Model:
        unsupported_claims = []
        calls = 0

        async def stream(self, system, prompt):
            self.calls += 1
            if self.calls == 1:
                yield 'Uses MySQL. [SOURCE:chunk-1:1]'
            else:
                assert 'MySQL is not in the source; it says PostgreSQL' in prompt
                yield 'Uses PostgreSQL. [SOURCE:chunk-1:1]'

        async def verify(self, answer, chunks):
            if self.calls == 1:
                self.unsupported_claims = ['MySQL is not in the source; it says PostgreSQL']
                return False
            return True

    events = [e async for e in stream_response('Database?', CHUNKS, Model())]
    assert events[0]['content'] == 'Uses PostgreSQL. [SOURCE:chunk-1:1]'
    assert events[-1]['metadata']['correction_attempts'] == 1


@pytest.mark.asyncio
async def test_unreadable_audit_is_not_reported_as_unsupported_source():
    client = ConfiguredLLMClient('openai/gpt-oss-120b')

    async def invalid_stream(*args):
        yield '{"supported":"true"}'

    client.stream = invalid_stream
    with pytest.raises(AnswerFailure) as error:
        await client.verify('Uses PostgreSQL. [SOURCE:chunk-1:1]', CHUNKS)
    assert error.value.code == 'invalid_audit_response'
    assert error.value.retryable


@pytest.mark.asyncio
async def test_short_rate_limit_retries_only_the_rejected_call(monkeypatch):
    from app.generation import streamer
    streamer._provider_cooldowns.clear()
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'short-limit-test')
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={'retry-after': '0.001'})
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"OK"}}]}\n\ndata: [DONE]\n\n')

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    client = ConfiguredLLMClient('openai/gpt-oss-120b')
    assert [p async for p in client.stream('system', 'question')] == ['OK']
    assert len(calls) == 2
    streamer._provider_cooldowns.clear()


@pytest.mark.asyncio
async def test_long_rate_limit_blocks_repeat_calls_and_reports_wait(monkeypatch):
    from app.generation import streamer
    streamer._provider_cooldowns.clear()
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'long-limit-test')
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, headers={'retry-after': '120'}, text='private quota payload')

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    for _ in range(2):
        client = ConfiguredLLMClient('openai/gpt-oss-120b')
        with pytest.raises(AnswerFailure) as error:
            _ = [p async for p in client.stream('system', 'question')]
        assert error.value.code == 'provider_rate_limited'
        assert 119 < error.value.retry_after_seconds <= 120
        assert 'private quota payload' not in str(error.value)
    assert len(calls) == 1
    streamer._provider_cooldowns.clear()


@pytest.mark.asyncio
async def test_audit_uses_smaller_budget_and_keeps_selected_model(monkeypatch):
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'audit-budget-test')
    payloads = []

    def handler(request):
        payloads.append(json.loads(request.content))
        answer = json.dumps({'supported': True, 'unsupported_claims': []})
        return httpx.Response(200, json={'choices': [{'message': {'content': answer}, 'finish_reason': 'stop'}]})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))
    client = ConfiguredLLMClient('openai/gpt-oss-120b')
    assert await client.verify('Uses PostgreSQL. [SOURCE:chunk-1:1]', CHUNKS)
    assert payloads[0]['max_tokens'] == 1024
    assert payloads[0]['model'] == 'openai/gpt-oss-120b'
    assert payloads[0]['stream'] is False
    assert payloads[0]['reasoning_effort'] == 'low'
    schema = payloads[0]['response_format']['json_schema']
    assert schema['strict'] is True
    assert schema['schema']['additionalProperties'] is False
    assert not client._checking_sources


@pytest.mark.asyncio
@pytest.mark.parametrize('model', ['openai/gpt-oss-120b', 'openai/gpt-oss-20b'])
async def test_truncated_audit_never_accepts_even_complete_looking_json(monkeypatch, model):
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'truncated-audit-test')
    real_client = httpx.AsyncClient
    response = {'choices': [{'message': {'content': '{"supported":true,"unsupported_claims":[]}'}, 'finish_reason': 'length'}]}
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(200,json=response))))
    with pytest.raises(AnswerFailure) as error:
        await ConfiguredLLMClient(model).verify('Uses PostgreSQL. [SOURCE:chunk-1:1]', CHUNKS)
    assert error.value.code == 'incomplete_audit_response'


@pytest.mark.asyncio
async def test_structured_negative_audit_still_withholds_claims(monkeypatch):
    monkeypatch.setattr(settings, 'GROQ_API_KEY', 'negative-audit-test')
    real_client = httpx.AsyncClient
    response = {'choices': [{'message': {'content': '{"supported":false,"unsupported_claims":["MySQL is not in the source"]}'}, 'finish_reason': 'stop'}]}
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda request: httpx.Response(200,json=response))))
    client = ConfiguredLLMClient('openai/gpt-oss-20b')
    assert not await client.verify('Uses MySQL. [SOURCE:chunk-1:1]', CHUNKS)
    assert client.unsupported_claims == ['MySQL is not in the source']
