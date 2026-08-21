"""
LLM-Based Strategy Router Module.

Classifies incoming search queries into one of four retrieval and generation strategies:
- FACTUAL_VECTOR: Single-document factual lookups
- MULTI_HOP_GRAPH: Multi-step entity traversal and relational queries
- ANALYTICAL_SQL: Aggregation and analytical calculations over structured records
- GREETING_DIRECT: Conversational queries requiring direct LLM responses without retrieval
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

ROUTE_FACTUAL_VECTOR = "FACTUAL_VECTOR"
ROUTE_MULTI_HOP_GRAPH = "MULTI_HOP_GRAPH"
ROUTE_ANALYTICAL_SQL = "ANALYTICAL_SQL"
ROUTE_GREETING_DIRECT = "GREETING_DIRECT"

VALID_ROUTES = {
    ROUTE_FACTUAL_VECTOR,
    ROUTE_MULTI_HOP_GRAPH,
    ROUTE_ANALYTICAL_SQL,
    ROUTE_GREETING_DIRECT,
}

ROUTER_PROMPT = """You are an expert query routing classifier for an enterprise RAG system.
Classify the given query into EXACTLY ONE of these four routing strategies:

1. FACTUAL_VECTOR — Single-document factual lookups and policy questions.
   Example: "What does the refund policy say?" -> FACTUAL_VECTOR
   Example: "What is our company maternity leave policy?" -> FACTUAL_VECTOR

2. MULTI_HOP_GRAPH — Multi-step entity traversal, organizational hierarchies, dependencies, or cross-entity relationships.
   Example: "What rules apply to employees in London hired before 2022?" -> MULTI_HOP_GRAPH
   Example: "What is Alice's department?" -> MULTI_HOP_GRAPH
   Example: "Who reports to Bob and what projects are they managing?" -> MULTI_HOP_GRAPH

3. ANALYTICAL_SQL — Aggregations, metrics, counts, averages, and structured data summaries.
   Example: "How many queries were made last week?" -> ANALYTICAL_SQL
   Example: "What is the total number of approved documents in Q3?" -> ANALYTICAL_SQL

4. GREETING_DIRECT — Conversational pleasantries, greetings, or meta-questions requiring no document retrieval.
   Example: "Hello, how are you?" -> GREETING_DIRECT
   Example: "Hi there!" -> GREETING_DIRECT

Query: {query}

Respond with ONLY the exact strategy name (FACTUAL_VECTOR, MULTI_HOP_GRAPH, ANALYTICAL_SQL, or GREETING_DIRECT).
"""


def _heuristic_classify_route(query: str) -> str:
    """Rule-based fallback classifier for offline/test environments or LLM failures."""
    q = query.strip().lower()

    # 1. Greetings
    greeting_patterns = [
        r"^(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))\b",
        r"^how\s+are\s+you",
        r"^who\s+are\s+you",
        r"^what\s+can\s+you\s+do",
    ]
    if any(re.search(pat, q) for pat in greeting_patterns):
        return ROUTE_GREETING_DIRECT

    # 2. Analytical / SQL
    analytical_patterns = [
        r"\b(how\s+many|count\s+of|total\s+number|average|sum\s+of|percentage\s+of)\b",
        r"\b(last\s+(week|month|year|quarter)|per\s+(day|week|month))\b",
        r"\b(aggregate|statistics|quantities|metrics)\b",
    ]
    if any(re.search(pat, q) for pat in analytical_patterns):
        return ROUTE_ANALYTICAL_SQL

    # 3. Multi-Hop Graph / Entity Relations
    graph_patterns = [
        r"\b[A-Za-z]+'s\s+(department|manager|team|role|salary|office|lead|report)\b",
        r"\b(who\s+is\s+the\s+(manager|head|director|lead)\s+of)\b",
        r"\b(who\s+reports\s+to)\b",
        r"\b(rules\s+apply\s+to\s+employees\s+in)\b",
        r"\b(hired\s+before|hired\s+after)\b",
        r"\b(department\s+of|hierarchy|relationship|connection\s+between)\b",
    ]
    if any(re.search(pat, q) for pat in graph_patterns):
        return ROUTE_MULTI_HOP_GRAPH

    # Default to FACTUAL_VECTOR
    return ROUTE_FACTUAL_VECTOR


def _extract_route(response_text: str) -> str | None:
    """Extract valid route label from LLM output."""
    if not response_text:
        return None
    cleaned = response_text.strip().upper()
    for route in VALID_ROUTES:
        if route in cleaned:
            return route
    return None


async def classify_route(query: str, llm_client: Optional[Any] = None) -> str:
    """
    Classify `query` into one of four routing strategies.
    Defaults to FACTUAL_VECTOR on failure.
    """
    cleaned_query = query.strip()
    if not cleaned_query:
        return ROUTE_FACTUAL_VECTOR

    prompt = ROUTER_PROMPT.format(query=cleaned_query)

    if llm_client is not None:
        try:
            # 1. Support OpenAI / Groq AsyncClient
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                response = await llm_client.chat.completions.create(
                    model=getattr(settings, "LLM_MODEL", "gpt-4o-mini"),
                    messages=[
                        {"role": "system", "content": "You are a precise query routing classifier."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )
                route = _extract_route(response.choices[0].message.content)
                if route:
                    return route

            # 2. Support callable async function / mock
            elif callable(llm_client):
                res = await llm_client(prompt)
                route = _extract_route(str(res))
                if route:
                    return route

            # 3. Support client with .generate / .agenerate
            elif hasattr(llm_client, "agenerate"):
                res = await llm_client.agenerate([prompt])
                route = _extract_route(res.generations[0][0].text)
                if route:
                    return route

            elif hasattr(llm_client, "generate"):
                res = llm_client.generate(prompt)
                route = _extract_route(str(res))
                if route:
                    return route

        except Exception as exc:
            logger.warning("LLM router classification failed: %s. Using heuristic classifier.", exc)

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
                    {"role": "system", "content": "You are a precise query routing classifier."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    route = _extract_route(data["choices"][0]["message"]["content"])
                    if route:
                        return route
        except Exception as groq_err:
            logger.debug("Groq route classification call failed: %s", groq_err)

    # Gemini API fallback if configured
    if settings.GEMINI_API_KEY:
        try:
            import httpx
            model_name = settings.LLM_MODEL if "gemini" in settings.LLM_MODEL else "gemini-2.0-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.0},
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        route = _extract_route(raw_text)
                        if route:
                            return route
        except Exception as gemini_err:
            logger.debug("Gemini route classification call failed: %s", gemini_err)

    # Fallback to deterministic heuristic classifier
    return _heuristic_classify_route(cleaned_query)
