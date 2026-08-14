# 12-Day Production RAG Pipeline Implementation Plan
### Project: Production RAG & Evaluation Engine (RagPipeline)
### Repository: https://github.com/Sobanshahid10/RagPipeline

> **Goal**: Build a complete, production-grade Retrieval-Augmented Generation (RAG) platform with Tri-Hybrid Search (BM25 + pgvector + GraphRAG), ColBERT Reranking, Vision Layout Parsing, Real-Time SSE Streaming, Bounding-Box PDF Citations, Agentic Query Routing, OpenTelemetry Observability, RAGAS Evaluation CI/CD, and dbt Analytics — from scratch to a fully deployed, enterprise-ready system.

---

## Overview Timeline

| Day | Focus Area | Status |
|:---:|:---|:---:|
| 1 | Foundation: Docker, PostgreSQL, Redis, Schema, RLS | |
| 2 | Authentication System: JWT, Multi-Tenant, RLS Policies | |
| 3 | Document Ingestion: Vision Parsing, PII Masking, Chunking | |
| 4 | Vector Indexing: pgvector HNSW, BM25 TSVector, Celery Workers | |
| 5 | Knowledge Graph: GraphRAG Entity Extraction & Triple Storage | |
| 6 | Retrieval Engine: RRF Fusion, ColBERT ONNX Reranker, Contextual Compression | |
| 7 | Agentic Query Layer: HyDE, Query Expansion, Redis Semantic Cache | |
| 8 | LLM Generation: Structured Streaming, Bounding-Box Citations, SSE | |
| 9 | Next.js Frontend: Streaming Chat UI, PDF Viewer, Citation Highlighting | |
| 10 | Observability: OpenTelemetry, LangFuse Tracing, Admin Dashboard | |
| 11 | RAGAS CI/CD Eval: Golden Dataset, Tiered GitHub Actions, Hard-Negative Mining | |
| 12 | dbt Analytics, Load Testing, Security Hardening & Production Deploy | |

---

## Day 1 — Foundation: Infrastructure, Docker, PostgreSQL Schema, Redis

### Learning Objectives
- Understand how to compose multi-service backends with Docker Compose
- Learn pgvector extension setup and vector index types (HNSW vs IVFFlat)
- Understand Row-Level Security (RLS) concepts in PostgreSQL
- Grasp Redis connection pooling and async patterns with FastAPI

### Implementation Tasks

#### 1.1 Project Scaffolding
```
RagPipeline/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── ingestion/
│   │   ├── retrieval/
│   │   ├── generation/
│   │   ├── evaluation/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── core/
│   │   └── main.py
│   ├── tests/
│   ├── db/
│   │   └── init.sql
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/          # Next.js 14 App Router
├── dbt/               # dbt Analytics Models
├── .github/
│   └── workflows/
├── docker-compose.yml
└── README.md
```

#### 1.2 Docker Compose Setup
- PostgreSQL 16 with pgvector, pg_trgm, uuid-ossp extensions
- Redis 7 Alpine for caching and Celery message broker
- FastAPI backend container
- Celery worker container (separate from API)
- Next.js frontend container

#### 1.3 Complete PostgreSQL Schema
- documents table: file metadata, doc_hash SHA-256 idempotency
- chunks table: VECTOR(1536) embedding, TSVECTOR sparse index, bounding_box JSONB
- entity_triples table: GraphRAG subject-predicate-object store
- query_interactions table: latency, token counts, user feedback
- eval_scores table: per-query RAGAS metric storage
- HNSW index with m=16, ef_construction=64 on embedding column
- GIN index on sparse_tsv for BM25 full-text search
- RLS enabled on all tenant-scoped tables

#### 1.4 FastAPI Application Bootstrap
- Async SQLAlchemy engine with asyncpg driver
- Redis async connection pool
- Health check endpoint: GET /health
- System info endpoint: GET /api/v1/info
- CORS middleware for Next.js origin

### Day 1 Outcomes
- Docker Compose starts all services with docker-compose up
- All 6 tables created in PostgreSQL with proper indexes
- FastAPI returns 200 on /health
- pgvector extension confirmed active

