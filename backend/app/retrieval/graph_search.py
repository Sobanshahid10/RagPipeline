"""
Knowledge Graph Multi-Hop Traversal Search Module (GraphRAG Retrieval).

Executes multi-hop relational retrieval across entity triples stored in PostgreSQL:
1. Extracts named entities and core concept terms from natural language queries.
2. Executes recursive CTE graph traversals (`WITH RECURSIVE graph_traverse`) up to `max_hops` deep.
3. Merges and deduplicates retrieved chunks across multiple query entities.
4. Returns standardized chunk dictionaries compatible with Vector & BM25 search outputs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.db.tenant import tenant_connection

logger = logging.getLogger(__name__)

# Cached spaCy NLP instance
_nlp_spacy = None


def _get_spacy_nlp():
    """Lazy load spaCy NLP pipeline with fallback."""
    global _nlp_spacy
    if _nlp_spacy is None:
        try:
            import spacy

            try:
                _nlp_spacy = spacy.load("en_core_web_sm")
            except Exception:
                _nlp_spacy = spacy.blank("en")
                if "sentencizer" not in _nlp_spacy.pipe_names:
                    _nlp_spacy.add_pipe("sentencizer")
        except Exception as e:
            logger.warning(f"Failed to initialize spaCy in graph_search: {e}")
            _nlp_spacy = None
    return _nlp_spacy


def _get_raw_db_url(url: str) -> str:
    """Convert SQLAlchemy asyncpg URL to standard PostgreSQL connection URL."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://")
    return url


def extract_query_entities(query: str) -> List[str]:
    """
    Extract key entity candidate strings from a user query using spaCy NER and linguistic patterns.
    Handles possessives ('s), question wrappers, and multi-word proper nouns.
    """
    cleaned = query.strip()
    if not cleaned:
        return []

    entities: List[str] = []
    seen = set()

    def _add_entity(ent: str):
        # Remove trailing punctuation and possessives ('s, ')
        candidate = re.sub(r"['’]s?\b", "", ent).strip(" ?.,!;:'\"")
        if candidate and len(candidate) > 1 and candidate.lower() not in seen:
            seen.add(candidate.lower())
            entities.append(candidate)

    # 1. Use spaCy NER if available
    nlp = _get_spacy_nlp()
    if nlp is not None:
        try:
            doc = nlp(cleaned)
            for ent in doc.ents:
                _add_entity(ent.text)

            # Also inspect noun chunks and proper nouns (e.g. "Alice's team" -> "Alice")
            for token in doc:
                if token.pos_ == "PROPN":
                    _add_entity(token.text)
        except Exception as err:
            logger.debug(f"spaCy query entity extraction error: {err}")

    # 2. Regex fallback: Look for capitalized names, acronyms, or quoted terms
    if not entities:
        # Check for quoted phrases
        quoted = re.findall(r'["\']([^"\']+)["\']', cleaned)
        for q in quoted:
            _add_entity(q)

        # Check for capitalized sequences (e.g., "Alice", "London Office", "UK Leave Policy")
        cap_matches = re.findall(
            r"\b[A-Z][a-zA-Z0-9_-]+(?:\s+[A-Z][a-zA-Z0-9_-]+)*\b", cleaned
        )
        for match in cap_matches:
            _add_entity(match)

        # Stop words filter for common question words that might be capitalized at sentence start
        stop_starters = {
            "what",
            "where",
            "who",
            "which",
            "how",
            "when",
            "why",
            "tell",
            "explain",
            "describe",
            "find",
            "is",
            "are",
            "does",
            "do",
        }
        filtered = [e for e in entities if e.lower() not in stop_starters]
        if filtered:
            entities = filtered

    # 3. Final fallback: If no entities could be identified, use significant words (len >= 3)
    if not entities:
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", cleaned)
        stop_words = {
            "what",
            "where",
            "who",
            "which",
            "how",
            "when",
            "why",
            "team",
            "policy",
            "does",
            "the",
            "and",
            "for",
            "with",
            "from",
        }
        for w in words:
            if w.lower() not in stop_words:
                _add_entity(w)

    return entities


