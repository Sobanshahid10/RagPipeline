"""
Knowledge Graph Entity & Relationship Extraction Module (GraphRAG Ingestion).

Extracts semantic triples (subject, predicate, object) from document chunks using:
1. spaCy NER pre-filtering to skip chunks with no named entities (reduces LLM costs).
2. LLM triple extraction (Groq GPT-OSS 120B/20B, Gemini 2.0/1.5 Flash, or OpenAI).
3. Robust JSON validation and entity normalization (title-casing, whitespace stripping).
4. Bulk insertion into the PostgreSQL `entity_triples` table.
"""

from __future__ import annotations

import re
import json
import logging
from typing import List, Dict, Any, Optional
import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Cached spaCy NLP instance
_nlp_spacy = None


def _get_spacy_nlp():
    """Lazy load spaCy NLP pipeline with fallback if model is not installed."""
    global _nlp_spacy
    if _nlp_spacy is None:
        try:
            import spacy
            try:
                _nlp_spacy = spacy.load("en_core_web_sm")
            except Exception:
                # Fallback to blank English model with sentencizer if small model not downloaded
                _nlp_spacy = spacy.blank("en")
                if "sentencizer" not in _nlp_spacy.pipe_names:
                    _nlp_spacy.add_pipe("sentencizer")
        except Exception as e:
            logger.warning(f"Failed to initialize spaCy NLP: {e}")
            _nlp_spacy = None
    return _nlp_spacy


def _get_raw_db_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def has_named_entities(text: str) -> bool:
    """
    Pre-filter check using spaCy NER to determine if text contains named entities.
    Optimization to bypass expensive LLM calls for chunks without extractable entities.
    """
    cleaned = text.strip()
    if not cleaned:
        return False

    nlp = _get_spacy_nlp()
    if nlp is not None:
        try:
            doc = nlp(cleaned)
            # If standard NER found entities, return True
            if doc.ents and len(doc.ents) > 0:
                return True
            # Check for noun chunks or capitalized proper nouns as secondary heuristic
            has_proper_nouns = any(token.pos_ in ("PROPN", "NOUN") and token.text[0].isupper() for token in doc)
            if has_proper_nouns:
                return True
        except Exception as err:
            logger.debug(f"spaCy entity detection error: {err}")

    # Regex heuristic fallback: looks for capitalized words (e.g. "Alice", "London Office", "UK Leave Policy")
    capitalized_words = re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", cleaned)
    return len(capitalized_words) >= 1


KNOWN_ACRONYMS = {
    "uk", "us", "usa", "eu", "hr", "ai", "ml", "it", "ceo", "cto", "cfo", "api", "sql", "llm", "rag", "cte", "db", "uri", "url"
}


def _normalize_entity(entity: str) -> str:
    """Normalize entity names to clean Title Case with stripped whitespace and uppercase acronyms."""
    if not entity or not isinstance(entity, str):
        return ""
    # Strip whitespace and collapse multiple spaces
    cleaned = " ".join(entity.strip().split())
    words = cleaned.split()
    normalized_words = []
    for w in words:
        lower_w = w.lower()
        if lower_w in KNOWN_ACRONYMS or (w.isupper() and len(w) <= 4):
            normalized_words.append(lower_w.upper())
        else:
            normalized_words.append(w.capitalize())
    return " ".join(normalized_words)


def _normalize_predicate(pred: str) -> str:
    """Normalize relationship predicate to snake_case / lowercase string."""
    if not pred or not isinstance(pred, str):
        return "related_to"
    cleaned = " ".join(pred.strip().split()).lower()
    return cleaned.replace(" ", "_")