---

## Day 2 — Authentication: JWT Auth, Multi-Tenancy, RBAC & RLS Enforcement

### Learning Objectives
- Understand JWT access token structure (header.payload.signature)
- Learn PostgreSQL Row-Level Security policy definitions
- Understand multi-tenant SaaS architecture patterns
- Implement async middleware for authentication context propagation

### Implementation Tasks

#### 2.1 User & Tenant Models
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id),
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    roles TEXT[] DEFAULT '{viewer}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 2.2 JWT Authentication Flow
- POST /api/v1/auth/register → Hash password with bcrypt, create user
- POST /api/v1/auth/login → Verify password, return JWT with tenant_id, user_id, roles
- GET /api/v1/auth/me → Decode JWT, return user profile
- JWT payload: { sub: user_id, tenant_id: uuid, roles: [], exp: timestamp }
- Token expiry: 24 hours (configurable via env)

#### 2.3 PostgreSQL RLS Policy Implementation
```sql
-- Automatically filter all queries to current tenant
CREATE POLICY tenant_isolation ON chunks
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- FastAPI sets this at query time per request session
```

#### 2.4 FastAPI Auth Middleware
- get_current_user dependency from Bearer token
- Request-scoped tenant ID injection into PostgreSQL session variable
- Role-Based Access Control: admin, editor, viewer roles
- Rate limiting: 60 requests/minute per user

### Day 2 Outcomes
- Register and login endpoints returning valid JWTs
- Protected endpoints return 401 without Bearer token
- RLS policies verified: User A cannot access User B's documents
- Unit tests: tests/test_auth.py with 5+ test cases

---

## Day 3 — Document Ingestion: Vision Parsing, PII Masking & Semantic Chunking

### Learning Objectives
- Understand layout-aware document parsing vs plain text extraction
- Learn why naive token chunking destroys semantic continuity
- Understand PII detection patterns and entity anonymization
- Learn Anthropic's Contextual Retrieval technique for embedding enrichment

### Implementation Tasks

#### 3.1 Upload API Endpoint
```python
# POST /api/v1/documents/upload
# Accepts: multipart/form-data (PDF, DOCX, TXT, max 50MB)
# Returns: document_id, status="processing"
# SHA-256 hash for idempotency — skip re-upload of identical files
```

#### 3.2 Layout-Aware Vision Parsing (Docling)
```python
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
result = converter.convert(file_path)
# Outputs: structured markdown preserving tables, headers, multi-column
# Each page → page_number, bounding_box coordinates, text content
```

#### 3.3 Microsoft Presidio PII Masking
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
# Detects: SSN, Credit Cards, Email, Phone, API Keys, Person Names
# Replaces with: <PERSON>, <EMAIL_ADDRESS>, <PHONE_NUMBER>, etc.
# Run on every page text before chunking and embedding
```

#### 3.4 Anthropic Contextual Summary Injection
- Generate 2-sentence global document summary via LLM
- Prepend to every chunk text before embedding
- Prevents orphaned chunks from losing global document context
- Dramatically improves vector retrieval accuracy for ambiguous queries

#### 3.5 Semantic Embedding-Shift Chunking
- Split into sentences using spaCy or regex boundaries
- Compute sentence embeddings with all-MiniLM-L6-v2
- Measure cosine distance between consecutive sentences
- Create chunk boundary when delta_similarity > 0.4 (adaptive threshold)
- Overlap: carry last 2 sentences of previous chunk into next
- Max chunk: 512 tokens; min: 64 tokens

#### 3.6 Celery Async Worker
- Task: process_document(document_id, tenant_id)
- Pipeline: Parse → PII Mask → Summarize → Chunk → Embed → Index
- Update document status at each step: pending → processing → indexed / failed
- Retry failed tasks up to 3 times with exponential backoff

### Day 3 Outcomes
- Upload endpoint returns document_id immediately (async processing)
- Celery worker processes PDF end-to-end in background
- Chunks stored in DB with bounding_box JSON, contextual_summary, page_number
- PII correctly masked in stored chunk content
- Unit tests: tests/test_ingestion.py

---

## Day 4 — Vector Indexing: pgvector HNSW, BM25 TSVector & Celery Optimization

### Learning Objectives
- Understand HNSW index parameters (m, ef_construction, ef_search)
- Learn BM25 Okapi TF-IDF scoring and PostgreSQL tsvector internals
- Understand embedding model selection trade-offs
- Learn Celery task chaining and priority queues

### Implementation Tasks

#### 4.1 Dense Vector Embedding Generation
```python
# Option A: OpenAI text-embedding-3-small → 1536 dims
# Option B: sentence-transformers/all-mpnet-base-v2 → 768 dims, free/local
async def generate_embedding(text: str) -> list[float]:
    # Batch embedding: 50 chunks per API call
    # Cache in Redis: key=sha256(text), TTL=30 days
