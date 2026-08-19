"""
Document Ingestion Pipeline Celery Task.

Orchestrates the end-to-end background document ingestion lifecycle:
1. Status transition -> 'processing'
2. Docling Vision / Layout Parsing -> Pages & Bounding Boxes
3. Presidio PII Masking -> Sanitized Content
4. Global Document Contextual Summary Generation
5. Sentence-Aware Semantic Chunking -> Context-Injected Chunks with UUIDs
6. Batch Vector Embedding Generation with Redis Caching
7. Bulk Insertion into PostgreSQL `chunks` table
8. Knowledge Graph Entity & Triple Extraction (Parallel GraphRAG via asyncio.gather)
9. Status transition -> 'indexed' (or 'failed' on fatal errors)
"""

from __future__ import annotations

import os
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, List
import asyncpg

from app.celery_app import celery_app
from app.config import settings
from app.ingestion.parser import parse_document
from app.ingestion.pii import mask_pii
from app.ingestion.contextual import generate_contextual_summary
from app.ingestion.chunker import semantic_chunk
from app.ingestion.embedder import embed_batch
from app.ingestion.graph_extractor import extract_triples

logger = logging.getLogger(__name__)


def _get_raw_db_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


async def _update_document_status(
    doc_id: str,
    status: str,
    total_pages: int = 0,
    error_msg: str = None
) -> None:
    """Helper to update document state and metadata in PostgreSQL."""
    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        if error_msg:
            await conn.execute(
                """
                UPDATE documents 
                SET status = $1, metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{error}', to_jsonb($2::text)), updated_at = NOW()
                WHERE id = $3::uuid
                """,
                status, error_msg, doc_id
            )
        else:
            await conn.execute(
                """
                UPDATE documents 
                SET status = $1, total_pages = GREATEST(total_pages, $2), updated_at = NOW()
                WHERE id = $3::uuid
                """,
                status, total_pages, doc_id
            )
    finally:
        await conn.close()


async def _persist_chunks(
    doc_id: str,
    tenant_id: str,
    chunks: List[Dict[str, Any]]
) -> None:
    """Bulk insert extracted chunks into the PostgreSQL chunks table with vector embeddings and TSVector."""
    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        # Prepare records for executemany
        records = [
            (
                c["id"],
                doc_id,
                tenant_id,
                c["chunk_index"],
                c["content"],
                c.get("contextual_summary", ""),
                c.get("page_number", 1),
                json.dumps(c.get("bounding_box", {})),
                c.get("token_count", 0),
                f"[{','.join(map(str, c['embedding']))}]" if c.get("embedding") else None
            )
            for c in chunks
        ]

        await conn.executemany(
            """
            INSERT INTO chunks (
                id, document_id, tenant_id, chunk_index, content,
                contextual_summary, page_number, bounding_box, token_count,
                embedding, sparse_tsv, created_at
            ) VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4, $5,
                $6, $7, $8::jsonb, $9,
                $10::vector, to_tsvector('english', $5), NOW()
            )
            """,
            records
        )
    finally:
        await conn.close()


async def run_pipeline(document_id: str, tenant_id: str, file_path: str) -> Dict[str, Any]:
    """Async execution wrapper for the ingestion pipeline."""
    logger.info(f"Starting ingestion pipeline for document={document_id}, file={file_path}")

    # Step 1: Update status to 'processing'
    await _update_document_status(document_id, status="processing")

    try:
        # Step 2: Parse document layout and extract pages
        pages = parse_document(file_path)
        if not pages:
            raise ValueError(f"No readable content or pages extracted from {file_path}")

        total_pages = len(pages)

        # Step 3: Mask PII on each page
        masked_pages = []
        full_text_accumulator = []

        for p in pages:
            sanitized_text = mask_pii(p["content"])
            masked_pages.append({
                "page_number": p["page_number"],
                "content": sanitized_text,
                "bounding_boxes": p.get("bounding_boxes", [])
            })
            if sanitized_text.strip():
                full_text_accumulator.append(sanitized_text)

        combined_doc_text = "\n\n".join(full_text_accumulator)

        # Step 4: Generate Global Contextual Summary
        summary = await generate_contextual_summary(combined_doc_text)

        # Step 5: Semantic Chunking per Page with UUIDs
        all_chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 0

        for p in masked_pages:
            if not p["content"].strip():
                continue

            page_chunks = semantic_chunk(
                text=p["content"],
                contextual_summary=summary,
                chunk_size=512,
                overlap=64
            )

            for chunk in page_chunks:
                # Find matching or representative bounding box from page
                matched_bbox = p["bounding_boxes"][0] if p.get("bounding_boxes") else {}

                all_chunks.append({
                    "id": str(uuid.uuid4()),
                    "chunk_index": global_chunk_idx,
                    "content": chunk["content"],
                    "token_count": chunk["token_count"],
                    "contextual_summary": summary,
                    "page_number": p["page_number"],
                    "bounding_box": matched_bbox
                })
                global_chunk_idx += 1

        # Step 6: Batch generate embeddings for all chunks with Redis caching
        if all_chunks:
            chunk_texts = [c["content"] for c in all_chunks]
            redis_client = None
            try:
                import redis.asyncio as aioredis
                redis_client = aioredis.from_url(settings.REDIS_URL)
            except Exception as r_err:
                logger.warning(f"Could not connect to Redis for embedding cache: {r_err}")

            try:
                embeddings = await embed_batch(chunk_texts, redis_client=redis_client)
                for idx, emb in enumerate(embeddings):
                    all_chunks[idx]["embedding"] = emb
            finally:
                if redis_client is not None:
                    try:
                        await redis_client.aclose()
                    except Exception:
                        pass

        # Step 7: Bulk insert chunks into PostgreSQL
        if all_chunks:
            await _persist_chunks(document_id, tenant_id, all_chunks)

        # Step 8: Knowledge Graph Entity & Triple Extraction in Parallel
        if all_chunks:
            logger.info(f"Extracting knowledge graph triples for {len(all_chunks)} chunks (tenant={tenant_id})")
            extraction_tasks = [
                extract_triples(
                    chunk_id=c["id"],
                    chunk_content=c["content"],
                    tenant_id=tenant_id
                )
                for c in all_chunks
            ]
            await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Step 9: Mark document as 'indexed'
        await _update_document_status(document_id, status="indexed", total_pages=total_pages)

        logger.info(f"Ingestion successful for document={document_id}. Total chunks: {len(all_chunks)}")
        return {
            "document_id": document_id,
            "status": "indexed",
            "total_pages": total_pages,
            "total_chunks": len(all_chunks)
        }

    except Exception as exc:
        logger.error(f"Ingestion failed for document {document_id}: {exc}", exc_info=True)
        try:
            await _update_document_status(document_id, status="failed", error_msg=str(exc))
        except Exception as db_err:
            logger.error(f"Failed to record failure status in DB: {db_err}")
        raise exc


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_document(self, document_id: str, tenant_id: str, file_path: str):
    """
    Celery background worker entrypoint for document ingestion.
    """
    try:
        return asyncio.run(run_pipeline(document_id, tenant_id, file_path))
    except Exception as exc:
        logger.warning(f"Retrying document processing task {self.request.id} due to: {exc}")
        # Retry with exponential backoff up to max_retries
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