def _clean_and_parse_json(response_text: str) -> List[Dict[str, str]]:
    """
    Safely extract and parse JSON array from raw LLM output.
    Strips markdown code fences and handles trailing commas or formatting anomalies.
    """
    if not response_text or not response_text.strip():
        return []

    text = response_text.strip()

    # Remove markdown code block markers if present (```json ... ``` or ``` ...)
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
        else:
            text = text.replace("```json", "").replace("```", "").strip()

    # Find JSON array boundaries [ ... ]
    start_idx = text.find("[")
    end_idx = text.rfind("]")

    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        return []

    json_str = text[start_idx : end_idx + 1]

    try:
        data = json.loads(json_str)
        if not isinstance(data, list):
            return []

        validated_triples: List[Dict[str, str]] = []
        for item in data:
            if isinstance(item, dict):
                sub = item.get("subject") or item.get("source") or item.get("head")
                pred = item.get("predicate") or item.get("relation") or item.get("type")
                obj = item.get("object") or item.get("target") or item.get("tail")

                if sub and pred and obj and isinstance(sub, str) and isinstance(obj, str):
                    norm_sub = _normalize_entity(sub)
                    norm_obj = _normalize_entity(obj)
                    norm_pred = _normalize_predicate(str(pred))

                    if norm_sub and norm_obj and norm_sub.lower() != norm_obj.lower():
                        validated_triples.append({
                            "subject": norm_sub,
                            "predicate": norm_pred,
                            "object": norm_obj
                        })

        return validated_triples

    except Exception as parse_err:
        logger.debug(f"JSON parsing failed for LLM response: {parse_err}. Raw: {text[:200]}")
        return []


def _heuristic_triple_extractor(text: str) -> List[Dict[str, str]]:
    """
    Deterministic rule-based triple extraction fallback for offline/test environments.
    Extracts Subject-Predicate-Object triples using linguistic heuristics and regex patterns.
    """
    triples: List[Dict[str, str]] = []
    # Match patterns like "X manages Y", "X follows Y", "X reports to Y", "X is located in Y", "X owns Y"
    patterns = [
        r"([A-Z][a-zA-Z\s]+?)\s+(manages|leads|directs|heads)\s+([A-Z][a-zA-Z\s]+)",
        r"([A-Z][a-zA-Z\s]+?)\s+(follows|adheres to|complies with)\s+([A-Z][a-zA-Z\s]+)",
        r"([A-Z][a-zA-Z\s]+?)\s+(is part of|belongs to|member of)\s+([A-Z][a-zA-Z\s]+)",
        r"([A-Z][a-zA-Z\s]+?)\s+(located in|based in|operates in)\s+([A-Z][a-zA-Z\s]+)",
        r"([A-Z][a-zA-Z\s]+?)\s+(reports to|works for)\s+([A-Z][a-zA-Z\s]+)",
    ]

    for pat in patterns:
        for match in re.finditer(pat, text, re.IGNORECASE):
            sub, pred, obj = match.groups()
            norm_sub = _normalize_entity(sub)
            norm_obj = _normalize_entity(obj.rstrip(". ,;"))
            norm_pred = _normalize_predicate(pred)
            if norm_sub and norm_obj and norm_sub.lower() != norm_obj.lower():
                triples.append({
                    "subject": norm_sub,
                    "predicate": norm_pred,
                    "object": norm_obj
                })

    return triples


