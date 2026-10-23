"""Admin metrics and system health API.

Provides:
  GET /api/v1/admin/stats          — aggregated query metrics (last 24 h)
  GET /api/v1/admin/recent_queries — last N interactions with metadata
  GET /api/v1/admin/health         — Postgres / Redis / Celery liveness
"""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends

from app.config import settings
from app.core.dependencies import get_current_user, require_admin
from app.db.tenant import tenant_connection
import asyncio
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{settings.API_V1_STR}/admin", tags=["Admin"])


# ── helpers ──────────────────────────────────────────────────────────────────


def _raw_db_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _db_conn() -> asyncpg.Connection:
    return await asyncpg.connect(_raw_db_url(settings.DATABASE_URL))


# ── endpoints ─────────────────────────────────────────────────────────────────


@router.get("/stats")
async def get_admin_stats(
    current_user: User = Depends(require_admin),
) -> dict[str, Any]:
    """Return aggregated query metrics for the last 24 h for the current tenant."""
    tenant_id = str(current_user.tenant_id)
    async with tenant_connection(tenant_id) as conn:
        row = await conn.fetchrow(
            """
            SELECT
                COUNT(*)                                                          AS total_queries_24h,
                COALESCE(AVG(ttft_ms)::INT, 0)                                    AS avg_ttft_ms,
                COALESCE(
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ttft_ms)::INT, 0
                )                                                                  AS p95_ttft_ms,
                COALESCE(
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY ttft_ms)::INT, 0
                )                                                                  AS p50_ttft_ms,
                COALESCE(
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ttft_ms)::INT, 0
                )                                                                  AS p99_ttft_ms,
                COALESCE(
                    COUNT(CASE WHEN route_used = 'cache' OR route_used = 'CACHE' THEN 1 END)::FLOAT
                    / NULLIF(COUNT(*), 0),
                    0
                )                                                                  AS cache_hit_rate,
                COALESCE(SUM(prompt_tokens + completion_tokens), 0)               AS total_tokens_today,
                COALESCE(
                    COUNT(CASE WHEN user_feedback = 1 THEN 1 END)::FLOAT
                    / NULLIF(COUNT(*), 0),
                    0
                )                                                                  AS thumbs_up_rate,
                COUNT(CASE WHEN route_used = 'MULTI_HOP_GRAPH' THEN 1 END)        AS graph_route_count,
                COUNT(CASE WHEN route_used IN ('FACTUAL_VECTOR','HYBRID') THEN 1 END)         AS vector_route_count,
                COUNT(CASE WHEN route_used = 'ANALYTICAL_SQL' THEN 1 END)         AS sql_route_count,
                COUNT(CASE WHEN route_used = 'GREETING_DIRECT' THEN 1 END)        AS direct_route_count
            FROM query_interactions
            WHERE tenant_id = $1::uuid
              AND created_at >= NOW() - INTERVAL '24 hours'
            """,
            tenant_id,
        )

    return {
        "total_queries_24h": int(row["total_queries_24h"] or 0),
        "avg_ttft_ms": int(row["avg_ttft_ms"] or 0),
        "p50_ttft_ms": int(row["p50_ttft_ms"] or 0),
        "p95_ttft_ms": int(row["p95_ttft_ms"] or 0),
        "p99_ttft_ms": int(row["p99_ttft_ms"] or 0),
        "cache_hit_rate": round(float(row["cache_hit_rate"] or 0), 4),
        "total_tokens_today": int(row["total_tokens_today"] or 0),
        "thumbs_up_rate": round(float(row["thumbs_up_rate"] or 0), 4),
        "route_breakdown": {
            "MULTI_HOP_GRAPH": int(row["graph_route_count"] or 0),
            "FACTUAL_VECTOR": int(row["vector_route_count"] or 0),
            "ANALYTICAL_SQL": int(row["sql_route_count"] or 0),
            "GREETING_DIRECT": int(row["direct_route_count"] or 0),
        },
    }


@router.get("/recent_queries")
async def get_recent_queries(
    limit: int = 20,
    current_user: User = Depends(require_admin),
) -> list[dict[str, Any]]:
    """Return the most recent query interactions for the current tenant."""
    tenant_id = str(current_user.tenant_id)
    async with tenant_connection(tenant_id) as conn:
        rows = await conn.fetch(
            """
            SELECT
                id,
                raw_query,
                route_used,
                ttft_ms,
                total_latency_ms,
                prompt_tokens,
                completion_tokens,
                user_feedback,
                created_at
            FROM query_interactions
            WHERE tenant_id = $1::uuid
            ORDER BY created_at DESC
            LIMIT $2
            """,
            tenant_id,
            max(1, min(limit, 100)),
        )

    return [
        {
            "id": str(r["id"]),
            "raw_query": r["raw_query"],
            "route_used": r["route_used"],
            "ttft_ms": r["ttft_ms"],
            "total_latency_ms": r["total_latency_ms"],
            "prompt_tokens": r["prompt_tokens"],
            "completion_tokens": r["completion_tokens"],
            "user_feedback": r["user_feedback"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


@router.get("/health")
async def system_health(current_user: User = Depends(require_admin)) -> dict[str, Any]:
    """Check Postgres, Redis, and Celery workers for workspace administrators."""
    results: dict[str, Any] = {}

    # ── Postgres ──────────────────────────────────────────────────────────
    try:
        conn = await _db_conn()
        await conn.fetchval("SELECT 1")
        await conn.close()
        results["postgres"] = {"status": "healthy"}
    except Exception as exc:
        logger.warning("Postgres health check failed: %s", exc)
        results["postgres"] = {"status": "unhealthy", "error": "Service unavailable"}

    # ── Redis ─────────────────────────────────────────────────────────────
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
        results["redis"] = {"status": "healthy"}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        results["redis"] = {"status": "unhealthy", "error": "Service unavailable"}

    # ── Celery (broker reachability) ──────────────────────────────────────
    try:
        from app.celery_app import celery_app

        inspect = celery_app.control.inspect(timeout=2.0)
        stats = await asyncio.to_thread(inspect.stats)  # type: ignore[union-attr]
        worker_count = len(stats) if stats else 0
        results["celery"] = {
            "status": "healthy" if worker_count > 0 else "no_workers",
            "active_workers": worker_count,
        }
    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        results["celery"] = {"status": "unhealthy", "error": "Service unavailable"}

    overall = all(v.get("status") == "healthy" for v in results.values())
    return {"overall": "healthy" if overall else "degraded", "services": results}


@router.get("/document_audit")
async def document_audit(current_user: User = Depends(require_admin)):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        rows = await conn.fetch(
            "SELECT id,user_id,document_id,action,created_at FROM document_audit_events WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 100",
            current_user.tenant_id,
        )
    return [dict(row) for row in rows]
