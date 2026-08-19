"""
Unit and Integration Tests for GraphRAG Knowledge Graph Extraction and Multi-Hop Traversal (Day 5).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ingestion.graph_extractor import (
    extract_triples,
    has_named_entities,
    _normalize_entity,
    _normalize_predicate,
    _clean_and_parse_json
)
from app.retrieval.graph_search import (
    graph_search,
    extract_query_entities
)


@pytest.mark.asyncio
async def test_triple_extraction_and_normalization():
    """
    Test 1: Triple extraction from a sample chunk.
    Verifies:
    - Named entity pre-filter detection
    - LLM JSON parsing and markdown code fence stripping
    - Entity normalization (Title Case, extra whitespace trimming)
    - Database insertion with tenant isolation
    """
    # 1. Test pre-filter
    assert has_named_entities("Alice manages the London Office.") is True
    assert has_named_entities("   ") is False

    # 2. Test JSON parsing and normalization
    raw_llm_json_output = """
    ```json
    [
        {"subject": " alice ", "predicate": "MANAGES", "object": " london office "},
        {"subject": "London Office", "predicate": "follows", "object": "uk leave policy"}
    ]
    ```
    """
    triples = _clean_and_parse_json(raw_llm_json_output)
    assert len(triples) == 2
    assert triples[0]["subject"] == "Alice"
    assert triples[0]["predicate"] == "manages"
    assert triples[0]["object"] == "London Office"
    assert triples[1]["object"] == "UK Leave Policy"

    # 3. Test extract_triples async execution with DB mock
    mock_db = AsyncMock()
    mock_llm_client = AsyncMock()
    mock_llm_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=raw_llm_json_output))]
    )

    chunk_id = "11111111-1111-1111-1111-111111111111"
    tenant_id = "00000000-0000-0000-0000-000000000001"
    content = "Alice manages the London Office. London Office follows UK Leave Policy."

    extracted = await extract_triples(
        chunk_id=chunk_id,
        chunk_content=content,
        tenant_id=tenant_id,
        llm_client=mock_llm_client,
        db=mock_db
    )

    assert len(extracted) == 2
    assert mock_db.executemany.called
    call_args = mock_db.executemany.call_args
    sql_query, records = call_args[0]
    assert "INSERT INTO entity_triples" in sql_query
    assert len(records) == 2
    assert records[0] == (tenant_id, chunk_id, "Alice", "manages", "London Office")


@pytest.mark.asyncio
async def test_multi_hop_graph_traversal():
    """
    Test 2: Graph traversal with a multi-hop query.
    Scenario:
    - Chunk 1: "Alice manages the London Office."
    - Chunk 2: "The London Office follows the UK Leave Policy."
    - Query: "What policy does Alice's team follow?"
    - Expected Result: Recursive CTE traverses Alice -> London Office -> UK Leave Policy and returns Chunk 2.
    """
    query = "What policy does Alice's team follow?"
    tenant_id = "00000000-0000-0000-0000-000000000001"

    # Verify query entity extraction extracts 'Alice'
    extracted_entities = extract_query_entities(query)
    assert any("alice" in e.lower() for e in extracted_entities)

    # Mock DB connection returning the traversed multi-hop chunks
    mock_db_conn = AsyncMock()

    # Simulate DB returning Chunk 2 (UK Leave Policy) and Chunk 1 from the recursive CTE
    mock_db_conn.fetch.return_value = [
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "document_id": "doc-001",
            "content": "The London Office follows the UK Leave Policy.",
            "contextual_summary": "HR Policy Overview",
            "page_number": 3,
            "bounding_box": json.dumps({"ymin": 0.1, "xmin": 0.1, "ymax": 0.5, "xmax": 0.9})
        },
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "document_id": "doc-001",
            "content": "Alice manages the London Office.",
            "contextual_summary": "Organization Structure",
            "page_number": 1,
            "bounding_box": json.dumps({"ymin": 0.0, "xmin": 0.0, "ymax": 0.2, "xmax": 0.8})
        }
    ]

    results = await graph_search(
        query=query,
        tenant_id=tenant_id,
        max_hops=3,
        top_k=5,
        db_conn=mock_db_conn
    )

    assert len(results) == 2
    # Verify the UK Leave Policy chunk is retrieved
    policy_chunk = next((r for r in results if "uk leave policy" in r["content"].lower()), None)
    assert policy_chunk is not None
    assert policy_chunk["id"] == "22222222-2222-2222-2222-222222222222"
    assert policy_chunk["page_number"] == 3
    assert policy_chunk["bounding_box"]["ymin"] == 0.1
    assert policy_chunk["source"] == "graph"

    # Verify recursive CTE was executed with tenant isolation
    assert mock_db_conn.fetch.called
    executed_sql, pattern_arg, tenant_arg, hops_arg, limit_arg = mock_db_conn.fetch.call_args[0]
    assert "WITH RECURSIVE graph_traverse" in executed_sql
    assert tenant_arg == tenant_id
    assert hops_arg == 3


@pytest.mark.asyncio
async def test_graph_search_deduplication():
    """
    Test 3: Deduplication of results across multiple entities in a single query.
    When a query contains multiple entities ("Alice", "London Office"), each entity may traverse
    to overlapping chunks. The search module must deduplicate results by chunk ID.
    """
    query = "Does Alice or London Office follow the UK Leave Policy?"
    tenant_id = "00000000-0000-0000-0000-000000000001"

    mock_db_conn = AsyncMock()

    # The mock returns the same chunk ID on successive queries for different entities
    shared_chunk = {
        "id": "22222222-2222-2222-2222-222222222222",
        "document_id": "doc-001",
        "content": "The London Office follows the UK Leave Policy.",
        "contextual_summary": "HR Policy Overview",
        "page_number": 3,
        "bounding_box": {}
    }
    mock_db_conn.fetch.return_value = [shared_chunk]

    results = await graph_search(
        query=query,
        tenant_id=tenant_id,
        max_hops=3,
        top_k=10,
        db_conn=mock_db_conn
    )

    # Should only contain 1 unique chunk despite multiple entity CTE matches
    assert len(results) == 1
    assert results[0]["id"] == "22222222-2222-2222-2222-222222222222"
    # Ensure fetch was called for each extracted entity
    assert mock_db_conn.fetch.call_count >= 2
