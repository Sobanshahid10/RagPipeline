"""Token streaming, timing, and post-stream citation emission."""

from __future__ import annotations

import inspect
import logging
import re
from collections.abc import AsyncGenerator, AsyncIterator
from time import perf_counter
from typing import Any

from app.config import settings
from app.generation.citation_parser import extract_citations
from app.generation.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


def _count_tokens(text: str) -> int:
    try:
        import tiktoken

        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(re.findall(r"\w+|[^\w\s]", text))


def _token_text(token: Any) -> str:
    if isinstance(token, str):
        return token
    if isinstance(token, dict):
        return str(token.get("content") or token.get("text") or "")
    return str(getattr(token, "content", None) or getattr(token, "text", None) or token)


class ConfiguredLLMClient:
    """Stream through the configured provider, with a grounded local fallback."""

    async def stream(self, system: str, user_prompt: str) -> AsyncIterator[str]:
        provider = settings.LLM_PROVIDER.casefold()

        if provider == "groq" and settings.GROQ_API_KEY:
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(
                    api_key=settings.GROQ_API_KEY,
                    base_url="https://api.groq.com/openai/v1",
                )
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=True,
                    temperature=0.0,
                )
                async for part in response:
                    text = part.choices[0].delta.content or ""
                    if text:
                        yield text
                return
            except Exception as exc:
                logger.warning("Groq stream failed; using grounded fallback: %s", exc)

        if provider == "gemini" and settings.GEMINI_API_KEY:
            try:
                import httpx

                model = settings.LLM_MODEL if "gemini" in settings.LLM_MODEL else "gemini-2.0-flash"
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:"
                    f"streamGenerateContent?alt=sse&key={settings.GEMINI_API_KEY}"
                )
                payload = {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0.0},
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", url, json=payload) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            import json

                            data = json.loads(line[6:])
                            candidates = data.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text = "".join(str(part.get("text", "")) for part in parts)
                            if text:
                                yield text
                return
            except Exception as exc:
                logger.warning("Gemini stream failed; using grounded fallback: %s", exc)

        if provider == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI

                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model=settings.LLM_MODEL if not settings.LLM_MODEL.startswith("gpt-oss") else "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=True,
                    temperature=0.0,
                )
                async for part in response:
                    text = part.choices[0].delta.content or ""
                    if text:
                        yield text
                return
            except Exception as exc:
                logger.warning("OpenAI stream failed; using grounded fallback: %s", exc)

        # Never invent an answer when no model is configured. This remains useful for
        # local development and makes the safety behavior explicit.
        yield "I don't have enough information in the provided documents to answer this question."


async def stream_response(
    query: str,
    chunks: list[dict[str, Any]],
    llm_client: Any,
    route_used: str = "FACTUAL_VECTOR",
) -> AsyncGenerator[dict[str, Any], None]:
    """Stream answer tokens, resolved citations, and final generation metadata."""
    started = perf_counter()
    system, user_prompt = build_prompt(query, chunks)
    accumulated: list[str] = []
    ttft_ms: int | None = None

    token_stream = llm_client.stream(system, user_prompt)
    if inspect.isawaitable(token_stream):
        token_stream = await token_stream

    async for token in token_stream:
        text = _token_text(token)
        if not text:
            continue
        if ttft_ms is None:
            ttft_ms = round((perf_counter() - started) * 1000)
        accumulated.append(text)
        yield {"type": "token", "content": text}

    answer = "".join(accumulated)
    for citation in extract_citations(answer, chunks):
        yield {"type": "citation", "citation": citation}

    total_latency_ms = round((perf_counter() - started) * 1000)
    yield {
        "type": "done",
        "metadata": {
            "ttft_ms": ttft_ms or total_latency_ms,
            "total_latency_ms": total_latency_ms,
            "prompt_tokens": _count_tokens(system + user_prompt),
            "completion_tokens": _count_tokens(answer),
            "route_used": route_used,
            "chunks_retrieved": len(chunks),
        },
    }
