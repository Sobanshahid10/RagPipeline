"""Grounded query streaming and interaction feedback API.

Request/database tracing is provided by optional OpenTelemetry instrumentation;
retrieval durations are recorded by the retrieval engine.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.tenant import tenant_connection

try:
    from sse_starlette.sse import EventSourceResponse
except (
    ImportError
):  # Lightweight local-test compatibility; production installs sse-starlette.
    from starlette.responses import StreamingResponse

    class EventSourceResponse(StreamingResponse):
        def __init__(
            self, content: AsyncIterator[dict[str, str]], **kwargs: Any
        ) -> None:
            async def encode() -> AsyncIterator[str]:
                async for event in content:
                    yield f"event: {event.get('event', 'message')}\ndata: {event['data']}\n\n"

            super().__init__(encode(), media_type="text/event-stream", **kwargs)


from app.agentic.pipeline import process_query
from app.config import settings
from app.core.dependencies import get_current_user
from app.generation.streamer import ConfiguredLLMClient, stream_response
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{settings.API_V1_STR}/query", tags=["Query"])
llm_client = ConfiguredLLMClient()


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    model: (
        Literal[
            "gemini-3.8-flash",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
        ]
        | None
    ) = None
    session_id: uuid.UUID | None = None
    include_context: bool = False
    bypass_cache: bool = False
    document_ids: list[uuid.UUID] | None = Field(default=None, max_length=100)


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
    async with tenant_connection(tenant_id) as conn:
        chunk_ids = [uuid.UUID(str(chunk["id"])) for chunk in chunks if chunk.get("id")]
        await conn.execute(
            """
            INSERT INTO query_interactions (
                id, tenant_id, user_id, session_id, raw_query, route_used,
                retrieved_chunk_ids, answer, ttft_ms, total_latency_ms,
                prompt_tokens, completion_tokens, retrieval_scope, created_at
            ) VALUES (
                $1, $2::uuid, $3::uuid, $4, $5, $6, $7::uuid[], $8,
                $9, $10, $11, $12, $13, NOW()
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
            metadata.get("retrieval_scope"),
        )


def _sse(event: dict[str, Any]) -> dict[str, str]:
    return {
        "event": str(event.get("type", "message")),
        "data": json.dumps(event, default=str),
    }


@router.get("/models")
async def available_models(current_user: User = Depends(get_current_user)):
    gemini = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
    ]
    groq = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    return {
        "models": (gemini if settings.GEMINI_API_KEY else [])
        + (groq if settings.GROQ_API_KEY else []),
        "default_model": settings.LLM_MODEL,
        "embedding_configured": bool(
            settings.GEMINI_API_KEY or settings.OPENAI_API_KEY
        ),
    }


async def _reserve_query(tenant_id):
    from datetime import datetime, timezone

    import redis.asyncio as redis

    client = redis.from_url(
        settings.REDIS_URL, socket_timeout=2, socket_connect_timeout=2
    )
    try:
        key = f"rag:budget:{tenant_id}:{datetime.now(timezone.utc).date()}"
        count = await client.eval(
            "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],172800) end; return n",
            1,
            key,
        )
        if count > settings.QUERY_BUDGET_PER_DAY:
            raise HTTPException(429, "Workspace daily question limit reached")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "Usage accounting service unavailable")
    finally:
        await client.aclose()


@router.delete("/history")
async def delete_own_history(current_user: User = Depends(get_current_user)):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        await conn.execute(
            "DELETE FROM query_interactions WHERE tenant_id=$1 AND user_id=$2",
            current_user.tenant_id,
            current_user.id,
        )
    return {"status": "deleted"}


