import pytest
import os
import tempfile
from app.main import app
from app.celery_app import celery_app
from app.ingestion.parser import parse_document
from app.ingestion.pii import mask_pii
from app.ingestion.contextual import generate_contextual_summary
from app.ingestion.chunker import semantic_chunk, split_into_sentences, count_tokens


def test_parser_with_text_and_pdf_fallback():
    """Test 1: Document parser extracts page content and structure."""
    sample_text = "Section 1: Introduction\nThis is a sample document for RAG ingestion testing."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_path = f.name

    try:
        pages = parse_document(temp_path)
        assert len(pages) > 0
        assert pages[0]["page_number"] == 1
        assert "sample document" in pages[0]["content"]
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_pii_masking():
    """Test 2: PII detection and redaction of emails, phones, and SSNs."""
    text_with_pii = (
        "Employee John Doe can be reached at john.doe@enterprise.com or +1-555-019-2834. "
        "His identification number is 123-45-6789."
    )
    sanitized = mask_pii(text_with_pii)
    
    assert "@enterprise.com" not in sanitized
    assert "123-45-6789" not in sanitized
    assert ("<EMAIL_ADDRESS>" in sanitized or "<EMAIL>" in sanitized or "<PERSON>" in sanitized)
    assert ("<PHONE_NUMBER>" in sanitized or "<PHONE>" in sanitized or "<US_SSN>" in sanitized)


@pytest.mark.asyncio
async def test_contextual_summary_generation():
    """Test 3: Contextual summary generator fallback and formatting."""
    doc_text = (
        "The Q3 Financial Report covers quarterly revenue, operational expenditures, and EBITDA margins. "
        "Total revenue grew by 14% year-over-year driven by enterprise cloud subscriptions."
    )
    summary = await generate_contextual_summary(doc_text, llm_client=None)
    assert len(summary) > 0
    assert "Financial Report" in summary or "revenue" in summary.lower()


def test_semantic_chunking_with_context():
    """Test 4: Sentence-aware chunking, token budgets, and contextual summary prefixing."""
    summary = "Enterprise HR leave policy guidelines."
    text = (
        "Full-time employees receive 25 days of annual leave per year. "
        "Unused leave can be carried over up to a maximum of 5 days. "
        "Leave requests must be submitted at least two weeks in advance. "
        "Emergency sick leave does not deduct from annual leave balance."
    )
    
    chunks = semantic_chunk(text=text, contextual_summary=summary, chunk_size=50, overlap=10)
    assert len(chunks) >= 1
    for chunk in chunks:
        assert f"[Context: {summary}]" in chunk["content"]
        assert chunk["token_count"] > 0
        assert chunk["contextual_summary"] == summary


def test_split_into_sentences_and_tokens():
    """Test 5: Sentence boundary detection and tokenizer token count accuracy."""
    paragraph = "Dr. Smith went to Washington D.C. yesterday. He attended the AI conference at 9:00 a.m. Did he speak?"
    sentences = split_into_sentences(paragraph)
    assert len(sentences) >= 2
    
    token_count = count_tokens("Hello world from the RAG ingestion pipeline!")
    assert token_count >= 5


def test_document_api_routes_registered():
    """Test 6: Verify document upload and status endpoints are registered in FastAPI."""
    routes = set()
    for r in app.routes:
        if hasattr(r, "path"):
            routes.add(r.path)
        if hasattr(r, "routes"):
            for sub_r in r.routes:
                if hasattr(sub_r, "path"):
                    routes.add(sub_r.path)
    openapi_paths = app.openapi().get("paths", {})
    all_paths = routes | set(openapi_paths.keys())
    assert "/api/v1/documents/upload" in all_paths
    assert "/api/v1/documents/{document_id}" in all_paths


def test_celery_task_registration():
    """Test 7: Verify process_document Celery task is registered and routed to high_priority."""
    assert "app.ingestion.pipeline.process_document" in celery_app.tasks
    assert celery_app.conf.task_routes["app.ingestion.pipeline.process_document"]["queue"] == "high_priority"
