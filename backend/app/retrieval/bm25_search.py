"""
BM25 Full-Text TSVector Search Module.

Executes keyword search using PostgreSQL Full-Text Search (tsvector, tsquery, and ts_rank_cd)
with tenant isolation and ranking.
"""

import json
import logging
from typing import List, Dict, Any, Optional
import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)


def _get_raw_db_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


async def bm25_search(
    query: str,
    tenant_id: str,
    top_k: int = 20,
    db_conn: Optional[Any] = None
) -> List[Dict[str, Any]]:
    """
    Execute full-text sparse query against PostgreSQL `sparse_tsv` column using `ts_rank_cd`.

    - Converts natural language query using `plainto_tsquery('english', $1)`.
    - Matches against GIN-indexed `sparse_tsv` TSVECTOR.
    - Enforces tenant isolation filter (`tenant_id = $2::uuid`).
    - Returns top_k chunks sorted by BM25 rank score descending.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    results: List[Dict[str, Any]] = []

    async def _execute_search(conn: Any) -> List[Dict[str, Any]]:
        rows = await conn.fetch(
            """
            SELECT c.id, c.document_id, c.content, c.contextual_summary, c.page_number,
                   c.bounding_box, d.filename AS source_filename,
                   ts_rank_cd(c.sparse_tsv, query) AS bm25_score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id,
                 plainto_tsquery('english', $1) AS query
            WHERE c.sparse_tsv @@ query AND c.tenant_id = $2::uuid
            ORDER BY bm25_score DESC
            LIMIT $3;
            """,
            cleaned_query,
            tenant_id,
            top_k
        )

        formatted_rows = []
        for r in rows:
            bbox = r["bounding_box"]
            if isinstance(bbox, str):
                try:
                    bbox = json.loads(bbox)
                except Exception:
                    bbox = {}

            formatted_rows.append({
                "id": str(r["id"]),
                "document_id": str(r["document_id"]),
                "content": r["content"],
                "contextual_summary": r["contextual_summary"] or "",
                "page_number": r["page_number"] or 1,
                "bounding_box": bbox or {},
                "source_filename": r.get("source_filename", ""),
                "bm25_score": round(float(r["bm25_score"]), 5) if r["bm25_score"] is not None else 0.0
            })
        return formatted_rows

    if db_conn is not None:
        return await _execute_search(db_conn)

    # Standalone connection
    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        results = await _execute_search(conn)
    finally:
        await conn.close()

    return results