```

#### 4.2 HNSW Index Optimization
```sql
CREATE INDEX idx_chunks_hnsw ON chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- At query time:
SET hnsw.ef_search = 100; -- Higher = better recall, slower
```

#### 4.3 BM25 Sparse Index Generation
```sql
UPDATE chunks
SET sparse_tsv = to_tsvector('english', content)
WHERE sparse_tsv IS NULL;

-- BM25 Query:
SELECT id, ts_rank_cd(sparse_tsv, query) AS bm25_score
FROM chunks, plainto_tsquery('english', $1) query
WHERE sparse_tsv @@ query AND tenant_id = $2
ORDER BY bm25_score DESC LIMIT 20;
```

#### 4.4 Celery Optimization
- high_priority queue: document ingestion tasks
- low_priority queue: batch re-indexing and eval tasks
- Concurrency: 4 workers per queue
- Flower web UI monitoring on port 5555
- Dead Letter Queue: failed tasks logged to failed_tasks table

### Day 4 Outcomes
- Chunks with embeddings stored and HNSW index verified
- BM25 tsvector populated and GIN index confirmed
- Celery Flower dashboard at localhost:5555
- Embedding cache hitting on re-upload test
- GET /api/v1/documents/{id} returns status and chunk count

---

## Day 5 — Knowledge Graph: GraphRAG Entity Extraction & Triple Storage

### Learning Objectives
- Understand Knowledge Graph concepts: nodes, edges, triples, traversal
- Learn why vector search fails at multi-hop relational queries
- Understand Named Entity Recognition (NER) pipelines
- Learn graph traversal query patterns with recursive CTEs

### Implementation Tasks

#### 5.1 Entity & Relationship Extraction
```python
EXTRACTION_PROMPT = """
Extract entities and relationships from the following text.
Return as JSON array: [{"subject": "", "predicate": "", "object": ""}]
Text: {chunk_content}
"""
# Example output:
# [{"subject": "John Smith", "predicate": "works_in", "object": "London Office"},
#  {"subject": "London Office", "predicate": "follows_policy", "object": "UK Leave Policy"}]
```

#### 5.2 Recursive CTE Graph Traversal
```sql
WITH RECURSIVE graph_traverse AS (
    SELECT subject, predicate, object, source_chunk_id, 1 AS depth
    FROM entity_triples
    WHERE subject ILIKE $1 AND tenant_id = $2

    UNION ALL

    SELECT e.subject, e.predicate, e.object, e.source_chunk_id, g.depth + 1
    FROM entity_triples e
    JOIN graph_traverse g ON e.subject = g.object
    WHERE g.depth < 3 AND e.tenant_id = $2
)
SELECT DISTINCT source_chunk_id FROM graph_traverse;
```

#### 5.3 Multi-Hop Query Example
- Query: "What leave policy applies to engineers hired before 2022 in London?"
- Entity extraction: London, engineers, 2022
- Graph traversal: London Office → follows_policy → UK Leave Policy
- Fetches relevant policy chunk via relationship traversal

### Day 5 Outcomes
- Entity extraction runs automatically during chunk ingestion
- Recursive CTE graph traversal returns relevant chunks for relational queries
- /api/v1/retrieval/graph?query=... endpoint working
- Unit tests: tests/test_graph.py

---

## Day 6 — Retrieval Engine: RRF Fusion, ColBERT ONNX Reranker & Contextual Compression

### Learning Objectives
- Deeply understand RRF fusion mathematics
- Understand bi-encoder vs cross-encoder vs late-interaction trade-offs
- Learn ONNX model export and Runtime execution provider configuration
- Understand contextual compression and "Lost in the Middle" LLM failure

### Implementation Tasks

#### 6.1 Tri-Hybrid Parallel Retrieval
```python
import asyncio

