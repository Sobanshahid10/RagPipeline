"""
Document Management API Router.

Provides endpoints for document upload (with SHA-256 deduplication and async task queuing)
and ingestion status polling.
"""

import os
import hashlib
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel
import asyncpg

from app.config import settings
from app.ingestion.pipeline import process_document

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])

UPLOAD_DIR = os.path.join(os.getcwd(), "storage", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_raw_db_url(url: str) -> str:
    """Convert asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    status: str
    doc_hash: str
    message: str


class DocumentStatusResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: str
    total_pages: int
    chunk_count: int
    created_at: str
    updated_at: str


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    tenant_id: Optional[str] = Form(None)
):
    """
    Upload a document (PDF, DOCX, TXT) for asynchronous layout-aware vision parsing and indexing.

    - Computes SHA-256 digest for deduplication.
    - Persists file to local volume storage.
    - Creates database record in 'pending' status.
    - Dispatches asynchronous Celery task.
    - Returns immediately with 202 Accepted status.
    """
    # Use default dummy tenant ID if none provided
    t_id = tenant_id or "00000000-0000-0000-0000-000000000001"

    # Read content to compute SHA-256 hash
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    doc_hash = hashlib.sha256(content_bytes).hexdigest()
    file_ext = os.path.splitext(file.filename)[1].lower().lstrip(".") or "txt"

    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        # Check for existing document with same SHA-256 hash
        existing = await conn.fetchrow(
            "SELECT id, filename, status FROM documents WHERE doc_hash = $1",
            doc_hash
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Document with identical content already exists (ID: {existing['id']}, status: {existing['status']})."
            )

        doc_id = str(uuid.uuid4())
        saved_filename = f"{doc_id}_{file.filename}"
        saved_file_path = os.path.join(UPLOAD_DIR, saved_filename)

        # Save to disk
        with open(saved_file_path, "wb") as f:
            f.write(content_bytes)

        # Insert metadata record into PostgreSQL
        await conn.execute(
            """
            INSERT INTO documents (
                id, tenant_id, filename, file_type, doc_hash, storage_uri, status, created_at, updated_at
            ) VALUES (
                $1::uuid, $2::uuid, $3, $4, $5, $6, 'pending', NOW(), NOW()
            )
            """,
            doc_id, t_id, file.filename, file_ext, doc_hash, saved_file_path
        )

        # Dispatch Celery background task
        try:
            process_document.delay(doc_id, t_id, saved_file_path)
        except Exception as queue_err:
            logger.warning(f"Failed to enqueue Celery task: {queue_err}. Task will need manual dispatch.")

        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            status="processing",
            doc_hash=doc_hash,
            message="Document accepted and queued for background ingestion."
        )

    finally:
        await conn.close()


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str):
    """
    Query the processing status and chunk statistics for an uploaded document.
    """
    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        doc = await conn.fetchrow(
            """
            SELECT d.id, d.filename, d.file_type, d.status, d.total_pages, d.created_at, d.updated_at,
                   COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
            WHERE d.id = $1::uuid
            GROUP BY d.id
            """,
            document_id
        )

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found."
            )

        return DocumentStatusResponse(
            document_id=str(doc["id"]),
            filename=doc["filename"],
            file_type=doc["file_type"],
            status=doc["status"],
            total_pages=doc["total_pages"] or 0,
            chunk_count=doc["chunk_count"] or 0,
            created_at=doc["created_at"].isoformat(),
            updated_at=doc["updated_at"].isoformat()
        )

    finally:
        await conn.close()
