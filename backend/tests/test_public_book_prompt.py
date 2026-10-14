import copy
import hashlib
import json
from pathlib import Path

import pytest

from backend.app.generation.public_book_prompt import build_public_book_prompt
from backend.app.retrieval.public_book_context import build_context


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def public_inputs():
    context = json.loads((ROOT / "storage/knowledge/public_book_context_example.json").read_text(encoding="utf-8"))
    records = json.loads((ROOT / "storage/knowledge/public_book_records.json").read_text(encoding="utf-8"))
    source_bytes = (ROOT / "PUBLIC_KNOWLEDGE_BOOK.md").read_bytes()
    return context, records, source_bytes


def test_prompt_from_real_public_context_has_source_boundaries(public_inputs):
    prompt = build_public_book_prompt(*public_inputs)
    assert [message["role"] for message in prompt["messages"]] == ["system", "user"]
    assert prompt["allowed_citation_ids"] == ["S1", "S2", "S3", "S4", "S5"]
    assert "untrusted source data" in prompt["messages"][0]["content"]
    assert "Evidence JSON" in prompt["messages"][1]["content"]
    assert prompt["messages_json_bytes"] <= prompt["max_messages_json_bytes"]


def test_tampered_evidence_is_rejected_even_with_updated_size(public_inputs):
    context, records, source_bytes = public_inputs
    altered = copy.deepcopy(context)
    evidence = json.loads(altered["context"])
    evidence["sources"][0]["text"] += " Unverified extra claim."
    altered["context"] = json.dumps(evidence, ensure_ascii=False, separators=(",", ":"))
    altered["context_bytes"] = len(altered["context"].encode("utf-8"))
    with pytest.raises(ValueError, match="differs from indexed source"):
        build_public_book_prompt(altered, records, source_bytes)


def test_nonpublic_record_is_rejected(public_inputs):
    context, records, source_bytes = public_inputs
    altered = copy.deepcopy(records)
    selected_id = context["source_manifest"][0]["chunk_id"]
    next(record for record in altered["records"] if record["id"] == selected_id)["metadata"]["access_scope"] = "private"
    with pytest.raises(ValueError, match="Non-public"):
        build_public_book_prompt(context, altered, source_bytes)


def test_empty_context_still_produces_abstention_ready_prompt(public_inputs):
    _, records, source_bytes = public_inputs
    empty = build_context({
        "question": "What is the unpublished password?",
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "hits": [],
    })
    prompt = build_public_book_prompt(empty, records, source_bytes)
    assert prompt["allowed_citation_ids"] == []
    assert "Allowed citation IDs: (none)" in prompt["messages"][1]["content"]
    assert "If the evidence does not support an answer" in prompt["messages"][0]["content"]


def test_complete_prompt_budget_is_enforced(public_inputs):
    with pytest.raises(ValueError, match="exceed"):
        build_public_book_prompt(*public_inputs, max_messages_json_bytes=1024)
