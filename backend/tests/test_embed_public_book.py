"""Checks for the public-book embedding boundary; API calls are never mocked as output data."""

import hashlib
import json
import math

import pytest

from backend.app.ingestion.embed_public_book import (
    DIMENSIONS,
    LocalMiniLM,
    MODEL_ID,
    generate_embeddings,
    validate_records,
    validate_vector,
)
from huggingface_hub import snapshot_download
from pathlib import Path


def sample_artifact():
    source = b"source book"
    content = "A useful fact."
    source_hash = hashlib.sha256(source).hexdigest()
    record = {
        "id": "chunk-1",
        "content": content,
        "metadata": {
            "section_title": "Education",
            "source_sha256": source_hash,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
        },
    }
    artifact = {
        "source_name": "PUBLIC_KNOWLEDGE_BOOK.md",
        "source_sha256": source_hash,
        "record_count": 1,
        "records": [record],
    }
    return artifact, source


def test_source_integrity():
    artifact, source = sample_artifact()
    assert validate_records(artifact, source) == artifact["records"]
    artifact["records"][0]["content"] = "Altered"
    with pytest.raises(ValueError, match="Content hash mismatch"):
        validate_records(artifact, source)


def test_vector_rejects_invalid_output():
    with pytest.raises(ValueError, match="expected"):
        validate_vector([1.0], record_id="chunk-1")
    with pytest.raises(ValueError, match="non-finite"):
        validate_vector([math.nan] + [0.0] * (DIMENSIONS - 1), record_id="chunk-1")
    with pytest.raises(ValueError, match="norm"):
        validate_vector([0.0] * DIMENSIONS, record_id="chunk-1")


def test_stale_checkpoint_is_rejected(tmp_path):
    artifact, source = sample_artifact()
    output = tmp_path / "embeddings.json"
    checkpoint = tmp_path / "embeddings.partial.json"
    checkpoint.write_text(json.dumps({"model": "wrong", "source_sha256": artifact["source_sha256"], "vectors": {}}))
    model = LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))
    with pytest.raises(ValueError, match="checkpoint belongs"):
        generate_embeddings(artifact, source, model=model, output=output)
    assert not output.exists()


def test_local_model_produces_deterministic_vector():
    model = LocalMiniLM(Path(snapshot_download(MODEL_ID, local_files_only=True)))
    first, tokens, windows = model.embed("A useful fact.")
    second, _, _ = model.embed("A useful fact.")
    assert len(first) == DIMENSIONS
    assert first == second
    assert 2 < tokens < 20 and windows == 1
    assert abs(math.sqrt(sum(x * x for x in first)) - 1) < 0.001
