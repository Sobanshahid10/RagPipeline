"""
Agentic Query Layer Module (Day 7).

Provides Semantic Caching, HyDE, Multi-Query Expansion, Strategy Routing,
and Pre-Retrieval Orchestration.
"""

from app.agentic.cache import SemanticCache
from app.agentic.expander import expand_query
from app.agentic.hyde import generate_hyde_embedding
from app.agentic.pipeline import process_query
from app.agentic.router import (
    ROUTE_ANALYTICAL_SQL,
    ROUTE_FACTUAL_VECTOR,
    ROUTE_GREETING_DIRECT,
    ROUTE_MULTI_HOP_GRAPH,
    classify_route,
)

__all__ = [
    "SemanticCache",
    "generate_hyde_embedding",
    "expand_query",
    "classify_route",
    "process_query",
    "ROUTE_FACTUAL_VECTOR",
    "ROUTE_MULTI_HOP_GRAPH",
    "ROUTE_ANALYTICAL_SQL",
    "ROUTE_GREETING_DIRECT",
]