async def _call_llm_for_triples(chunk_content: str, llm_client: Optional[Any] = None) -> List[Dict[str, str]]:
    """
    Query LLM (Groq, Gemini, OpenAI, or custom client) to extract entity triples.
    """
    prompt = (
        "Extract all entity relationships from the text below.\n"
        "Return ONLY a valid JSON array with this exact structure, no markdown:\n"
        '[{"subject": "Entity A", "predicate": "relationship_type", "object": "Entity B"}]\n'
        f"Text: {chunk_content}"
    )

    # 1. Custom or injected LLM client
    if llm_client is not None:
        try:
            if hasattr(llm_client, "chat") and hasattr(llm_client.chat, "completions"):
                model_name = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
                res = await llm_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": "You are a Knowledge Graph entity and relationship extractor. Output strictly JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0
                )
                raw_text = res.choices[0].message.content
                return _clean_and_parse_json(raw_text)

            elif callable(llm_client):
                res = await llm_client(prompt)
                return _clean_and_parse_json(str(res))

            elif hasattr(llm_client, "agenerate"):
                res = await llm_client.agenerate([prompt])
                return _clean_and_parse_json(res.generations[0][0].text)
        except Exception as e:
            logger.warning(f"Injected LLM client triple extraction failed: {e}")

    # 2. Groq Provider (openai/gpt-oss-120b / openai/gpt-oss-20b)
    if settings.GROQ_API_KEY:
        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": settings.LLM_MODEL if settings.LLM_MODEL.startswith("openai/gpt-oss-") else "openai/gpt-oss-120b",
                "messages": [
                    {"role": "system", "content": "You are a Knowledge Graph extractor. Output only a raw JSON array of subject-predicate-object triples."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.0
            }
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                resp = await http_client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    parsed = _clean_and_parse_json(content)
                    if parsed:
                        return parsed
        except Exception as groq_err:
            logger.warning(f"Groq triple extraction call failed: {groq_err}")

    # 3. Gemini Provider (model selected through LLM_MODEL)
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
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = _clean_and_parse_json(text_part)
                        if parsed:
                            return parsed
        except Exception as gemini_err:
            logger.warning(f"Gemini triple extraction call failed: {gemini_err}")

    # 4. OpenAI Provider
    if settings.OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            res = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a Knowledge Graph extractor. Output only a raw JSON array of triples."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            parsed = _clean_and_parse_json(res.choices[0].message.content)
            if parsed:
                return parsed
        except Exception as oai_err:
            logger.warning(f"OpenAI triple extraction call failed: {oai_err}")

    # 5. Deterministic heuristic fallback
    return _heuristic_triple_extractor(chunk_content)


async def extract_triples(
    chunk_id: str,
    chunk_content: str,
    tenant_id: str,
    llm_client: Optional[Any] = None,
    db: Optional[Any] = None
) -> List[Dict[str, str]]:
    """
    Extract entity relationships from a text chunk and persist valid triples into `entity_triples`.

    Args:
        chunk_id: UUID of the source chunk in the `chunks` table.
        chunk_content: Text content of the chunk.
        tenant_id: UUID of the tenant for multi-tenant isolation.
        llm_client: Optional LLM client instance (e.g. AsyncOpenAI, Groq, custom async callable).
        db: Optional database connection (asyncpg Connection/Pool or SQLAlchemy session).

    Returns:
        List[Dict[str, str]]: The extracted and persisted triples.
    """
    if not chunk_content or not chunk_content.strip():
        return []

    # Step 1: Pre-filter chunks using spaCy NER to avoid unnecessary LLM calls
    if not has_named_entities(chunk_content):
        logger.debug(f"Chunk {chunk_id} skipped: No named entities found by pre-filter.")
        return []

    # Step 2: Extract triples via LLM (or fallback)
    triples = await _call_llm_for_triples(chunk_content, llm_client=llm_client)
    if not triples:
        logger.debug(f"No triples extracted for chunk {chunk_id}.")
        return []

    # Step 3: Deduplicate triples within the chunk
    unique_triples: List[Dict[str, str]] = []
    seen = set()
    for t in triples:
        key = (t["subject"].lower(), t["predicate"].lower(), t["object"].lower())
        if key not in seen:
            seen.add(key)
            unique_triples.append(t)

    # Step 4: Bulk insert into PostgreSQL `entity_triples` table
    records = [
        (tenant_id, chunk_id, t["subject"], t["predicate"], t["object"])
        for t in unique_triples
    ]

    async def _insert_records(conn: Any) -> None:
        if hasattr(conn, "executemany"):
            await conn.executemany(
                """
                INSERT INTO entity_triples (
                    tenant_id, source_chunk_id, subject, predicate, object, created_at
                ) VALUES (
                    $1::uuid, $2::uuid, $3, $4, $5, NOW()
                );
                """,
                records
            )
        elif hasattr(conn, "execute"):
            for r in records:
                await conn.execute(
                    """
                    INSERT INTO entity_triples (
                        tenant_id, source_chunk_id, subject, predicate, object, created_at
                    ) VALUES (
                        $1::uuid, $2::uuid, $3, $4, $5, NOW()
                    );
                    """,
                    *r
                )

    try:
        if db is not None:
            await _insert_records(db)
        else:
            conn = await asyncpg.connect(_get_raw_db_url(settings.DATABASE_URL))
            try:
                await _insert_records(conn)
            finally:
                await conn.close()

        logger.info(f"Persisted {len(unique_triples)} triples for chunk {chunk_id} (tenant={tenant_id})")
    except Exception as db_err:
        logger.error(f"Failed to persist entity triples to DB for chunk {chunk_id}: {db_err}", exc_info=True)

    return unique_triples
