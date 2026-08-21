"""
Multi-Query Expansion Module.

Expands a single user query into multiple alternative phrasings using an LLM,
increasing retrieval recall across lexical and semantic variations.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

EXPANSION_PROMPT_TEMPLATE = (
    "Generate 3 alternative phrasings of this search query for a document retrieval system. "
    "Return as a JSON array only: {query}"
)


def _clean_and_parse_alternatives(raw_text: str) -> list[str]:
    """Extract and parse a JSON array of query alternatives from raw LLM output."""
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    # Remove markdown code fences if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            text = text.replace("```json", "").replace("```", "").strip()

    start_idx = text.find("[")
    end_idx = text.rfind("]")
    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        raise ValueError(f"No valid JSON array boundaries found in: {text[:100]}")

    json_str = text[start_idx : end_idx + 1]
    parsed = json.loads(json_str)

    if not isinstance(parsed, list):
        raise ValueError("Parsed JSON is not a list.")

    alternatives = [str(item).strip() for item in parsed if isinstance(item, (str, int, float)) and str(item).strip()]
    return alternatives


async def _call_llm_for_expansion(query: str, llm_client: Optional[Any] = None) -> list[str]:
    """Query LLM to generate alternative phrasings."""
    prompt = EXPANSION_PROMPT_TEMPLATE.format(query=query)

    if llm_client is not None:
        # 1. Support OpenAI / Groq AsyncClient
        if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
            response = await llm_client.chat.completions.create(
                model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "You are a search query optimizer. Return only a JSON array of strings."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            raw_content = response.choices[0].message.content
            return _clean_and_parse_alternatives(raw_content)

        # 2. Support callable async function / mock
        elif callable(llm_client):
            res = await llm_client(prompt)
            if isinstance(res, list):
                return [str(x) for x in res]
            return _clean_and_parse_alternatives(str(res))

        # 3. Support client with .generate / .agenerate
        elif hasattr(llm_client, "agenerate"):
            res = await llm_client.agenerate([prompt])
            raw_text = res.generations[0][0].text
            return _clean_and_parse_alternatives(raw_text)

        elif hasattr(llm_client, "generate"):
            res = llm_client.generate(prompt)
            if isinstance(res, list):
                return [str(x) for x in res]
            return _clean_and_parse_alternatives(str(res))

    # Groq API fallback if configured
    if settings.GROQ_API_KEY:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.LLM_MODEL if "gpt-oss" in settings.LLM_MODEL or "llama" in settings.LLM_MODEL else "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": "You are a search query optimizer. Return only a JSON array of strings."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return _clean_and_parse_alternatives(content)
        except Exception as groq_err:
            logger.debug("Groq query expansion failed: %s", groq_err)

    # Gemini API fallback if configured
    if settings.GEMINI_API_KEY:
        try:
            import httpx
            model_name = settings.LLM_MODEL if "gemini" in settings.LLM_MODEL else "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4},
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        return _clean_and_parse_alternatives(raw_text)
        except Exception as gemini_err:
            logger.debug("Gemini query expansion failed: %s", gemini_err)

    return []


async def expand_query(query: str, llm_client: Optional[Any] = None) -> list[str]:
    """
    Expand `query` into multiple search variants using an LLM.
    Always returns `[query] + alternatives`, with the original query first.
    On failure or unparseable JSON, returns `[query]` and logs a warning.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return [query]

    try:
        alternatives = await _call_llm_for_expansion(cleaned_query, llm_client=llm_client)
        # Filter out duplicates and empty strings while preserving original query at index 0
        filtered_alternatives: list[str] = []
        seen = {cleaned_query.lower()}
        for alt in alternatives:
            alt_clean = alt.strip()
            if alt_clean and alt_clean.lower() not in seen:
                seen.add(alt_clean.lower())
                filtered_alternatives.append(alt_clean)

        return [cleaned_query] + filtered_alternatives
    except Exception as exc:
        logger.warning("Query expansion failed for '%s': %s. Returning original query.", cleaned_query, exc)
        return [cleaned_query]
