"""
Vector Similarity Search Module (pgvector HNSW).

Executes cosine distance approximate nearest neighbor (ANN) search
over multi-tenant document chunks with HNSW index tuning.
"""

import json
import logging
from typing import List, Dict, Any, Optional
import asyncpg

from app.config import settings
from app.db.tenant import tenant_connection

logger = logging.getLogger(__name__)


def _get_raw_db_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def _format_vector(vector: List[float]) -> str:
    """Format float list into pgvector string representation."""
    return f"[{','.join(str(x) for x in vector)}]"


async def vector_search(
    embedding: List[float],
    tenant_id: str,
    top_k: int = 20,
    db_conn: Optional[Any] = None,
    ef_search: Optional[int] = None,
    document_ids: Optional[list[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Query PostgreSQL pgvector HNSW index using cosine similarity distance operator (<=>).

    - Configures `hnsw.ef_search` for search recall/latency balance.
    - Enforces tenant isolation filter (`tenant_id = $2::uuid`).
    - Returns top_k chunks sorted by similarity score in descending order.
    """
    if not embedding:
        return []

    target_ef = ef_search or settings.HNSW_EF_SEARCH
    vector_str = _format_vector(embedding)
    results: List[Dict[str, Any]] = []

    async def _execute_search(conn: Any) -> List[Dict[str, Any]]:
        # Tune HNSW runtime probe depth for the transaction/connection
        await conn.execute(f"SET hnsw.ef_search = {target_ef};")

        rows = await conn.fetch(
            """
            SELECT c.id, c.document_id, c.content, c.contextual_summary, c.page_number,
                   c.bounding_box, d.filename AS source_filename,
                   1 - (c.embedding <=> $1::vector) AS similarity_score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.tenant_id = $2::uuid AND d.tenant_id=$2::uuid AND d.status='indexed' AND c.embedding IS NOT NULL
              AND ($4::uuid[] IS NULL OR d.id=ANY($4::uuid[]))
            ORDER BY c.embedding <=> $1::vector ASC
            LIMIT $3;
            """,
            vector_str,
            tenant_id,
            top_k,
            document_ids,
        )

        formatted_rows = []
        for r in rows:
            bbox = r["bounding_box"]
            if isinstance(bbox, str):
                try:
                    bbox = json.loads(bbox)
                except Exception:
                    bbox = {}

            formatted_rows.append(
                {
                    "id": str(r["id"]),
                    "document_id": str(r["document_id"]),
                    "content": r["content"],
                    "contextual_summary": r["contextual_summary"] or "",
                    "page_number": r["page_number"] or 1,
                    "bounding_box": bbox or {},
                    "source_filename": r.get("source_filename", ""),
                    "similarity_score": round(float(r["similarity_score"]), 5)
                    if r["similarity_score"] is not None
                    else 0.0,
                }
            )
        return formatted_rows

    if db_conn is not None:
        return await _execute_search(db_conn)

    # Standalone connection
    async with tenant_connection(tenant_id) as conn:
        results = await _execute_search(conn)

    return results
