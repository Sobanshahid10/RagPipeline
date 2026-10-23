"""
Frontend API Integration & Day 9 Contract Tests.

Tests the endpoints and SSE contracts required by the Next.js 14 frontend:
- Document upload and listing contracts
- Document file serving for PDFViewer
- Streaming query SSE event structure (token, citation, done)
- Citation format with bounding boxes matching frontend TypeScript types
"""

import os
import uuid
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from types import SimpleNamespace
from app.api import documents as documents_api
from fastapi.testclient import TestClient

from app.main import app
from app.api.documents import list_documents, get_document_file, get_document_status
from app.generation.citation_parser import extract_citations
from app.generation.streamer import stream_response


@pytest.mark.asyncio
async def test_citation_schema_compatibility():
    """Verify extracted citations contain document_id, page_number, bounding_box, and filename."""
    sample_chunk_id = str(uuid.uuid4())
    sample_doc_id = str(uuid.uuid4())
    chunks = [
        {
            "id": sample_chunk_id,
            "document_id": sample_doc_id,
            "page_number": 3,
            "source_filename": "annual_report.pdf",
            "bounding_box": {"ymin": 0.1, "xmin": 0.2, "ymax": 0.3, "xmax": 0.8},
            "content": "Total revenue grew by 24% year-over-year.",
        }
    ]

    answer_text = f"Revenue grew by 24% [SOURCE:{sample_chunk_id}:3]."
    citations = extract_citations(answer_text, chunks)

    assert len(citations) == 1
    cit = citations[0]
    assert cit["chunk_id"] == sample_chunk_id
    assert cit["document_id"] == sample_doc_id
    assert cit["page_number"] == 3
    assert cit["source_filename"] == "annual_report.pdf"
    assert cit["bounding_box"] == {"ymin": 0.1, "xmin": 0.2, "ymax": 0.3, "xmax": 0.8}
    assert "revenue" in cit["excerpt"].lower()


@pytest.mark.asyncio
async def test_stream_response_events():
    """Verify stream_response generates token, citation, and done events properly."""
    sample_chunk_id = str(uuid.uuid4())
    chunks = [
        {
            "id": sample_chunk_id,
            "document_id": str(uuid.uuid4()),
            "page_number": 1,
            "source_filename": "spec.pdf",
            "bounding_box": {"ymin": 0.05, "xmin": 0.05, "ymax": 0.2, "xmax": 0.9},
            "content": "Nexus RAG supports multi-tenant vector and BM25 search.",
        }
    ]

    class MockLLM:
        async def stream(self, system, user_prompt):
            tokens = [
                "Nexus ",
                "RAG ",
                "supports ",
                "search ",
                f"[SOURCE:{sample_chunk_id}:1].",
            ]
            for t in tokens:
                yield t

    mock_llm = MockLLM()
    events = []
    async for event in stream_response("How does search work?", chunks, mock_llm):
        events.append(event)

    types = [e["type"] for e in events]
    assert "token" in types
    assert "citation" in types
    assert "done" in types

    done_event = next(e for e in events if e["type"] == "done")
    assert "ttft_ms" in done_event["metadata"]
    assert "total_latency_ms" in done_event["metadata"]


@pytest.mark.asyncio
async def test_list_documents_mocked():
    """Verify list_documents returns properly structured list."""
    mock_conn = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=AsyncMock())
    mock_conn.fetch.return_value = [
        {
            "id": uuid.uuid4(),
            "filename": "demo.pdf",
            "file_type": "pdf",
            "status": "indexed",
            "total_pages": 5,
            "chunk_count": 12,
            "created_at": MagicMock(isoformat=lambda: "2026-08-23T10:00:00"),
            "updated_at": MagicMock(isoformat=lambda: "2026-08-23T10:05:00"),
            "stalled": False,
        }
    ]

    with patch("asyncpg.connect", return_value=mock_conn):
        results = await list_documents(SimpleNamespace(tenant_id=uuid.uuid4()))
        assert len(results) == 1
        assert results[0].filename == "demo.pdf"
        assert results[0].status == "indexed"
        assert results[0].total_pages == 5
        assert results[0].chunk_count == 12


@pytest.mark.asyncio
async def test_get_document_file_mocked(tmp_path, monkeypatch):
    monkeypatch.setattr(documents_api, "UPLOAD_DIR", tmp_path)
    """Verify get_document_file serves the existing PDF file."""
    fake_pdf = tmp_path / "test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 test document content")

    mock_conn = AsyncMock()
    mock_conn.transaction = MagicMock(return_value=AsyncMock())
    mock_conn.fetchrow.return_value = {
        "storage_uri": str(fake_pdf),
        "filename": "test.pdf",
        "file_type": "pdf",
    }

    with patch("asyncpg.connect", return_value=mock_conn):
        response = await get_document_file(
            uuid.uuid4(), SimpleNamespace(tenant_id=uuid.uuid4())
        )
        assert response.status_code == 200
        assert response.media_type == "application/pdf"
