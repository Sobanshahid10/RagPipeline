"""
Document Management API Router.

Provides endpoints for document upload (with SHA-256 deduplication and async task queuing)
and ingestion status polling.
"""

import os
import hashlib
import uuid
import logging
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Request
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


def _extract_tenant_from_request(request: Optional[Request]) -> Optional[str]:
    """Extract tenant_id from the Authorization Bearer JWT if present."""
    if not request:
        return None
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(parts[1])
            return payload.get("tenant_id")
        except Exception:
            return None
    return None


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
    request: Request = None,
    file: UploadFile = File(...),
    tenant_id: Optional[str] = Form(None)
):
    """
    Upload a document (PDF, DOCX, TXT) for asynchronous layout-aware vision parsing and indexing.

    - Computes SHA-256 digest for deduplication.
    - Resolves tenant ID via Form parameter, Authorization JWT token, or system default tenant.
    - Persists file to local volume storage.
    - Creates database record in 'pending' status.
    - Dispatches asynchronous Celery task.
    - Returns immediately with 202 Accepted status.
    """
    # If explicit tenant_id provided, validate UUID format
    if tenant_id:
        try:
            uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tenant_id format: {tenant_id}"
            )

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
        # Resolve tenant ID: Form -> JWT Token -> First DB Tenant -> Auto-created Default
        resolved_tenant_id = tenant_id or _extract_tenant_from_request(request)
        t_row = None
        if resolved_tenant_id:
            try:
                uuid.UUID(str(resolved_tenant_id))
                t_row = await conn.fetchrow("SELECT id FROM tenants WHERE id = $1::uuid", str(resolved_tenant_id))
            except Exception:
                t_row = None

        if not t_row:
            # Fallback to the first existing tenant in the database
            t_row = await conn.fetchrow("SELECT id FROM tenants ORDER BY created_at ASC LIMIT 1")
            if not t_row:
                # Create a default workspace tenant if database has none
                default_id = str(uuid.uuid4())
                await conn.execute(
                    "INSERT INTO tenants (id, name, slug, created_at, updated_at) VALUES ($1::uuid, $2, $3, NOW(), NOW())",
                    default_id, "Default Workspace", "default-workspace"
                )
                t_id = default_id
            else:
                t_id = str(t_row["id"])
        else:
            t_id = str(t_row["id"])

        # Check for existing document with same SHA-256 hash
        existing = await conn.fetchrow(
            "SELECT id, filename, status FROM documents WHERE doc_hash = $1",
            doc_hash
        )
        if existing:
            if existing["status"] == "failed":
                # Clear out previously failed document attempt so it can be reprocessed cleanly
                await conn.execute("DELETE FROM documents WHERE id = $1", existing["id"])
            else:
                return DocumentUploadResponse(
                    document_id=str(existing["id"]),
                    filename=existing["filename"],
                    status=existing["status"],
                    doc_hash=doc_hash,
                    message=f"Document already exists and is {existing['status']}."
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


@router.get("", response_model=List[DocumentStatusResponse])
async def list_documents(
    request: Request = None,
    tenant_id: Optional[str] = None
):
    """
    List all uploaded documents with status and chunk counts.
    """
    target_tenant_id = tenant_id
    if not target_tenant_id and request:
        target_tenant_id = _extract_tenant_from_request(request)

    if target_tenant_id:
        try:
            uuid.UUID(target_tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tenant_id format: {target_tenant_id}"
            )

    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        query = """
            SELECT d.id, d.filename, d.file_type, d.status, d.total_pages, d.created_at, d.updated_at,
                   COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
        """
        params = []
        if target_tenant_id:
            query += " WHERE d.tenant_id = $1::uuid"
            params.append(target_tenant_id)
        query += " GROUP BY d.id ORDER BY d.created_at DESC"

        docs = await conn.fetch(query, *params)
        return [
            DocumentStatusResponse(
                document_id=str(doc["id"]),
                filename=doc["filename"],
                file_type=doc["file_type"],
                status=doc["status"],
                total_pages=doc["total_pages"] or 0,
                chunk_count=doc["chunk_count"] or 0,
                created_at=doc["created_at"].isoformat(),
                updated_at=doc["updated_at"].isoformat()
            )
            for doc in docs
        ]

    finally:
        await conn.close()


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str):
    """
    Query the processing status and chunk statistics for an uploaded document.
    """
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

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


@router.get("/{document_id}/file")
async def get_document_file(document_id: str):
    """
    Serve the raw document file (e.g. PDF) for client-side rendering in PDFViewer.
    """
    from fastapi.responses import FileResponse

    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        doc = await conn.fetchrow(
            "SELECT storage_uri, filename, file_type FROM documents WHERE id = $1::uuid",
            document_id
        )
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found."
            )

        file_path = doc["storage_uri"]
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document file not found on disk."
            )

        media_type = "application/pdf" if doc["file_type"] == "pdf" else "application/octet-stream"
        return FileResponse(
            file_path,
            media_type=media_type,
            filename=doc["filename"]
        )
    finally:
        await conn.close()


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    request: Request = None
):
    """
    Permanently delete a document, its file on disk, and cascading chunks & entity triples.
    """
    try:
        uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found."
        )

    target_tenant_id = None
    if request:
        target_tenant_id = _extract_tenant_from_request(request)

    conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
    try:
        if target_tenant_id:
            doc = await conn.fetchrow(
                "SELECT id, filename, storage_uri FROM documents WHERE id = $1::uuid AND tenant_id = $2::uuid",
                document_id, target_tenant_id
            )
        else:
            doc = await conn.fetchrow(
                "SELECT id, filename, storage_uri FROM documents WHERE id = $1::uuid",
                document_id
            )

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found."
            )

        # Remove file from disk if present
        file_path = doc["storage_uri"]
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError as err:
                logger.warning(f"Could not remove disk file {file_path}: {err}")

        # Delete database row (chunks and entity_triples CASCADE)
        await conn.execute("DELETE FROM documents WHERE id = $1::uuid", document_id)

        return {
            "status": "deleted",
            "document_id": document_id,
            "filename": doc["filename"],
            "message": f"Document '{doc['filename']}' successfully removed."
        }
    finally:
        await conn.close()