@router.post("")
async def query_documents(
    request: QueryRequest, current_user: User = Depends(get_current_user)
):
    started = perf_counter()
    tenant_id = str(current_user.tenant_id)
    user_id = str(current_user.id)
    session_id = request.session_id or uuid.uuid4()
    retrieval_scope = json.dumps(sorted({str(i) for i in request.document_ids or []}))
    interaction_id = uuid.uuid4()
    selected_client = ConfiguredLLMClient(request.model)
    # Validate selection before reserving quota or querying any document content.
    keys = {
        "gemini": settings.GEMINI_API_KEY,
        "groq": settings.GROQ_API_KEY,
        "openai": settings.OPENAI_API_KEY,
    }
    if not keys.get(selected_client.provider):
        raise HTTPException(503, "Selected provider is not configured")
    if request.document_ids == []:
        raise HTTPException(
            422, "Select at least one document or use all indexed documents"
        )
    async with tenant_connection(tenant_id) as conn:
        if request.document_ids:
            count = await conn.fetchval(
                "SELECT count(*) FROM documents WHERE tenant_id=$1::uuid AND id=ANY($2::uuid[]) AND status='indexed'",
                tenant_id,
                request.document_ids,
            )
            if count != len(set(request.document_ids)):
                raise HTTPException(
                    404, "One or more selected documents are unavailable or not indexed"
                )
        history = await conn.fetch(
            """SELECT raw_query,answer FROM query_interactions WHERE tenant_id=$1::uuid
            AND user_id=$2::uuid AND session_id=$3 AND retrieval_scope=$4
            ORDER BY created_at DESC LIMIT 3""",
            tenant_id,
            user_id,
            session_id,
            retrieval_scope,
        )
    await _reserve_query(tenant_id)
    # Bounded owned conversation context supports referential follow-up questions.
    prior = [
        {"question": row["raw_query"][:1000], "answer": (row["answer"] or "")[:2000]}
        for row in reversed(history)
    ]
    retrieval_query = (
        " ".join(turn["question"] for turn in prior[-2:]) + " " + request.query
    ).strip()[-3000:]
    try:
        prepared = await process_query(
            retrieval_query,
            tenant_id,
            user_id,
            bypass_cache=True,
            document_ids=[str(i) for i in request.document_ids]
            if request.document_ids
            else None,
        )
    except Exception as exc:
        logger.warning("Retrieval failed (%s)", type(exc).__name__)
        raise HTTPException(
            503,
            "Retrieval unavailable. Check embedding configuration and document reindexing status.",
        ) from exc
    chunks = prepared.get("chunks", [])
    generation_question = (
        (
            "Conversation for resolving references only (not evidence): "
            + json.dumps(prior)
            + "\nCurrent question: "
            + request.query
        )
        if prior
        else request.query
    )

    async def events():
        answer_parts = []
        if prepared.get("source") == "direct":
            metadata = {
                "interaction_id": str(interaction_id),
                "session_id": str(session_id),
                "source": "direct",
                "route_used": "GREETING_DIRECT",
                "total_latency_ms": round((perf_counter() - started) * 1000),
                "chunks_retrieved": 0,
                "validation": "direct_greeting",
                "retrieval_scope": retrieval_scope,
            }
            await _persist_interaction(
                interaction_id,
                tenant_id,
                user_id,
                session_id,
                request.query,
                "GREETING_DIRECT",
                [],
                prepared["answer"],
                metadata,
            )
            yield _sse(
                {"type": "done", "answer": prepared["answer"], "metadata": metadata}
            )
            return
        try:
            if request.include_context:
                yield _sse({"type": "retrieval", "chunks": chunks})
            async for event in stream_response(
                generation_question, chunks, selected_client, route_used="HYBRID"
            ):
                if event["type"] == "token":
                    answer_parts.append(event["content"])
                if event["type"] == "done":
                    metadata = {
                        **event["metadata"],
                        "interaction_id": str(interaction_id),
                        "session_id": str(session_id),
                        "retrieval_scope": retrieval_scope,
                        "total_latency_ms": round((perf_counter() - started) * 1000),
                    }
                    metadata["ttft_ms"] = metadata["total_latency_ms"]
                    # Persist before exposing the feedback ID to avoid a completion race.
                    await _persist_interaction(
                        interaction_id,
                        tenant_id,
                        user_id,
                        session_id,
                        request.query,
                        "HYBRID",
                        chunks,
                        "".join(answer_parts),
                        metadata,
                    )
                    event = {**event, "metadata": metadata}
                yield _sse(event)
        except Exception as exc:
            logger.warning("Query response failed (%s)", type(exc).__name__)
            yield _sse(
                {
                    "type": "error",
                    "message": "Answer could not be completed and verified. Please retry or choose another configured model.",
                }
            )

    return EventSourceResponse(events())


@router.post("/{interaction_id}/feedback")
async def submit_feedback(
    interaction_id: uuid.UUID,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Set positive or negative feedback on a tenant-owned interaction."""
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        result = await conn.execute(
            """
            UPDATE query_interactions
            SET user_feedback = $1
            WHERE id = $2 AND tenant_id = $3::uuid AND user_id=$4::uuid
            """,
            request.feedback,
            interaction_id,
            str(current_user.tenant_id),
            str(current_user.id),
        )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Interaction not found")
    return {"interaction_id": str(interaction_id), "feedback": request.feedback}
