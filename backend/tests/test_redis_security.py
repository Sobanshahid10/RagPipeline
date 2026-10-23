"""Opt-in tests against an isolated Redis server, without the offline Redis stub."""

import os
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from redis.asyncio.client import Redis
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.query import _reserve_query as reserve_query_impl
from app.config import settings
from app.core.security_middleware import RateLimitingMiddleware

REDIS_URL = os.environ.get("RAG_TEST_REDIS_URL")


@pytest.mark.asyncio
async def test_production_rate_limiter_fails_closed_on_redis_failure(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    limiter = RateLimitingMiddleware(None)
    limiter._redis = AsyncMock()
    limiter._redis.eval.side_effect = ConnectionError("offline")
    next_handler = AsyncMock()
    response = await limiter.dispatch(
        Request(
            {
                "type": "http",
                "headers": [],
                "method": "GET",
                "path": "/limited",
                "client": ("test", 1),
            }
        ),
        next_handler,
    )
    assert response.status_code == 503
    next_handler.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Isolated Redis URL is not configured")
async def test_rate_limit_is_shared_between_api_processes(monkeypatch):
    import redis.asyncio

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "REDIS_URL", REDIS_URL)
    monkeypatch.setattr(redis.asyncio, "from_url", Redis.from_url)
    limiters = [RateLimitingMiddleware(None, requests_per_minute=2) for _ in range(2)]
    request = Request(
        {
            "type": "http",
            "headers": [],
            "method": "GET",
            "path": "/limited",
            "client": (str(uuid.uuid4()), 1),
        }
    )
    handler = AsyncMock(return_value=JSONResponse({"ok": True}))
    try:
        assert (await limiters[0].dispatch(request, handler)).status_code == 200
        assert (await limiters[1].dispatch(request, handler)).status_code == 200
        assert (await limiters[0].dispatch(request, handler)).status_code == 429
        assert handler.await_count == 2
    finally:
        for limiter in limiters:
            if limiter._redis:
                await limiter._redis.aclose()


@pytest.mark.asyncio
@pytest.mark.skipif(not REDIS_URL, reason="Isolated Redis URL is not configured")
async def test_daily_question_budget_is_tenant_scoped_and_atomic(monkeypatch):
    import asyncio
    import redis.asyncio

    monkeypatch.setattr(settings, "REDIS_URL", REDIS_URL)
    monkeypatch.setattr(settings, "QUERY_BUDGET_PER_DAY", 2)
    monkeypatch.setattr(redis.asyncio, "from_url", Redis.from_url)
    tenant = str(uuid.uuid4())
    results = await asyncio.gather(
        *(reserve_query_impl(tenant) for _ in range(4)), return_exceptions=True
    )
    assert results.count(None) == 2
    errors = [result for result in results if isinstance(result, HTTPException)]
    assert len(errors) == 2 and all(error.status_code == 429 for error in errors)
    await reserve_query_impl(str(uuid.uuid4()))
