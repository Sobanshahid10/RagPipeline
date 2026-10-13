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

    def __init__(self, model_override: str | None = None) -> None:
        self.model_override = model_override

    @property
    def provider(self) -> str:
        if self.model_override:
            return "gemini" if self.model_override.startswith("gemini-") else "groq"
        return settings.LLM_PROVIDER.casefold()

    async def stream(self, system: str, user_prompt: str) -> AsyncIterator[str]:
        provider = self.provider
        if self.model_override and provider == "groq" and not settings.GROQ_API_KEY:
            raise RuntimeError("Groq API key is missing. Add GROQ_API_KEY to .env and restart the backend.")
        if self.model_override and provider == "gemini" and not settings.GEMINI_API_KEY:
            raise RuntimeError("Gemini API key is missing. Add GEMINI_API_KEY to .env and restart the backend.")

        if provider == "groq" and settings.GROQ_API_KEY:
            try:
                import httpx
                import json

                payload = {
                    "model": self.model_override or (settings.LLM_MODEL if settings.LLM_MODEL.startswith("openai/gpt-oss-") else "openai/gpt-oss-120b"),
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": True,
                }
                headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: ") or line == "data: [DONE]":
                                continue
                            data = json.loads(line[6:])
                            choices = data.get("choices", [])
                            text = choices[0].get("delta", {}).get("content") if choices else None
                            if text:
                                yield text
                return
            except Exception as exc:
                if self.model_override:
                    raise RuntimeError("Groq answer generation failed. Check the model, API key, and quota.") from exc
                logger.warning("Groq stream failed; using grounded fallback: %s", exc)

        if provider == "gemini" and settings.GEMINI_API_KEY:
            import httpx
            import json

            configured_model = self.model_override or settings.LLM_MODEL
            primary_model = configured_model if configured_model.startswith("gemini-") else "gemini-3.5-flash"
            gemini_candidates = [primary_model] + [m for m in ("gemini-3.5-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite") if m != primary_model]

            gemini_succeeded = False
            for model in gemini_candidates:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:"
                    "streamGenerateContent?alt=sse"
                )
                payload = {
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                }
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        async with client.stream("POST", url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY}) as response:
                            if response.status_code == 200:
                                async for line in response.aiter_lines():
                                    if not line.startswith("data: "):
                                        continue
                                    data = json.loads(line[6:])
                                    candidates = data.get("candidates", [])
                                    if not candidates:
                                        continue
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    text = "".join(str(part.get("text", "")) for part in parts)
                                    if text:
                                        gemini_succeeded = True
                                        yield text
                                if gemini_succeeded:
                                    return
                except Exception as exc:
                    logger.warning("Gemini model %s stream failed: %s; trying fallback", model, exc)
                    continue

            # If all Gemini models are exhausted, fall back to Groq if configured
            if settings.GROQ_API_KEY:
                try:
                    payload = {
                        "model": "openai/gpt-oss-120b",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": True,
                    }
                    headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}"}
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        async with client.stream("POST", "https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers) as response:
                            if response.status_code == 200:
                                async for line in response.aiter_lines():
                                    if not line.startswith("data: ") or line == "data: [DONE]":
                                        continue
                                    data = json.loads(line[6:])
                                    choices = data.get("choices", [])
                                    text = choices[0].get("delta", {}).get("content") if choices else None
                                    if text:
                                        yield text
                                return
                except Exception as exc:
                    logger.warning("Groq emergency fallback stream failed: %s", exc)

            if self.model_override:
                raise RuntimeError("LLM answer generation failed across providers. Check model, API key, and quota.")

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
