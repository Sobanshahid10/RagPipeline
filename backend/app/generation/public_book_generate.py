"""Step-eleven Gemini generation from verified public-book evidence.

The CLI validates and previews by default. --send makes exactly one API request.
The returned model response is saved raw for later validation.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import httpx

from backend.app.config import settings
from backend.app.generation.public_book_prompt import build_public_book_prompt

DEFAULT_MODEL = "gemini-3.8-flash"
SUGGESTED_MODELS = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
)
MODEL_ID_PATTERN = re.compile(r"gemini-[a-z0-9][a-z0-9.-]*\Z")


def select_model(override: str | None = None, configured: str | None = None) -> str:
    model = override or configured or DEFAULT_MODEL
    if not MODEL_ID_PATTERN.fullmatch(model):
        raise ValueError("Choose a Gemini model ID such as gemini-3.8-flash")
    return model


def gemini_payload(prompt: dict[str, Any]) -> dict[str, Any]:
    messages = prompt["messages"]
    if len(messages) != 2 or [entry.get("role") for entry in messages] != ["system", "user"]:
        raise ValueError("Expected one system message and one user message")
    return {
        "systemInstruction": {"parts": [{"text": messages[0]["content"]}]},
        "contents": [{"role": "user", "parts": [{"text": messages[1]["content"]}]}],
    }


def send_to_gemini(
    prompt: dict[str, Any], *, model: str, api_key: str,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    model = select_model(model)
    if not api_key or not api_key.strip():
        raise ValueError("Set GEMINI_API_KEY in the repository .env file before using --send")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=90.0)
    try:
        response = client.post(url, headers={"x-goog-api-key": api_key}, json=gemini_payload(prompt))
        if response.status_code == 429:
            raise RuntimeError(
                f"Gemini quota or rate limit reached for {model}. Check AI Studio limits or retry "
                "with --model and another available model; switching may not help if the project-wide limit is exhausted."
            )
        if response.status_code == 404:
            raise RuntimeError(f"Gemini model {model} is unavailable for this API/project; choose an available model ID")
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            client.close()


def main() -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Preview or send a public-book prompt to Gemini")
    parser.add_argument("--context", type=Path, default=root / "storage/knowledge/public_book_context_example.json")
    parser.add_argument("--records", type=Path, default=root / "storage/knowledge/public_book_records.json")
    parser.add_argument("--source", type=Path, default=root / "PUBLIC_KNOWLEDGE_BOOK.md")
    parser.add_argument("--output", type=Path, default=root / "storage/knowledge/public_book_generation.json")
    parser.add_argument("--model", help="Gemini model ID for this request; overrides LLM_MODEL")
    parser.add_argument("--list-models", action="store_true", help="Show suggested current text models without calling Gemini")
    parser.add_argument("--send", action="store_true", help="Make one billable or quota-counted Gemini request")
    args = parser.parse_args()
    if args.list_models:
        print("\n".join(SUGGESTED_MODELS))
        return 0
    model = select_model(args.model, settings.LLM_MODEL)
    prompt = build_public_book_prompt(
        json.loads(args.context.read_text(encoding="utf-8")),
        json.loads(args.records.read_text(encoding="utf-8")),
        args.source.read_bytes(),
    )
    if not args.send:
        print(json.dumps({
            "mode": "preview_only", "model": model, "question": prompt["question"],
            "citation_ids": prompt["allowed_citation_ids"],
            "messages_json_bytes": prompt["messages_json_bytes"], "api_calls": 0,
        }, indent=2))
        return 0
    raw_response = send_to_gemini(prompt, model=model, api_key=settings.GEMINI_API_KEY or "")
    artifact = {
        "generation_version": 1,
        "source_name": prompt["source_name"],
        "source_sha256": prompt["source_sha256"],
        "question": prompt["question"],
        "model": model,
        "allowed_citation_ids": prompt["allowed_citation_ids"],
        "source_manifest": prompt["source_manifest"],
        "raw_response": raw_response,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "sent", "model": model, "output": str(args.output), "api_calls": 1}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