async def graph_search(
    query: str,
    tenant_id: str,
    max_hops: int = 3,
    top_k: int = 15,
    db_conn: Optional[Any] = None,
    document_ids: Optional[list[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Perform multi-hop relational GraphRAG search over `entity_triples` and `chunks`.

    Args:
        query: Natural language query string.
        tenant_id: UUID of the tenant for multi-tenant isolation.
        max_hops: Maximum recursion depth for graph traversal (defaults to 3).
        top_k: Maximum number of distinct chunks to return.
        db_conn: Optional existing database connection (asyncpg or mock).

    Returns:
        List[Dict[str, Any]]: Standardized chunk dicts sorted by relevance / hop proximity.
    """
    if not query or not query.strip():
        return []

    # Step 1: Extract entity entrypoints from the query
    entities = extract_query_entities(query)[:12]
    if not entities:
        logger.debug(f"No entities extracted from query: '{query}'")
        return []

    logger.debug(f"Extracted entities for graph search: {entities}")

    # Recursive CTE Query pattern matching exact specification
    traversal_query = """
    WITH RECURSIVE eligible_triples AS MATERIALIZED (
        SELECT e.subject,e.predicate,e.object,e.source_chunk_id
        FROM entity_triples e
        JOIN chunks c ON c.id=e.source_chunk_id AND c.tenant_id=$2::uuid
        JOIN documents d ON d.id=c.document_id AND d.tenant_id=$2::uuid
        WHERE e.tenant_id=$2::uuid AND d.status='indexed'
          AND ($5::uuid[] IS NULL OR d.id=ANY($5::uuid[]))
    ), graph_traverse AS (
        SELECT subject, predicate, object, source_chunk_id, 1 AS depth
        FROM eligible_triples
        WHERE subject ILIKE $1 OR object ILIKE $1

        UNION

        SELECT e.subject, e.predicate, e.object, e.source_chunk_id, g.depth + 1
        FROM eligible_triples e
        JOIN graph_traverse g ON e.subject = g.object
        WHERE g.depth < $3
    )
    SELECT c.id, c.document_id, c.content, c.contextual_summary, c.bounding_box,
                    c.page_number, d.filename AS source_filename
    FROM graph_traverse gt
    JOIN chunks c ON c.id = gt.source_chunk_id
    JOIN documents d ON d.id = c.document_id
    WHERE c.tenant_id=$2::uuid AND d.tenant_id=$2::uuid AND d.status='indexed'
      AND ($5::uuid[] IS NULL OR d.id=ANY($5::uuid[]))
    GROUP BY c.id,d.filename
    ORDER BY MIN(gt.depth), c.id
    LIMIT $4;
    """

    all_results: Dict[str, Dict[str, Any]] = {}

    async def _execute_for_conn(conn: Any):
        for ent in entities:
            search_pattern = f"%{ent}%"
            rows = await conn.fetch(
                traversal_query,
                search_pattern,
                tenant_id,
                max(1, min(max_hops, 4)),
                max(1, min(top_k, 50)),
                document_ids,
            )

            for r in rows:
                chunk_id = str(r["id"])
                if chunk_id not in all_results:
                    bbox = (
                        r.get("bounding_box")
                        if hasattr(r, "get")
                        else r["bounding_box"]
                    )
                    if isinstance(bbox, str):
                        try:
                            bbox = json.loads(bbox)
                        except Exception:
                            bbox = {}

                    doc_id = (
                        str(r.get("document_id", ""))
                        if hasattr(r, "get")
                        else (str(r["document_id"]) if "document_id" in r else "")
                    )
                    summary = (
                        r.get("contextual_summary")
                        if hasattr(r, "get")
                        else r["contextual_summary"]
                    ) or ""
                    page_num = (
                        r.get("page_number") if hasattr(r, "get") else r["page_number"]
                    ) or 1

                    all_results[chunk_id] = {
                        "id": chunk_id,
                        "document_id": doc_id,
                        "content": r["content"],
                        "contextual_summary": summary,
                        "page_number": page_num,
                        "bounding_box": bbox or {},
                        "source_filename": (
                            r.get("source_filename", "") if hasattr(r, "get") else ""
                        ),
                        "graph_score": 1.0,  # Standard placeholder score for graph hits
                        "source": "graph",
                    }

    if db_conn is not None:
        await _execute_for_conn(db_conn)
    else:
        async with tenant_connection(tenant_id) as conn:
            await _execute_for_conn(conn)

    # Step 3: Deduplicate and trim to top_k
    final_results = list(all_results.values())[:top_k]
    return final_results