async def tri_hybrid_retrieve(query, embedding, tenant_id):
    bm25_task = asyncio.create_task(bm25_search(query, tenant_id, top_k=20))
    vector_task = asyncio.create_task(vector_search(embedding, tenant_id, top_k=20))
    graph_task = asyncio.create_task(graph_retrieval(query, tenant_id, top_k=15))

    bm25, vector, graph = await asyncio.gather(bm25_task, vector_task, graph_task)
    return {"bm25": bm25, "vector": vector, "graph": graph}
```

#### 6.2 Reciprocal Rank Fusion (RRF)
```python
# RRF(d) = sum( 1 / (k + rank_i(d)) ), k=60
def reciprocal_rank_fusion(result_sets: dict, k: int = 60) -> list:
    scores = {}
    for method, results in result_sets.items():
        for rank, chunk in enumerate(results):
            cid = str(chunk["id"])
            scores[cid] = scores.get(cid, 0) + (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

#### 6.3 ONNX-Accelerated Cross-Encoder Reranker
```python
from optimum.onnxruntime import ORTModelForSequenceClassification
# Export bge-reranker-large or ms-marco-MiniLM-L-6-v2 to ONNX
# Runtime inference: 3-5x faster than PyTorch CPU
# Target: rerank top-40 candidates in <35ms
```

#### 6.4 ColBERT Late Interaction Scoring
```
S(q,d) = sum_i( max_j( E_q_i · E_d_j^T ) )
Token-level MaxSim: superior to bi-encoder for precision retrieval
```

#### 6.5 LongLLMLingua Contextual Compression
```python
from llmlingua import PromptCompressor
# Compress top-5 chunks before LLM injection
# 2000 tokens → 1000 tokens (50% compression)
# Prevents "Lost in the Middle" LLM degradation
```

### Day 6 Outcomes
- Full tri-hybrid retrieval working end-to-end in <150ms
- RRF fusion outperforming single-source retrieval in precision tests
- ONNX reranker serving in <35ms verified
- LLMLingua compressing context by 40-50%
- Unit tests: tests/test_retrieval.py

---

## Day 7 — Agentic Query Layer: HyDE, Query Expansion & Redis Semantic Cache

### Learning Objectives
- Understand why user queries are sub-optimal for vector retrieval
- Learn HyDE (Hypothetical Document Embeddings) technique
- Understand semantic caching architecture and similarity thresholds
- Learn how to build an LLM-based intent classifier for query routing

### Implementation Tasks

#### 7.1 Redis Semantic Cache
```python
class SemanticCache:
    # Check cached query vectors via cosine similarity > 0.96 threshold
    # Cache hit response: <15ms
    # Cache store: hash=sha256(normalized_query), TTL=3600s
```

#### 7.2 Hypothetical Document Embedding (HyDE)
```python
async def hyde_generate(query: str) -> list[float]:
    hypothetical_doc = await llm.generate(
        f"Write a 2-paragraph excerpt answering: '{query}'"
    )
    # Embed the hypothetical document, not the raw question
    # The answer vector is closer to real document embeddings
    return await generate_embedding(hypothetical_doc)
```

#### 7.3 Multi-Query Expansion
```python
# Generate 3 semantic variations in parallel
# Run parallel vector lookups for each variation
# Merge via RRF for maximum coverage
```

#### 7.4 Agentic Strategy Classifier
```
FACTUAL_VECTOR   → Tri-hybrid vector search
MULTI_HOP_GRAPH  → GraphRAG + vector search
ANALYTICAL_SQL   → SQL query against dbt tables
GREETING_DIRECT  → Direct LLM response (skip retrieval)
```

#### 7.5 Full Query Pre-Processing Pipeline
```
Query → Cache Check → (MISS) → Classify Route → Expand + HyDE
     → Parallel Retrieval → RRF → Reranker → Compress → Generate
```

### Day 7 Outcomes
- Semantic cache returning responses in <15ms on similarity match
- HyDE improving retrieval recall verified by recall@k test
- Query router correctly classifying 5 test cases per category
- Full agentic pipeline: query → route → retrieve → compress in <200ms

---

## Day 8 — LLM Generation: Structured Streaming, Citations & SSE

### Learning Objectives
- Understand Server-Sent Events (SSE) protocol and streaming architecture
- Learn structured LLM output generation with JSON schema enforcement
- Understand citation grounding and hallucination mitigation techniques
- Learn how to include metadata in SSE token streams

### Implementation Tasks

#### 8.1 Grounding Prompt Template
```python
SYSTEM_PROMPT = """
You are a precise document Q&A assistant. Answer ONLY based on provided context.
If information is insufficient, say "I don't have enough information in the provided documents."
NEVER fabricate facts. Every factual claim must be sourced from context.
Citation format: [SOURCE:chunk_id:page_number]
"""
```

#### 8.2 Structured SSE Response Schema
```python
class SSEEvent(BaseModel):
    type: Literal["token", "citation", "metadata", "done", "error"]
    content: str | None = None

class CitationBlock(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    bounding_box: list[float]  # [ymin, xmin, ymax, xmax] normalized 0-1
    source_filename: str
    excerpt: str

class ResponseMetadata(BaseModel):
    total_tokens: int
    ttft_ms: int
    total_latency_ms: int
    route_used: str
    chunks_retrieved: int
```

#### 8.3 FastAPI SSE Streaming Endpoint
```python
@router.post("/api/v1/query")
async def query_endpoint(request: QueryRequest, current_user: User = Depends(get_current_user)):
    async def generate():
        async for chunk in llm.stream(prompt):
            yield {"data": SSEEvent(type="token", content=chunk).json()}
        for citation in extracted_citations:
            yield {"data": SSEEvent(type="citation", citation=citation).json()}
        yield {"data": SSEEvent(type="done", metadata=build_metadata(...)).json()}
    return EventSourceResponse(generate())
```

#### 8.4 User Feedback Endpoint
```python
# POST /api/v1/query/{interaction_id}/feedback
# Body: {"feedback": 1}  # 1=thumbs up, -1=thumbs down
```

### Day 8 Outcomes
- SSE streaming endpoint responding with structured JSON events
- Citation blocks with bounding box coordinates in every response
- Interaction log confirming all queries stored to DB
- Hallucination guardrail refusing out-of-context questions
- Unit tests: tests/test_generation.py

---

## Day 9 — Next.js 14 Frontend: Streaming Chat UI, PDF Viewer & Citation Highlighting

### Learning Objectives
- Understand Next.js 14 App Router patterns (server vs client components)
- Learn ReadableStream and EventSource API for consuming SSE in browser
- Learn react-pdf rendering and canvas overlay for bounding box highlights
- Understand optimistic UI updates for streaming responses

### Implementation Tasks

#### 9.1 Application Structure
```
app/
├── layout.tsx          # Root layout with sidebar
├── page.tsx            # Landing/dashboard
├── (auth)/login/page.tsx
├── (auth)/register/page.tsx
├── chat/page.tsx       # Main streaming chat interface
├── documents/page.tsx  # Document library + upload
└── dashboard/page.tsx  # Analytics overview
```

#### 9.2 SSE Streaming Chat Component
```typescript
async function* streamSSEResponse(query: string, token: string) {
    const response = await fetch('/api/v1/query', {
        method: 'POST',
        body: JSON.stringify({ query }),
        headers: { Authorization: `Bearer ${token}` }
    });
    const reader = response.body!.getReader();
    // Decode chunks → parse SSEEvent JSON → yield events
}
```

#### 9.3 PDF Viewer with Bounding Box Highlights
```typescript
// react-pdf canvas + absolute-positioned highlight overlays
// coordinates from citation bounding_box [ymin, xmin, ymax, xmax]
// Animate highlight opacity: 0 → 0.4 on citation received
function BoundingBoxHighlight({ bbox, pageHeight, pageWidth }) {
    const [ymin, xmin, ymax, xmax] = bbox;
    // CSS absolute positioning with yellow translucent background
}
```

#### 9.4 Design System
- Dark mode by default with glassmorphism cards
- Color palette: #0A0A0F (bg), #6366F1 (indigo accent), #A78BFA (violet)
- Google Fonts: Inter (body) + Outfit (headings)
- Framer Motion for page transitions and chat message animations

### Day 9 Outcomes
- Chat UI streams LLM responses token-by-token in real time
- PDF viewer highlights cited text with yellow bounding boxes
- Document upload with real-time status progress bar
- Responsive layout on desktop and tablet
- Authentication flow: login → dashboard → chat

---

## Day 10 — Observability: OpenTelemetry, LangFuse Tracing & Admin Dashboard

### Learning Objectives
- Understand distributed tracing: spans, traces, context propagation
- Learn OpenTelemetry instrumentation patterns for FastAPI
- Understand time-to-first-token (TTFT) measurement importance
- Learn how to detect retrieval regressions using trace comparison

### Implementation Tasks

#### 10.1 OpenTelemetry Setup
```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
# Auto-instrument FastAPI, asyncpg, Redis
# Export traces to Jaeger or LangFuse collector
```

#### 10.2 Per-Component Span Instrumentation
```python
with tracer.start_as_current_span("query.cache_check") as span:
    span.set_attribute("cache.hit", cache_result is not None)

with tracer.start_as_current_span("retrieval.bm25"): ...
with tracer.start_as_current_span("retrieval.vector"): ...
with tracer.start_as_current_span("retrieval.graph"): ...
with tracer.start_as_current_span("retrieval.rrf_fusion"): ...
with tracer.start_as_current_span("retrieval.reranker"): ...
with tracer.start_as_current_span("query.generation") as span:
    span.set_attribute("llm.prompt_tokens", prompt_tokens)
    span.set_attribute("llm.ttft_ms", ttft_ms)
```

#### 10.3 Key Production Metrics

| Metric | Target | Alert Threshold |
|:---|:---:|:---:|
| Time to First Token (TTFT) | <200ms | >500ms |
| Full Response Latency | <2000ms | >5000ms |
| Cache Hit Rate | >30% | <10% |
| Retrieval Precision@5 | >0.80 | <0.65 |
| Hallucination Rate | <5% | >10% |
| Failed Ingestion Rate | <1% | >5% |

### Day 10 Outcomes
- Every query generates full OpenTelemetry trace visible in LangFuse
- TTFT and full latency tracked per interaction
- Admin dashboard displaying live system metrics and token costs
- Alert configured for TTFT > 500ms

---

## Day 11 — RAGAS CI/CD Eval: Golden Dataset, GitHub Actions & Hard-Negative Mining

### Learning Objectives
- Understand LLM-as-a-judge evaluation methodology and limitations
- Learn distinction between deterministic micro-evals and probabilistic macro-evals
- Understand hard-negative example mining for continuous dataset improvement
- Learn GitHub Actions workflow design for ML evaluation pipelines

### Implementation Tasks

#### 11.1 Golden Evaluation Dataset (200+ Q&A pairs)
```json
[
  {
    "id": "eval_001",
    "query": "What is the annual leave entitlement for full-time employees?",
    "ground_truth": "Full-time employees receive 25 days of annual leave per year.",
    "relevant_chunk_ids": ["chunk_abc123"],
    "difficulty": "easy",
    "category": "HR_Policy"
  }
]
// 4 categories: HR_Policy, Technical_Docs, Financial_Reports, Legal_Contracts
// 3 difficulty levels: easy, medium, hard (multi-hop)
```

#### 11.2 RAGAS Evaluation Metrics
- **Faithfulness**: Claims in answer verified against context (target >0.90)
- **Answer Relevancy**: Answer addresses the actual question (target >0.85)
- **Context Precision**: Relevant chunks in top positions (target >0.80)
- **Context Recall**: All relevant chunks retrieved (target >0.75)

#### 11.3 Tiered GitHub Actions CI/CD

**Fast PR Check (runs in <60 seconds):**
```yaml
name: Fast Eval - PR Check
on: [pull_request]
jobs:
  fast-eval:
    steps:
      - run: pytest tests/ -v
      - run: python scripts/eval_recall.py --min-recall 0.75
      - run: python scripts/eval_latency.py --max-ttft-ms 500
      - run: python scripts/eval_citations.py
```

**Nightly Full RAGAS Eval (runs at 2 AM UTC):**
```yaml
name: Nightly RAGAS Full Eval
on:
  schedule:
    - cron: '0 2 * * *'
jobs:
  ragas-eval:
    steps:
      - run: python scripts/run_ragas_eval.py --dataset golden_dataset.json
      - run: python scripts/assert_threshold.py --metric faithfulness --min 0.90
      - run: python scripts/upload_eval_results.py
```

#### 11.4 Hard-Negative Mining Automation
```python
# Runs every 6 hours via Celery periodic task
async def hard_negative_mining_worker():
    # 1. Fetch interactions with user_feedback = -1 (thumbs down)
    # 2. LLM diagnoses retrieval/generation failure
    # 3. LLM generates corrected ground truth
    # 4. Append to golden_dataset.json with failure_mode tag
    #    Categories: retrieval_fail, hallucination, context_loss
```

### Day 11 Outcomes
- 200+ entry golden dataset covering 4 categories and 3 difficulty levels
- Fast CI running on every PR in <60 seconds
- Nightly RAGAS eval storing results to eval_scores table
- Hard-negative miner running on 6-hour cron schedule

---

## Day 12 — dbt Analytics, Load Testing, Security Hardening & Production Deploy

### Learning Objectives
- Understand dbt model DAG (Staging → Intermediate → Fact → Report layers)
- Learn load testing methodology: concurrent users, RPS, p95/p99 latency
- Understand production security checklist
- Learn Docker Compose production configuration

### Implementation Tasks

#### 12.1 dbt Analytics Models
```
dbt/models/
├── staging/
│   ├── stg_query_interactions.sql   # Clean raw query logs
│   └── stg_eval_scores.sql          # Clean RAGAS eval scores
├── intermediate/
│   ├── int_daily_query_metrics.sql  # Aggregate by day
│   └── int_route_performance.sql    # Performance per route type
└── marts/
    ├── fct_daily_performance.sql    # Daily KPI fact table
    └── rpt_eval_dashboard.sql       # Evaluation reporting model
```

**Key metrics in fct_daily_performance:**
- total_queries, avg_ttft_ms, p95_ttft_ms
- total_tokens, thumbs_up_rate, thumbs_down_rate
- cache_hit_rate, hallucination_rate

#### 12.2 Load Testing with Locust
```python
# locustfile.py — Target: 100 concurrent users, p95 TTFT <200ms
class RAGPipelineUser(HttpUser):
    wait_time = between(1, 3)
    @task(10)
    def query_factual(self):
        # POST /api/v1/query with JWT auth

# Run: locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m
```

#### 12.3 Security Hardening Checklist
- [ ] All secrets in .env (never hardcoded)
- [ ] JWT_SECRET minimum 64-character random string
- [ ] Security headers: X-Content-Type-Options, X-Frame-Options, HSTS
- [ ] Rate limiting: 60 req/min per user, 1000 req/min per tenant
- [ ] Input sanitization: max 1000 chars, strip HTML/script tags
- [ ] SQL injection prevention: parameterized queries only
- [ ] PostgreSQL rag_user has no SUPERUSER privileges
- [ ] Redis password-protected, no external port exposure
- [ ] API key rotation every 90 days

#### 12.4 Final Production Checklist
- [ ] All 200+ golden dataset evaluation tests passing (faithfulness >0.90)
- [ ] Load test: 100 concurrent users, p95 TTFT <200ms
- [ ] All security headers verified
- [ ] RLS verified: tenant A cannot access tenant B data
- [ ] dbt models running and populating analytics tables
- [ ] GitHub Actions CI: fast eval passing, nightly eval scheduled
- [ ] Hard-negative mining worker running on cron
- [ ] API documentation complete at /docs
- [ ] README.md with full setup and architecture guide
- [ ] Docker Compose production manifest tested end-to-end

### Day 12 Outcomes
- dbt models producing daily analytics fact tables
- System sustains 100 concurrent SSE streams at <200ms TTFT (p95)
- All security headers and RLS policies verified
- **Full platform end-to-end live and production-ready**

---

## Final Architecture Delivered

```
                +-----------------------------------------+
                |   Next.js 14 Streaming Chat UI           |
                |   SSE Consumer + PDF BBox Viewer         |
                +------------------+----------------------+
                                   | HTTPS / SSE
                +-----------------------------------------+
                |   FastAPI API Gateway (Nginx)            |
                |   JWT Auth → PII Guard → Rate Limiter    |
                +--------+--------------------------+------+
         Cache HIT <15ms |                          | Cache MISS
    +-------------------v--+    +------------------v------------------+
    | Redis Semantic Cache  |    | Agentic Query Processor             |
    | (Vector Similarity)   |    | HyDE + Multi-Query + Strategy Route |
    +-----------------------+    +----+----------+----------+----------+
                                      |          |          |
                              BM25    |  pgvector |  GraphRAG|
                    +-----------------v----------v----------v---------+
                    |         Tri-Hybrid Retrieval Engine              |
                    |   pgvector HNSW + BM25 TSVector + GraphRAG      |
                    +----------------------------+---------------------+
                                                 | RRF Fusion
                    +----------------------------v---------------------+
                    |   ONNX ColBERT Reranker + LLMLingua Compressor   |
                    +----------------------------+---------------------+
                                                 | Top-5 Chunks
                    +----------------------------v---------------------+
                    |   Gemini 1.5 Pro / GPT-4o Grounded Generation    |
                    |   Structured JSON + Bounding-Box Citation SSE    |
                    +--------------------+----------------------------+
                                         |
              +---------------------------+---------------------------+
              |                                                        |
+-------------v-----------+                         +----------------v--+
| OpenTelemetry + LangFuse |                         | Postgres Logs      |
| Live Tracing Dashboard   |                         | dbt Analytics      |
+--------------------------+                         | RAGAS CI/CD Eval   |
                                                     +--------------------+
```

---

## Technology Stack

| Component | Technology |
|:---|:---|
| API Framework | FastAPI + Pydantic v2 + asyncpg |
| Document Parsing | Docling (Vision Layout Parser) |
| PII Masking | Microsoft Presidio |
| Embedding Model | OpenAI text-embedding-3-small (1536d) |
| Vector DB | PostgreSQL 16 + pgvector HNSW |
| Lexical Search | PostgreSQL TSVector + BM25 Okapi |
| Knowledge Graph | PostgreSQL Recursive CTE / Apache AGE |
| Reranking | ONNX ColBERT + BGE Reranker Large |
| Compression | LongLLMLingua2 |
| Caching | Redis 7 (Semantic Vector Cache) |
| Task Queue | Celery 5 + Redis Broker |
| LLM Generation | Gemini 1.5 Pro / GPT-4o |
| Frontend | Next.js 14 App Router + TypeScript |
| Observability | OpenTelemetry + LangFuse |
| Evaluation | RAGAS + Golden Dataset CI/CD |
| Analytics | dbt Core + PostgreSQL Marts |
| Load Testing | Locust |
| Infrastructure | Docker Compose → Kubernetes-ready |
