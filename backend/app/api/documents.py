"""Authenticated, tenant-scoped document lifecycle."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.core.dependencies import get_current_user, require_writer
from app.db.tenant import tenant_connection
from app.ingestion.pipeline import process_document
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix=f"{settings.API_V1_STR}/documents", tags=["Documents"])
UPLOAD_DIR = Path(settings.UPLOAD_DIR).resolve()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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
    stage: str | None = None
    error: str | None = None
    graph_status: str | None = None
    stalled: bool = False


SELECT_DOCUMENTS = """
SELECT d.*, (SELECT count(*) FROM chunks c WHERE c.document_id=d.id AND c.tenant_id=d.tenant_id) AS chunk_count,
       (d.status IN ('pending','processing') AND d.updated_at < NOW() - INTERVAL '20 minutes') AS stalled
FROM documents d
"""


def _status(row):
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    return DocumentStatusResponse(
        document_id=str(row["id"]),
        filename=row["filename"],
        file_type=row["file_type"],
        status=row["status"],
        total_pages=row["total_pages"] or 0,
        chunk_count=row["chunk_count"] or 0,
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
        stage=metadata.get("stage"),
        error=metadata.get("error"),
        graph_status=metadata.get("graph_status"),
        stalled=row["stalled"],
    )


def _storage_path(storage_uri: str) -> Path:
    path = Path(storage_uri).resolve()
    if not path.is_relative_to(UPLOAD_DIR):
        raise HTTPException(404, "Document file unavailable")
    return path


async def _audit(conn, user, document_id, action):
    await conn.execute(
        "INSERT INTO document_audit_events(tenant_id,user_id,document_id,action) VALUES($1,$2,$3,$4)",
        user.tenant_id,
        user.id,
        document_id,
        action,
    )


async def _dispatch(document_id: str, tenant_id: str, path: str, job_id: str):
    try:
        await asyncio.to_thread(
            process_document.delay, document_id, tenant_id, path, job_id
        )
    except Exception:
        logger.warning("Document queue dispatch failed for %s", document_id)
        async with tenant_connection(tenant_id) as conn:
            await conn.execute(
                """UPDATE documents SET status='failed', updated_at=NOW(),
                metadata=metadata || '{"stage":"dispatch","error":"Queue unavailable; retry this document."}'::jsonb
                WHERE id=$1 AND tenant_id=$2::uuid AND status='pending'
                AND metadata->>'job_id'=$3""",
                uuid.UUID(document_id),
                tenant_id,
                job_id,
            )
        raise HTTPException(
            503,
            "Upload saved, but the worker queue is unavailable. Retry from Documents.",
        )


def _validate_content(destination: Path, extension: str):
    if extension == "pdf":
        with destination.open("rb") as source:
            if not source.read(1024).lstrip().startswith(b"%PDF-"):
                raise HTTPException(415, "Invalid PDF content")
        from pypdf import PdfReader

        reader = PdfReader(destination)
        if reader.is_encrypted or len(reader.pages) > settings.MAX_DOCUMENT_PAGES:
            raise HTTPException(422, "PDF is encrypted or exceeds the page limit")
    elif extension == "docx":
        with zipfile.ZipFile(destination) as archive:
            entries = archive.infolist()
            if (
                len(entries) > 2000
                or sum(e.file_size for e in entries) > settings.MAX_EXPANDED_BYTES
                or any(e.flag_bits & 1 for e in entries)
                or "word/document.xml" not in archive.namelist()
            ):
                raise HTTPException(422, "DOCX exceeds expansion limits or is invalid")
    else:
        data = destination.read_bytes()
        if b"\x00" in data:
            raise HTTPException(415, "TXT must contain UTF-8 text")
        data.decode("utf-8")


async def _validate_upload(file: UploadFile, destination: Path, extension: str):
    size = 0
    try:
        with destination.open("xb") as output:
            while data := await file.read(1024 * 1024):
                size += len(data)
                if size > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "Document exceeds the upload size limit")
                output.write(data)
        if not size:
            raise HTTPException(400, "Uploaded file is empty")
        await asyncio.to_thread(_validate_content, destination, extension)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(415, "Invalid or unsupported document content")
    return size


@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    file: UploadFile = File(...), current_user: User = Depends(require_writer)
):
    tenant_id = str(current_user.tenant_id)
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1][:240]
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in {"pdf", "docx", "txt"}:
        raise HTTPException(415, "Supported document types: PDF, DOCX, TXT")
    doc_id = uuid.uuid4()
    job_id = str(uuid.uuid4())
    destination = UPLOAD_DIR / f"{doc_id}.{extension}"
    retained = False
    try:
        size = await _validate_upload(file, destination, extension)

        def hash_file():
            with destination.open("rb") as source:
                return hashlib.file_digest(source, "sha256").hexdigest()

        digest = await asyncio.to_thread(hash_file)
        async with tenant_connection(tenant_id) as conn:
            # Serialize quota and duplicate checks for concurrent workspace uploads.
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended($1, 0))", tenant_id
            )
            existing = await conn.fetchrow(
                "SELECT * FROM documents WHERE tenant_id=$1::uuid AND doc_hash=$2",
                tenant_id,
                digest,
            )
            if existing:
                return DocumentUploadResponse(
                    document_id=str(existing["id"]),
                    filename=existing["filename"],
                    status=existing["status"],
                    doc_hash=digest,
                    message="Document already exists; retry it if processing failed.",
                )
            usage = await conn.fetchval(
                "SELECT COALESCE(SUM((metadata->>'size_bytes')::bigint),0) FROM documents WHERE tenant_id=$1::uuid",
                tenant_id,
            )
            if usage + size > settings.MAX_TENANT_STORAGE_BYTES:
                raise HTTPException(413, "Workspace storage limit reached")
            await conn.execute(
                """INSERT INTO documents(id,tenant_id,filename,file_type,doc_hash,storage_uri,status,metadata)
                VALUES($1,$2::uuid,$3,$4,$5,$6,'pending',$7::jsonb)""",
                doc_id,
                tenant_id,
                filename,
                extension,
                digest,
                str(destination),
                json.dumps({"stage": "queued", "size_bytes": size, "job_id": job_id}),
            )
            await _audit(conn, current_user, doc_id, "upload")
            # Preserve the original if cancellation makes the commit outcome uncertain.
            # An orphan is recoverable; a committed row with a deleted original is not.
            retained = True
        await _dispatch(str(doc_id), tenant_id, str(destination), job_id)
        return DocumentUploadResponse(
            document_id=str(doc_id),
            filename=filename,
            status="pending",
            doc_hash=digest,
            message="Upload received and queued; indexing is not complete.",
        )
    finally:
        await file.close()
        if not retained:
            destination.unlink(missing_ok=True)


@router.get("", response_model=list[DocumentStatusResponse])
async def list_documents(current_user: User = Depends(get_current_user)):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        rows = await conn.fetch(
            SELECT_DOCUMENTS + " WHERE d.tenant_id=$1 ORDER BY d.created_at DESC",
            current_user.tenant_id,
        )
    return [_status(row) for row in rows]


@router.get("/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID, current_user: User = Depends(get_current_user)
):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        row = await conn.fetchrow(
            SELECT_DOCUMENTS + " WHERE d.id=$1 AND d.tenant_id=$2",
            document_id,
            current_user.tenant_id,
        )
    if not row:
        raise HTTPException(404, "Document not found")
    return _status(row)


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: uuid.UUID, current_user: User = Depends(get_current_user)
):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        row = await conn.fetchrow(
            "SELECT * FROM documents WHERE id=$1 AND tenant_id=$2",
            document_id,
            current_user.tenant_id,
        )
    if not row:
        raise HTTPException(404, "Document not found")
    path = _storage_path(row["storage_uri"])
    if not path.is_file():
        raise HTTPException(404, "Document file unavailable")
    return FileResponse(
        path,
        filename=row["filename"],
        media_type="application/pdf"
        if row["file_type"] == "pdf"
        else "application/octet-stream",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/{document_id}/retry", status_code=202)
async def retry_document(
    document_id: uuid.UUID, current_user: User = Depends(require_writer)
):
    tenant_id = str(current_user.tenant_id)
    job_id = str(uuid.uuid4())
    async with tenant_connection(tenant_id) as conn:
        locked = await conn.fetchval(
            "SELECT pg_try_advisory_xact_lock(hashtextextended($1,0))", str(document_id)
        )
        if not locked:
            raise HTTPException(409, "Document is still processing")
        row = await conn.fetchrow(
            SELECT_DOCUMENTS + " WHERE d.id=$1 AND d.tenant_id=$2 FOR UPDATE OF d",
            document_id,
            current_user.tenant_id,
        )
        if not row:
            raise HTTPException(404, "Document not found")
        if row["status"] not in ("failed", "indexed") and not row["stalled"]:
            raise HTTPException(
                409,
                "Only failed, stalled or indexed documents can be queued for retry or reindexing",
            )
        path = _storage_path(row["storage_uri"])
        if not path.is_file():
            raise HTTPException(
                409, "Original file unavailable; upload the document again"
            )
        await conn.execute(
            "UPDATE documents SET status='pending', updated_at=NOW(), metadata=(metadata - 'error') || $3::jsonb WHERE id=$1 AND tenant_id=$2",
            document_id,
            current_user.tenant_id,
            json.dumps({"stage": "queued", "job_id": job_id}),
        )
        await _audit(conn, current_user, document_id, "retry")
    await _dispatch(str(document_id), tenant_id, str(path), job_id)
    return {"document_id": str(document_id), "status": "pending"}


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID, current_user: User = Depends(require_writer)
):
    async with tenant_connection(str(current_user.tenant_id)) as conn:
        locked = await conn.fetchval(
            "SELECT pg_try_advisory_xact_lock(hashtextextended($1,0))", str(document_id)
        )
        if not locked:
            raise HTTPException(
                409, "Document is processing; retry deletion after it finishes"
            )
        row = await conn.fetchrow(
            "DELETE FROM documents WHERE id=$1 AND tenant_id=$2 RETURNING *",
            document_id,
            current_user.tenant_id,
        )
        if not row:
            raise HTTPException(404, "Document not found")
        path = _storage_path(row["storage_uri"])
        await _audit(conn, current_user, document_id, "delete")
    # Never destroy the original before the database commit has succeeded.
    # A failed cleanup leaves an inaccessible orphan, rather than losing a live file.
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.exception("Deleted document %s requires storage cleanup", document_id)
    return {
        "status": "deleted",
        "document_id": str(document_id),
        "filename": row["filename"],
    }
