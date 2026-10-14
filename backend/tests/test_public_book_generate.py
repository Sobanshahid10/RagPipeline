import json
from pathlib import Path

import httpx
import pytest

from backend.app.generation.public_book_generate import gemini_payload, select_model, send_to_gemini
from backend.app.generation.public_book_prompt import build_public_book_prompt


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def prompt():
    context = json.loads((ROOT / "storage/knowledge/public_book_context_example.json").read_text(encoding="utf-8"))
    records = json.loads((ROOT / "storage/knowledge/public_book_records.json").read_text(encoding="utf-8"))
    return build_public_book_prompt(context, records, (ROOT / "PUBLIC_KNOWLEDGE_BOOK.md").read_bytes())


def test_model_can_be_switched_for_one_request():
    assert select_model(None, "gemini-3.8-flash") == "gemini-3.8-flash"
    assert select_model("gemini-3.7-flash", "gemini-3.8-flash") == "gemini-3.7-flash"
    with pytest.raises(ValueError):
        select_model("https://example.com/key")


def test_request_maps_roles_and_keeps_key_out_of_url(prompt):
    seen = {}

    def handler(request):
        seen["request"] = request
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = send_to_gemini(prompt, model="gemini-3.7-flash", api_key="test-secret", client=client)
    request = seen["request"]
    payload = json.loads(request.content)
    assert request.url.path.endswith("/gemini-3.7-flash:generateContent")
    assert "test-secret" not in str(request.url)
    assert request.headers["x-goog-api-key"] == "test-secret"
    assert payload == gemini_payload(prompt)
    assert payload["systemInstruction"]["parts"][0]["text"] == prompt["messages"][0]["content"]
    assert payload["contents"][0]["parts"][0]["text"] == prompt["messages"][1]["content"]
    assert response["candidates"][0]["content"]["parts"][0]["text"] == "{}"


def test_quota_error_does_not_silently_call_another_model(prompt):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(429, json={"error": {"message": "limit"}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="quota or rate limit"):
            send_to_gemini(prompt, model="gemini-3.8-flash", api_key="test-secret", client=client)
    assert len(calls) == 1


def test_missing_key_stops_before_request(prompt):
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        send_to_gemini(prompt, model="gemini-3.8-flash", api_key="")
