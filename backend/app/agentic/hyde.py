"""
Hypothetical Document Embedding (HyDE) Generation Module.

Generates a hypothetical document excerpt using an LLM that directly answers the user's query,
then computes and returns the embedding of that hypothetical document for dense vector retrieval.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

HYDE_PROMPT_TEMPLATE = "Write a 3-sentence document excerpt that would directly answer this question: {query}"


async def _call_llm_for_hyde(query: str, llm_client: Optional[Any] = None) -> str:
    """Call LLM client to generate a hypothetical answer document."""
    prompt = HYDE_PROMPT_TEMPLATE.format(query=query)

    if llm_client is not None:
        try:
            # 1. Support OpenAI / Groq AsyncClient
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                response = await llm_client.chat.completions.create(
                    model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "You are a helpful document assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                return response.choices[0].message.content.strip()

            # 2. Support callable async function / mock
            elif callable(llm_client):
                res = await llm_client(prompt)
                return str(res).strip()

            # 3. Support client with .generate / .agenerate
            elif hasattr(llm_client, "agenerate"):
                res = await llm_client.agenerate([prompt])
                return res.generations[0][0].text.strip()

            elif hasattr(llm_client, "generate"):
                res = llm_client.generate(prompt)
                return str(res).strip()

        except Exception as exc:
            logger.warning("LLM call for HyDE generation failed: %s. Using default hypothetical answer.", exc)

    # Groq / Gemini API fallback if API keys configured
    if settings.GROQ_API_KEY:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.LLM_MODEL if settings.LLM_MODEL.startswith("openai/gpt-oss-") else "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": "You are a helpful document assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception as groq_err:
            logger.debug("Groq HyDE call failed: %s", groq_err)

    if settings.GEMINI_API_KEY:
        try:
            import httpx
            model_name = settings.LLM_MODEL if settings.LLM_MODEL.startswith("gemini-") else "gemini-3.8-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post(url, json=payload, headers={"x-goog-api-key": settings.GEMINI_API_KEY})
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        except Exception as gemini_err:
            logger.debug("Gemini HyDE call failed: %s", gemini_err)

    # Deterministic hypothetical excerpt fallback
    return f"This official document directly answers the inquiry regarding {query}. It outlines the core principles, detailed guidelines, and relevant policy rules applicable to all stakeholders."


async def generate_hyde_embedding(
    query: str,
    llm_client: Optional[Any] = None,
    embedder: Optional[Any] = None,
) -> list[float]:
    """
    Generate a hypothetical answer document for `query` via LLM and return its vector embedding.
    """
    hypothetical_doc = await _call_llm_for_hyde(query, llm_client=llm_client)

    # Embed the hypothetical document excerpt (not the query)
    if embedder is not None:
        if hasattr(embedder, "embed_text"):
            res = embedder.embed_text(hypothetical_doc)
            if hasattr(res, "__await__"):
                return await res
            return res
        elif callable(embedder):
            res = embedder(hypothetical_doc)
            if hasattr(res, "__await__"):
                return await res
            return res

    # Use default application embedder
    from app.ingestion import embedder as app_embedder

    return await app_embedder.embed_text(hypothetical_doc)
