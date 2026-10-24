"""Bounded, retry-safe document ingestion with explicit stage state."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from app.celery_app import celery_app
from app.config import settings
from app.db.tenant import tenant_connection
from app.ingestion.chunker import semantic_chunk
from app.ingestion.contextual import generate_contextual_summary
from app.ingestion.embedder import embed_batch, embedding_identity
from app.ingestion.graph_extractor import extract_triples
from app.ingestion.parser import parse_document
from app.ingestion.pii import mask_pii

logger = logging.getLogger(__name__)


async def _extract_graph_batch(chunks, tenant_id):
    # Bound the whole provider operation, including a stream that keeps trickling
    # tokens and never triggers its HTTP read timeout.
    return await asyncio.gather(
        *(
            asyncio.wait_for(
                extract_triples(chunk["id"], chunk["content"], tenant_id),
                timeout=settings.GRAPH_EXTRACTION_TIMEOUT_SECONDS,
            )
            for chunk in chunks
        ),
        return_exceptions=True,
    )


async def _update_document_status(
    doc_id, status, total_pages=0, error_msg=None, *, tenant_id, **metadata
):
    if error_msg:
        metadata["error"] = error_msg
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            """UPDATE documents SET status=$1, total_pages=GREATEST(total_pages,$2),
            metadata=(metadata - 'error') || $3::jsonb, updated_at=NOW()
            WHERE id=$4::uuid AND tenant_id=$5::uuid""",
            status,
            total_pages,
            json.dumps(metadata),
            doc_id,
            tenant_id,
        )


async def _persist_chunks(doc_id, tenant_id, chunks):
    # A failed attempt's chunks and graph are replaced atomically on retry.
    async with tenant_connection(tenant_id) as conn:
        await conn.execute(
            "DELETE FROM chunks WHERE document_id=$1::uuid AND tenant_id=$2::uuid",
            doc_id,
            tenant_id,
        )
        await conn.executemany(
            """INSERT INTO chunks(id,document_id,tenant_id,chunk_index,content,
            contextual_summary,page_number,bounding_box,token_count,embedding,sparse_tsv)
            VALUES($1::uuid,$2::uuid,$3::uuid,$4,$5,$6,$7,$8::jsonb,$9,$10::vector,to_tsvector('english',$5))""",
            [
                (
                    c["id"],
                    doc_id,
                    tenant_id,
                    c["chunk_index"],
                    c["content"].replace("\x00", ""),
                    c["contextual_summary"],
                    c["page_number"],
                    json.dumps(c["bounding_box"]),
                    c["token_count"],
                    str(c["embedding"]),
                )
                for c in chunks
            ],
        )


async def run_pipeline(
    document_id: str, tenant_id: str, file_path: str, job_id: str | None = None
) -> dict[str, Any]:
    # Shared with retry/delete; duplicate Celery delivery cannot run concurrently.
    async with tenant_connection(tenant_id) as lock:
        acquired = await lock.fetchval(
            "SELECT pg_try_advisory_xact_lock(hashtextextended($1,0))", document_id
        )
        if not acquired:
            return {"document_id": document_id, "status": "already_running"}
        row = await lock.fetchrow(
            "SELECT status,storage_uri,metadata->>'job_id' AS job_id FROM documents WHERE id=$1::uuid AND tenant_id=$2::uuid",
            document_id,
            tenant_id,
        )
        if not row or row["status"] not in ("pending", "failed", "processing"):
            return {"document_id": document_id, "status": "skipped"}
        if row["job_id"] != job_id:
            return {"document_id": document_id, "status": "superseded"}
        from pathlib import Path

        path = Path(file_path).resolve()
        if path != Path(row["storage_uri"]).resolve() or not path.is_relative_to(
            Path(settings.UPLOAD_DIR).resolve()
        ):
            raise RuntimeError("Invalid document storage path")
        try:
            identity = embedding_identity()
            await _update_document_status(
                document_id, "processing", tenant_id=tenant_id, stage="parsing"
            )
            pages = await asyncio.to_thread(parse_document, str(path))
            if not pages or len(pages) > settings.MAX_DOCUMENT_PAGES:
                raise ValueError("No readable pages or page limit exceeded")
            if sum(len(p["content"]) for p in pages) > settings.MAX_DOCUMENT_CHARS:
                raise ValueError("Extracted text limit exceeded")
            await _update_document_status(
                document_id,
                "processing",
                tenant_id=tenant_id,
                stage="privacy",
                total_pages=len(pages),
            )
            masked_pages = []
            for page in pages:
                masked_pages.append(
                    {
                        **page,
                        "content": await asyncio.to_thread(mask_pii, page["content"]),
                    }
                )
            text = "\n\n".join(p["content"] for p in masked_pages)
            if not text.strip():
                raise ValueError("Document has no usable text after privacy processing")
            await _update_document_status(
                document_id, "processing", tenant_id=tenant_id, stage="summarizing"
            )
            summary = await generate_contextual_summary(text)
            await _update_document_status(
                document_id, "processing", tenant_id=tenant_id, stage="chunking"
            )
            chunks = []
            for page in masked_pages:
                for chunk in semantic_chunk(
                    page["content"],
                    contextual_summary=summary,
                    chunk_size=512,
                    overlap=64,
                ):
                    if not chunk["content"].strip():
                        continue
                    # Without reliable offsets, show page-level provenance; never invent a region.
                    chunks.append(
                        {
                            "id": str(uuid.uuid4()),
                            "chunk_index": len(chunks),
                            "content": chunk["content"],
                            "token_count": chunk["token_count"],
                            "contextual_summary": summary,
                            "page_number": page["page_number"],
                            "bounding_box": {},
                        }
                    )
                    if len(chunks) > settings.MAX_DOCUMENT_CHUNKS:
                        raise ValueError("Document exceeds chunk limit")
            if not chunks:
                raise ValueError("Document has no indexable chunks")
            await _update_document_status(
                document_id, "processing", tenant_id=tenant_id, stage="embedding"
            )
            vectors = await embed_batch([c["content"] for c in chunks])
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding count mismatch")
            for chunk, vector in zip(chunks, vectors):
                chunk["embedding"] = vector
            await _update_document_status(
                document_id, "processing", tenant_id=tenant_id, stage="indexing"
            )
            await _persist_chunks(document_id, tenant_id, chunks)
            await _update_document_status(
                document_id,
                "indexed",
                tenant_id=tenant_id,
                stage="graph",
                graph_status="processing",
                embedding_identity=identity,
                pii_mode="presidio" if settings.PII_REQUIRED else "best_effort",
            )
            failures = 0
            graph_chunks = chunks[: settings.MAX_GRAPH_CHUNKS]
            for offset in range(0, len(graph_chunks), 4):
                results = await _extract_graph_batch(
                    graph_chunks[offset : offset + 4], tenant_id
                )
                for result in results:
                    if isinstance(result, BaseException):
                        failures += 1
                        logger.warning(
                            "Graph extraction failed for document %s (%s)",
                            document_id,
                            type(result).__name__,
                        )
            await _update_document_status(
                document_id,
                "indexed",
                total_pages=len(pages),
                tenant_id=tenant_id,
                stage="complete",
                embedding_identity=identity,
                pii_mode="presidio" if settings.PII_REQUIRED else "best_effort",
                graph_status="degraded"
                if failures
                else "limited"
                if len(graph_chunks) < len(chunks)
                else "complete",
            )
            return {
                "document_id": document_id,
                "status": "indexed",
                "total_pages": len(pages),
                "total_chunks": len(chunks),
            }
        except Exception as exc:
            logger.warning(
                "Ingestion failed for document %s (%s)", document_id, type(exc).__name__
            )
            await _update_document_status(
                document_id,
                "failed",
                tenant_id=tenant_id,
                stage="failed",
                error_msg="Processing failed. Check provider availability, privacy model installation, and document limits; then retry.",
            )
            raise


@celery_app.task(bind=True, max_retries=3, soft_time_limit=840, time_limit=900)
def process_document(self, document_id, tenant_id, file_path, job_id=None):
    try:
        return asyncio.run(run_pipeline(document_id, tenant_id, file_path, job_id))
    except Exception as exc:
        raise self.retry(
            exc=RuntimeError("Document processing failed"),
            countdown=2**self.request.retries * 5,
        ) from exc
