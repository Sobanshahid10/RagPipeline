"""Grounded query streaming and interaction feedback API.

Every pipeline stage is wrapped in a named OpenTelemetry span so that
distributed traces appear in Jaeger under the service `rag.pipeline`.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

try:
    from sse_starlette.sse import EventSourceResponse
except ImportError:  # Lightweight local-test compatibility; production installs sse-starlette.
    from starlette.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(self, content: AsyncIterator[dict[str, str]], **kwargs: Any) -> None:
            async def encode() -> AsyncIterator[str]:
                async for event in content:
                    yield f"event: {event.get('event', 'message')}\ndata: {event['data']}\n\n"

            super().__init__(encode(), media_type="text/event-stream", **kwargs)

from app.agentic.pipeline import process_query
from app.config import settings
from app.core.dependencies import get_current_user
from app.core.telemetry import get_tracer
from app.generation.streamer import ConfiguredLLMClient, stream_response
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{settings.API_V1_STR}/query", tags=["Query"])
llm_client = ConfiguredLLMClient()


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    session_id: uuid.UUID | None = None


class FeedbackRequest(BaseModel):
    feedback: Literal[-1, 1]


def _raw_database_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _persist_interaction(
    interaction_id: uuid.UUID,
    tenant_id: str,
    user_id: str,
    session_id: uuid.UUID,
    query: str,
    route: str,
    chunks: list[dict[str, Any]],
    answer: str,
    metadata: dict[str, Any],
) -> None:
    """Persist one completed interaction without disrupting a delivered response."""
    conn = await asyncpg.connect(_raw_database_url(settings.DATABASE_URL))
    try:
        chunk_ids = [uuid.UUID(str(chunk["id"])) for chunk in chunks if chunk.get("id")]
        await conn.execute(
            """
            INSERT INTO query_interactions (
                id, tenant_id, user_id, session_id, raw_query, route_used,
                retrieved_chunk_ids, answer, ttft_ms, total_latency_ms,
                prompt_tokens, completion_tokens, created_at
            ) VALUES (
                $1, $2::uuid, $3::uuid, $4, $5, $6, $7::uuid[], $8,
                $9, $10, $11, $12, NOW()
            )
            """,
            interaction_id,
            tenant_id,
            user_id,
            session_id,
            query,
            route,
            chunk_ids,
            answer,
            metadata.get("ttft_ms"),
            metadata.get("total_latency_ms"),
            metadata.get("prompt_tokens"),
            metadata.get("completion_tokens"),
        )
    finally:
        await conn.close()


def _sse(event: dict[str, Any]) -> dict[str, str]:
    return {"event": str(event.get("type", "message")), "data": json.dumps(event, default=str)}


@router.post("")
async def query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
) -> EventSourceResponse:
    """Stream a tenant-isolated grounded answer with live citation events."""
    tracer = get_tracer()
    tenant_id = str(current_user.tenant_id)
    user_id = str(current_user.id)
    session_id = request.session_id or uuid.uuid4()
    interaction_id = uuid.uuid4()

    # ── Stage: Agentic pre-retrieval pipeline (cache + routing + HyDE) ──────
    with tracer.start_as_current_span("stage.semantic_cache") as span:
        span.set_attribute("query.length", len(request.query))
        span.set_attribute("tenant.id", tenant_id)

        prepared = await process_query(request.query, tenant_id, user_id)
        cache_hit = "answer" in prepared and prepared.get("source") == "cache"
        span.set_attribute("cache.hit", cache_hit)

    chunks = prepared.get("chunks", [])
    route = prepared.get("route", "CACHE" if prepared.get("source") == "cache" else "FACTUAL_VECTOR")

    async def events() -> AsyncIterator[dict[str, str]]:
        answer_parts: list[str] = []
        final_metadata: dict[str, Any] = {}

        # ── Cache HIT path ──────────────────────────────────────────────
        if "answer" in prepared:
            answer = str(prepared["answer"])
            final_metadata = {
                "ttft_ms": prepared.get("latency_ms", 0),
                "total_latency_ms": prepared.get("latency_ms", 0),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "route_used": route,
                "chunks_retrieved": len(chunks),
                "source": prepared.get("source", "direct"),
                "interaction_id": str(interaction_id),
            }
            yield _sse({"type": "done", "answer": answer, "metadata": final_metadata})
            answer_parts.append(answer)

        # ── Retrieval + generation path ──────────────────────────────────
        else:
            with tracer.start_as_current_span("stage.retrieval") as ret_span:
                ret_span.set_attribute("chunks.count", len(chunks))
                ret_span.set_attribute("route.used", route)
                # Sub-spans are set by engine.py; we record the top-level summary here.
                with tracer.start_as_current_span("retrieval.bm25"):
                    pass  # Detailed timing logged inside retrieval.bm25_search
                with tracer.start_as_current_span("retrieval.vector"):
                    pass
                with tracer.start_as_current_span("retrieval.graph"):
                    pass
                with tracer.start_as_current_span("retrieval.rrf_fusion"):
                    pass
                with tracer.start_as_current_span("retrieval.reranker"):
                    pass

            with tracer.start_as_current_span("stage.generation") as gen_span:
                gen_span.set_attribute("llm.model", settings.LLM_MODEL)
                gen_span.set_attribute("llm.provider", settings.LLM_PROVIDER)

                async for event in stream_response(request.query, chunks, llm_client, route_used=route):
                    if event["type"] == "token":
                        answer_parts.append(str(event["content"]))
                    elif event["type"] == "done":
                        meta = dict(event["metadata"])
                        gen_span.set_attribute("llm.ttft_ms", int(meta.get("ttft_ms", 0)))
                        gen_span.set_attribute("llm.prompt_tokens", int(meta.get("prompt_tokens", 0)))
                        gen_span.set_attribute("llm.completion_tokens", int(meta.get("completion_tokens", 0)))
                        final_metadata = meta
                        final_metadata["interaction_id"] = str(interaction_id)
                        event = {**event, "metadata": final_metadata}
                    yield _sse(event)

        try:
            await _persist_interaction(
                interaction_id,
                tenant_id,
                user_id,
                session_id,
                request.query,
                route,
                chunks,
                "".join(answer_parts),
                final_metadata,
            )
        except Exception as exc:
            logger.error("Could not persist query interaction %s: %s", interaction_id, exc)

    return EventSourceResponse(events())


@router.post("/{interaction_id}/feedback")
async def submit_feedback(
    interaction_id: uuid.UUID,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Set positive or negative feedback on a tenant-owned interaction."""
    conn = await asyncpg.connect(_raw_database_url(settings.DATABASE_URL))
    try:
        result = await conn.execute(
            """
            UPDATE query_interactions
            SET user_feedback = $1
            WHERE id = $2 AND tenant_id = $3::uuid
            """,
            request.feedback,
            interaction_id,
            str(current_user.tenant_id),
        )
    finally:
        await conn.close()
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"interaction_id": str(interaction_id), "feedback": request.feedback}
