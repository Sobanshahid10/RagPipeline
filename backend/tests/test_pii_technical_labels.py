from types import SimpleNamespace
import pytest

try:
    from presidio_analyzer import RecognizerResult
    from presidio_anonymizer import AnonymizerEngine
except ImportError:
    pytest.skip("presidio not installed in local environment", allow_module_level=True)

from app.ingestion import pii


def test_software_labels_survive_false_person_matches_but_real_pii_does_not(monkeypatch):
    text = "Agent Dispatcher enters Quarantine Mode. Agent John Doe uses john@example.com."
    results = []
    for word in ["Dispatcher", "Quarantine Mode", "John Doe"]:
        start = text.index(word)
        results.append(RecognizerResult(entity_type="PERSON", start=start, end=start + len(word), score=0.9))
    monkeypatch.setattr(pii, "_init_presidio", lambda: None)
    monkeypatch.setattr(pii, "_presidio_available", True)
    monkeypatch.setattr(pii, "_analyzer", SimpleNamespace(analyze=lambda **kwargs: results))
    monkeypatch.setattr(pii, "_anonymizer", AnonymizerEngine())
    monkeypatch.setattr(pii.settings, "PII_REQUIRED", True)
    masked = pii.mask_pii(text)
    assert "Agent Dispatcher" in masked
    assert "Quarantine Mode" in masked
    assert "John Doe" not in masked
    assert "john@example.com" not in masked
