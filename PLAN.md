# Production RAG Pipeline — 12-Day Implementation Guide
### Repository: https://github.com/Sobanshahid10/RagPipeline

> This is a day-by-day execution guide. Every task specifies exactly what file to create, what it must contain, and what test proves it works. Nothing is vague. Follow this top to bottom and you will have a fully deployed, production-grade RAG platform on Day 12.

---

## Day 1 — Project Scaffold, Docker Infrastructure & PostgreSQL Schema

**Goal:** Every service runs, the database schema is live, and FastAPI returns 200 on `/health`.

**Deliverables:**
- `docker-compose.yml` — orchestrates PostgreSQL, Redis, FastAPI backend, Celery worker
- `backend/db/init.sql` — full schema with extensions, indexes, and RLS
- `backend/app/main.py` — FastAPI app with `/health` and `/api/v1/info`
- `backend/app/config.py` — Pydantic Settings from environment variables
- `backend/Dockerfile` — reproducible Python 3.11 image
- `backend/requirements.txt` — pinned dependency list
- `.gitignore` — excludes `.venv/`, `.env`, `__pycache__/`, `*.pyc`, `node_modules/`

**Tasks:**

1. **Create `docker-compose.yml`** at project root. It must define four services:
   - `postgres`: image `pgvector/pgvector:pg16`, port `5432`, healthcheck `pg_isready -U rag_user -d rag_db`, volume `postgres_data:/var/lib/postgresql/data`, mounts `./backend/db/init.sql` into `/docker-entrypoint-initdb.d/`
   - `redis`: image `redis:7-alpine`, port `6379`, healthcheck `redis-cli ping`
   - `backend`: built from `./backend/Dockerfile`, port `8000:8000`, `depends_on` postgres and redis with `condition: service_healthy`
   - `celery_worker`: same image as backend, command `celery -A app.celery_app worker --loglevel=info -Q high_priority,low_priority --concurrency=4`

2. **Create `backend/db/init.sql`**. It must:
   - Run `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`, `"vector"`, `"pg_trgm"` in that order
   - Create table `tenants(id UUID, name TEXT, slug VARCHAR(50) UNIQUE, created_at TIMESTAMPTZ)`
   - Create table `users(id UUID, tenant_id UUID FK→tenants, email TEXT UNIQUE, hashed_password TEXT, roles TEXT[] DEFAULT '{viewer}', is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ)`
   - Create table `documents(id UUID, tenant_id UUID, filename TEXT, file_type VARCHAR(20), doc_hash VARCHAR(64) UNIQUE, storage_uri TEXT, status VARCHAR(20) DEFAULT 'pending', total_pages INT DEFAULT 0, metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`
   - Create table `chunks(id UUID, document_id UUID FK→documents ON DELETE CASCADE, tenant_id UUID, chunk_index INT, content TEXT, contextual_summary TEXT, page_number INT, bounding_box JSONB, token_count INT, embedding VECTOR(1536), sparse_tsv TSVECTOR, created_at TIMESTAMPTZ)`
   - Create table `entity_triples(id UUID, tenant_id UUID, source_chunk_id UUID FK→chunks ON DELETE CASCADE, subject TEXT, predicate TEXT, object TEXT, created_at TIMESTAMPTZ)`
   - Create table `query_interactions(id UUID, tenant_id UUID, user_id UUID, session_id UUID, raw_query TEXT, rewritten_query TEXT, route_used VARCHAR(50), retrieved_chunk_ids UUID[], answer TEXT, ttft_ms INT, total_latency_ms INT, prompt_tokens INT, completion_tokens INT, user_feedback INT DEFAULT 0, created_at TIMESTAMPTZ)`
   - Create table `eval_scores(id UUID, interaction_id UUID FK→query_interactions, context_recall FLOAT, context_precision FLOAT, faithfulness FLOAT, answer_relevancy FLOAT, hallucination_detected BOOLEAN DEFAULT FALSE, evaluated_at TIMESTAMPTZ)`
   - Create HNSW index: `CREATE INDEX idx_chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);`
   - Create GIN index: `CREATE INDEX idx_chunks_sparse_tsv ON chunks USING gin (sparse_tsv);`
   - Run `ALTER TABLE documents ENABLE ROW LEVEL SECURITY;` and same for `chunks`, `entity_triples`, `query_interactions`

3. **Create `backend/app/config.py`** using `pydantic_settings.BaseSettings`. Fields: `PROJECT_NAME`, `API_V1_STR="/api/v1"`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ALGORITHM="HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES=1440`. Load from `.env` file.

4. **Create `backend/app/main.py`**. It must:
   - Instantiate `FastAPI(title=settings.PROJECT_NAME, docs_url="/docs")`
   - Add `CORSMiddleware` allowing all origins (tighten on Day 12)
   - Define `GET /health` returning `{"status": "healthy", "version": "1.0.0"}`
   - Define `GET /api/v1/info` returning project name and environment string

5. **Create `backend/requirements.txt`**. Include: `fastapi>=0.110.0`, `uvicorn[standard]`, `pydantic>=2.6.0`, `pydantic-settings`, `asyncpg`, `sqlalchemy[asyncio]>=2.0`, `redis`, `celery`, `python-jose[cryptography]`, `passlib[bcrypt]`, `tiktoken`, `pytest`, `pytest-asyncio`

6. **Create `backend/Dockerfile`**. Base image `python:3.11-slim`. Install system deps `build-essential curl`. Copy `requirements.txt`, run `pip install --no-cache-dir -r requirements.txt`. Copy `.`. Expose `8000`. CMD `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

**Test:** Run `docker-compose up`. All four containers must show `healthy` or `running`. Open `http://localhost:8000/health` in browser and confirm `{"status":"healthy"}`. Open `http://localhost:8000/docs` and confirm Swagger UI loads.

---

## Day 2 — Authentication: JWT, Multi-Tenant Users & PostgreSQL RLS Enforcement

**Goal:** Register, login, and access a protected endpoint using a JWT. Verify RLS blocks cross-tenant data access.

**Deliverables:**
- `backend/app/models/user.py` — SQLAlchemy ORM models for `tenants` and `users`
- `backend/app/schemas/auth.py` — Pydantic schemas for register, login, token, profile
- `backend/app/core/security.py` — bcrypt hashing, JWT creation and verification
- `backend/app/core/dependencies.py` — `get_current_user` FastAPI dependency
- `backend/app/api/auth.py` — `/register`, `/login`, `/me` router
- `backend/app/db/session.py` — async SQLAlchemy engine and session factory
- `backend/tests/test_auth.py` — 6 test cases covering the full auth flow

**Tasks:**

1. **Create `backend/app/db/session.py`**. It must:
   - Create `async_engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=10)`
   - Define `AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)`
   - Define `async def get_db()` as an async generator yielding a session and closing it on exit
   - Before yielding the session, execute `SET LOCAL app.current_tenant_id = '<tenant_id>'` so RLS applies

2. **Create `backend/app/core/security.py`**. It must define:
   - `hash_password(plain: str) -> str` using `passlib.CryptContext(schemes=["bcrypt"])`
   - `verify_password(plain: str, hashed: str) -> bool`
   - `create_access_token(data: dict, expires_delta: timedelta) -> str` using `python-jose` and `settings.JWT_SECRET`
   - `decode_access_token(token: str) -> dict` — returns payload or raises `HTTPException(401)`

3. **Create `backend/app/core/dependencies.py`**. Define `get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db))`. It must decode the token, look up the user in the database, and raise `HTTPException(401, "Invalid token")` if user is not found or token is expired.

4. **Create `backend/app/api/auth.py`** router with prefix `/api/v1/auth`. It must define:
   - `POST /register` — accepts `UserCreate(email, password, tenant_name)`. Creates a tenant record then a user record. Returns `UserProfile`.
   - `POST /login` — accepts `OAuth2PasswordRequestForm`. Verifies email and password. Returns `{"access_token": "...", "token_type": "bearer"}`.
   - `GET /me` — protected by `get_current_user`. Returns the current user's profile.

5. **Add RLS policy to `init.sql`** (append if not already there):
   ```sql
   CREATE POLICY chunks_tenant_isolation ON chunks
       USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
   ```
   Do the same for `documents`, `entity_triples`, `query_interactions`.

6. **Create `backend/tests/test_auth.py`**. Test cases must cover:
   - Register a new user: expect 200 with `email` in response
   - Login with correct credentials: expect JWT token in response
   - Login with wrong password: expect 401
   - Access `GET /me` with valid token: expect user profile
   - Access `GET /me` without token: expect 401
   - Access `GET /me` with malformed token: expect 401

**Test:** Run `pytest tests/test_auth.py -v`. All 6 tests pass. Manually register two users with different `tenant_name` values, log in as user A, and confirm that querying `chunks` only returns rows where `tenant_id` matches user A's tenant.

---

## Day 3 — Document Ingestion: Vision Parsing, PII Masking & Semantic Chunking

**Goal:** Upload a PDF, have Celery process it end-to-end in the background, and confirm chunks appear in the database with bounding boxes and contextual summaries.

**Deliverables:**
- `backend/app/api/documents.py` — upload and status endpoints
- `backend/app/ingestion/parser.py` — Docling-based layout-aware PDF parser
- `backend/app/ingestion/pii.py` — Microsoft Presidio PII masker
- `backend/app/ingestion/chunker.py` — sentence-aware semantic chunking
- `backend/app/ingestion/contextual.py` — LLM-based global summary generator
- `backend/app/ingestion/pipeline.py` — Celery task wiring all stages together
- `backend/app/celery_app.py` — Celery app instance connected to Redis broker
- `backend/tests/test_ingestion.py` — 5 unit tests

**Tasks:**

1. **Add to `requirements.txt`**: `docling`, `presidio-analyzer`, `presidio-anonymizer`, `spacy`, `sentence-transformers`

2. **Create `backend/app/celery_app.py`**:
   ```python
   from celery import Celery
   from app.config import settings
   
   celery_app = Celery(
       "rag_worker",
       broker=settings.REDIS_URL,
       backend=settings.REDIS_URL,
       include=["app.ingestion.pipeline"]
   )
   celery_app.conf.task_routes = {
       "app.ingestion.pipeline.process_document": {"queue": "high_priority"}
   }
   ```

3. **Create `backend/app/ingestion/parser.py`**. The function `parse_document(file_path: str) -> list[dict]` must:
   - Use `docling.DocumentConverter` to convert the file
   - Return a list of page dicts, each containing: `page_number: int`, `content: str` (plain text with structure preserved), `bounding_boxes: list[dict]` (list of `{text, ymin, xmin, ymax, xmax}` coordinates normalized 0–1)
   - For scanned PDFs, Docling's built-in OCR pipeline activates automatically

4. **Create `backend/app/ingestion/pii.py`**. The function `mask_pii(text: str) -> str` must:
   - Initialize `AnalyzerEngine()` and `AnonymizerEngine()` from Presidio
   - Detect entities: `PERSON`, `EMAIL_ADDRESS`, `PHONE_NUMBER`, `CREDIT_CARD`, `US_SSN`, `NRP`
   - Replace each detected entity with its type label, e.g., `<PERSON>`, `<EMAIL_ADDRESS>`
   - Return the anonymized text string

5. **Create `backend/app/ingestion/contextual.py`**. The async function `generate_contextual_summary(document_text: str, llm_client) -> str` must:
   - Send a prompt to the LLM: `"In 2 sentences, summarize what this document is about for retrieval context: {first_500_chars}"`
   - Return the summary string
   - This summary is prepended to every chunk before embedding: `f"[Context: {summary}]\n{chunk_text}"`

6. **Create `backend/app/ingestion/chunker.py`**. The function `semantic_chunk(text: str, contextual_summary: str, chunk_size: int = 512, overlap: int = 64) -> list[dict]` must:
   - Split text into sentences (use spaCy `en_core_web_sm` sentencizer or regex fallback)
   - Prepend `[Context: {contextual_summary}]` to every chunk
   - Slide a window of sentences, enforcing `chunk_size` token limit counted by tiktoken `cl100k_base`
   - Overlap by carrying the last 2 sentences of the previous window into the next
   - Return list of dicts: `{chunk_index, content, token_count, contextual_summary}`

7. **Create `backend/app/ingestion/pipeline.py`**. The Celery task `@celery_app.task process_document(document_id, tenant_id, file_path)` must:
   - Step 1: Update `documents.status = 'processing'`
   - Step 2: Call `parser.parse_document(file_path)` — get pages with bounding boxes
   - Step 3: For each page, call `pii.mask_pii(page.content)`
   - Step 4: Call `contextual.generate_contextual_summary(all_text)`
   - Step 5: Call `chunker.semantic_chunk(masked_text, summary)`
   - Step 6: For each chunk, generate embedding (Day 4 will add this — insert `None` for now)
   - Step 7: Bulk insert chunk rows into `chunks` table with `bounding_box`, `contextual_summary`, `page_number`
   - Step 8: Update `documents.status = 'indexed'`
   - On any exception: update `documents.status = 'failed'`, log the error, re-raise with retry

8. **Create `backend/app/api/documents.py`** router with prefix `/api/v1/documents`. Define:
   - `POST /upload` — accepts `UploadFile`. Computes SHA-256 hash. Rejects if `doc_hash` already exists. Saves file to `storage/uploads/`. Creates `documents` record. Enqueues `process_document` Celery task. Returns `{document_id, status: "processing"}` immediately.
   - `GET /{document_id}` — returns document status, filename, total_pages, and chunk count

**Test:** Start the stack with `docker-compose up`. Upload a sample PDF to `POST /api/v1/documents/upload`. Poll `GET /api/v1/documents/{id}` until status is `indexed`. Query the `chunks` table via psql and confirm rows have non-null `content`, `contextual_summary`, and `bounding_box` fields.

---

## Day 4 — Vector Indexing: Embeddings, pgvector HNSW & Celery Task Optimization

**Goal:** Every chunk in the database has a non-null embedding vector. Vector similarity search returns relevant results in under 100ms.

**Deliverables:**
- `backend/app/ingestion/embedder.py` — embedding generation with Redis cache
- Updated `backend/app/ingestion/pipeline.py` — embedding step wired into pipeline
- `backend/app/retrieval/vector_search.py` — pgvector cosine similarity query
- `backend/app/retrieval/bm25_search.py` — BM25 TSVector full-text query
- `backend/tests/test_search.py` — 4 unit tests

**Tasks:**

1. **Create `backend/app/ingestion/embedder.py`**. The async function `embed_text(text: str, redis_client) -> list[float]` must:
   - Compute `cache_key = f"emb:{hashlib.sha256(text.encode()).hexdigest()[:16]}"`
   - Check Redis for cached vector: `await redis_client.get(cache_key)`
   - On cache miss: generate embedding via Gemini `text-embedding-004` (or local `sentence-transformers/all-mpnet-base-v2` / deterministic unit normalized fallback)
   - Store result in Redis with `TTL = 2592000` (30 days)
   - Return the embedding as `list[float]`
   - Batch variant: `embed_batch(texts: list[str]) -> list[list[float]]` — submit all texts in a single API call

2. **Update `backend/app/ingestion/pipeline.py`**. In the Celery task, after chunking:
   - Call `embed_batch([c["content"] for c in chunks])` to get all embeddings in one API call
   - Assign each embedding to its chunk before the bulk INSERT
   - Also generate and store `sparse_tsv = to_tsvector('english', content)` via a raw SQL update after insert

3. **Create `backend/app/retrieval/vector_search.py`**. The async function `vector_search(embedding: list[float], tenant_id: str, top_k: int = 20) -> list[dict]` must execute:
   ```sql
   SET hnsw.ef_search = 100;
   SELECT id, document_id, content, contextual_summary, page_number, bounding_box,
          1 - (embedding <=> $1::vector) AS similarity_score
   FROM chunks
   WHERE tenant_id = $2
   ORDER BY embedding <=> $1::vector
   LIMIT $3;
   ```
   Return list of chunk dicts with `id`, `content`, `similarity_score`, `bounding_box`.

4. **Create `backend/app/retrieval/bm25_search.py`**. The async function `bm25_search(query: str, tenant_id: str, top_k: int = 20) -> list[dict]` must execute:
   ```sql
   SELECT id, document_id, content, contextual_summary, page_number, bounding_box,
          ts_rank_cd(sparse_tsv, query) AS bm25_score
   FROM chunks, plainto_tsquery('english', $1) AS query
   WHERE sparse_tsv @@ query AND tenant_id = $2
   ORDER BY bm25_score DESC
   LIMIT $3;
   ```

5. **Verify HNSW index**: after inserting 1000+ chunks, run `EXPLAIN ANALYZE` on the vector query and confirm `Index Scan using idx_chunks_hnsw` appears in the plan.

**Test:** Insert 500 test chunks with known content. Call `vector_search("annual leave policy", tenant_id)` and confirm the top result has a `similarity_score > 0.75`. Call `bm25_search("dental coverage", tenant_id)` and confirm the top result contains "dental". Both queries must complete in under 100ms (measure with `time.perf_counter()`).

---

## Day 5 — Knowledge Graph: Entity Extraction, Triple Storage & Multi-Hop Traversal

**Goal:** GraphRAG retrieval returns relevant chunks for a multi-hop query that vector search alone would miss.

**Deliverables:**
- `backend/app/ingestion/graph_extractor.py` — LLM-based triple extraction (Gemini / Groq / local fallback)
- `backend/app/retrieval/graph_search.py` — recursive CTE multi-hop traversal
- Updated `backend/app/ingestion/pipeline.py` — graph extraction wired after chunking
- `backend/tests/test_graph.py` — 3 unit tests

**Tasks:**

1. **Create `backend/app/ingestion/graph_extractor.py`**. The async function `extract_triples(chunk_id: str, chunk_content: str, tenant_id: str, llm_client, db) -> None` must:
   - Send prompt to Groq (`gpt-oss-120b` / `gpt-oss-20b`) or Gemini (`gemini-2.0-flash` / `gemini-1.5-flash`):
     ```
     Extract all entity relationships from the text below.
     Return ONLY a valid JSON array with this exact structure, no markdown:
     [{"subject": "Entity A", "predicate": "relationship_type", "object": "Entity B"}]
     Text: {chunk_content}
     ```
   - Parse the JSON response. Skip if JSON is malformed — never crash.
   - Normalize all entity strings to title case, strip extra whitespace
   - Bulk INSERT valid triples into `entity_triples` with `source_chunk_id = chunk_id` and `tenant_id`
   - Only run extraction on chunks that contain at least one named entity (pre-filter with spaCy NER to save LLM calls)

2. **Update `backend/app/ingestion/pipeline.py`**. After the chunk embedding step, for each chunk, call `extract_triples()` asynchronously. Use `asyncio.gather()` to run extractions in parallel.

3. **Create `backend/app/retrieval/graph_search.py`**. The async function `graph_search(query: str, tenant_id: str, max_hops: int = 3, top_k: int = 15) -> list[dict]` must:
   - Extract entities from the query using spaCy NER
   - For each extracted entity, execute the recursive CTE:
     ```sql
     WITH RECURSIVE graph_traverse AS (
         SELECT subject, predicate, object, source_chunk_id, 1 AS depth
         FROM entity_triples
         WHERE (subject ILIKE $1 OR object ILIKE $1) AND tenant_id = $2
     
         UNION ALL
     
         SELECT e.subject, e.predicate, e.object, e.source_chunk_id, g.depth + 1
         FROM entity_triples e
         JOIN graph_traverse g ON e.subject = g.object
         WHERE g.depth < $3 AND e.tenant_id = $2
     )
     SELECT DISTINCT c.id, c.content, c.bounding_box, c.page_number
     FROM graph_traverse gt
     JOIN chunks c ON c.id = gt.source_chunk_id
     LIMIT $4;
     ```
   - Merge and deduplicate results across all entities
   - Return list of chunk dicts compatible with vector and BM25 result format

**Test:** Ingest a document containing sentences like "Alice manages the London Office. The London Office follows the UK Leave Policy." Then query `graph_search("What policy does Alice's team follow?")`. Confirm the UK Leave Policy chunk is returned. Verify with `pytest tests/test_graph.py -v`, all 3 tests pass.

---

## Day 6 — Retrieval Engine: RRF Fusion, ONNX Reranker & LLMLingua Compression

**Goal:** A single `/api/v1/retrieval/search` call runs all three retrieval methods in parallel, fuses them, reranks in under 150ms total, and returns top-5 compressed chunks.

**Deliverables:**
- `backend/app/retrieval/fusion.py` — Reciprocal Rank Fusion implementation
- `backend/app/retrieval/reranker.py` — ONNX cross-encoder reranker
- `backend/app/retrieval/compressor.py` — LLMLingua contextual compression
- `backend/app/retrieval/engine.py` — orchestrator combining all retrieval stages
- `backend/app/api/retrieval.py` — `/search` API endpoint
- `backend/tests/test_retrieval_pipeline.py` — 5 integration tests

**Tasks:**

1. **Create `backend/app/retrieval/fusion.py`**. The function `reciprocal_rank_fusion(result_sets: dict[str, list[dict]], k: int = 60, top_n: int = 50) -> list[dict]` must:
   - Accept a dict with keys `"bm25"`, `"vector"`, `"graph"` each containing a ranked list of chunk dicts
   - Compute `score[chunk_id] += 1.0 / (k + rank + 1)` for every chunk in every list
   - Merge chunk metadata from the first time each chunk ID is seen
   - Sort by score descending, return top `top_n` as list of dicts with added `rrf_score` field

2. **Create `backend/app/retrieval/reranker.py`**. The class `CrossEncoderReranker` must:
   - On `__init__`: load `cross-encoder/ms-marco-MiniLM-L-6-v2` as ONNX model using `optimum.onnxruntime.ORTModelForSequenceClassification` (export once on first run)
   - Method `rerank(query: str, candidates: list[dict], top_k: int = 5) -> list[dict]`:
     - Build input pairs `[(query, chunk["content"]) for chunk in candidates[:40]]`
     - Run inference in batch via ONNX Runtime
     - Sort by logit score descending
     - Return top `top_k` with added `rerank_score` field
   - Fallback: if ONNX model is unavailable, sort by `rrf_score` directly and log a warning

3. **Create `backend/app/retrieval/compressor.py`**. The function `compress_context(chunks: list[dict], query: str, ratio: float = 0.5) -> list[dict]` must:
   - Add to requirements: `llmlingua`
   - Initialize `PromptCompressor("microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank")`
   - Concatenate chunk contents into a single context string
   - Call `compressor.compress_prompt(context, question=query, ratio=ratio)`
   - Map compressed segments back to source chunk IDs (preserve `bounding_box` metadata)
   - Return chunks with updated compressed `content` field

4. **Create `backend/app/retrieval/engine.py`**. The async function `retrieve(query: str, tenant_id: str) -> list[dict]` must:
   - Step 1: Embed the query via `embedder.embed_text(query)`
   - Step 2: Fire BM25, vector, and graph searches in parallel using `asyncio.gather()`
   - Step 3: Fuse results via `fusion.reciprocal_rank_fusion()`
   - Step 4: Rerank top-40 via `reranker.rerank()`
   - Step 5: Compress top-5 via `compressor.compress_context()`
   - Return final list of 5 chunks with `rrf_score`, `rerank_score`, `bounding_box`, `page_number`
   - Measure and log total latency at each stage

5. **Create `backend/app/api/retrieval.py`**. Define `POST /api/v1/retrieval/search` accepting `{query: str}`. Call `engine.retrieve()`. Return the top-5 chunks as JSON.

**Test:** Run `pytest tests/test_retrieval_pipeline.py -v`. Measure end-to-end retrieval latency — it must be under 150ms excluding embedding API call. Confirm the chunk that appears in all three retrieval methods gets the highest RRF score.

---

## Day 7 — Agentic Query Layer: Semantic Cache, HyDE, Query Expansion & Strategy Router

**Goal:** Semantically identical queries return cached answers in under 15ms. Novel queries are automatically routed to the correct retrieval strategy.

**Deliverables:**
- `backend/app/agentic/cache.py` — Redis semantic vector cache
- `backend/app/agentic/hyde.py` — Hypothetical Document Embedding generator
- `backend/app/agentic/expander.py` — multi-query expansion
- `backend/app/agentic/router.py` — LLM-based strategy classifier
- `backend/app/agentic/pipeline.py` — full pre-retrieval orchestrator
- `backend/tests/test_agentic.py` — 4 unit tests

**Tasks:**

1. **Create `backend/app/agentic/cache.py`**. Class `SemanticCache` with:
   - `__init__(redis_client, threshold: float = 0.96)`
   - `async get(query_embedding: list[float]) -> str | None`:
     - Fetch all cached entries from Redis hash `rag:cache:entries`
     - Compute cosine similarity between `query_embedding` and each cached embedding using numpy
     - If max similarity >= `self.threshold`, return the cached answer string
     - Otherwise return `None`
   - `async set(query: str, embedding: list[float], answer: str, ttl: int = 3600)`:
     - Store `{embedding: list, answer: str}` as JSON in Redis with key `rag:cache:{sha256(query)[:12]}` and given TTL

2. **Create `backend/app/agentic/hyde.py`**. Async function `generate_hyde_embedding(query: str, llm_client, embedder) -> list[float]` must:
   - Send prompt: `"Write a 3-sentence document excerpt that would directly answer this question: {query}"`
   - Embed the hypothetical answer text (not the query text)
   - Return the embedding vector

3. **Create `backend/app/agentic/expander.py`**. Async function `expand_query(query: str, llm_client) -> list[str]` must:
   - Send prompt: `"Generate 3 alternative phrasings of this search query for a document retrieval system. Return as a JSON array only: {query}"`
   - Parse JSON response
   - Return `[query] + alternatives` (original always first)
   - On parse failure, return `[query]` and log warning

4. **Create `backend/app/agentic/router.py`**. Async function `classify_route(query: str, llm_client) -> str` must:
   - Send a few-shot classification prompt listing these routes with examples:
     - `FACTUAL_VECTOR` — "What does the refund policy say?" → single-document factual lookup
     - `MULTI_HOP_GRAPH` — "What rules apply to employees in London hired before 2022?" → requires entity traversal
     - `ANALYTICAL_SQL` — "How many queries were made last week?" → requires aggregation over structured data
     - `GREETING_DIRECT` — "Hello, how are you?" → no retrieval needed
   - Return exactly one of the four string labels
   - Default to `FACTUAL_VECTOR` on failure

5. **Create `backend/app/agentic/pipeline.py`**. Async function `process_query(query: str, tenant_id: str, user_id: str) -> dict` must:
   ```
   1. Generate query embedding
   2. Check SemanticCache → if HIT: return {answer, source: "cache", latency_ms}
   3. Classify route via router.classify_route()
   4. If route == GREETING_DIRECT: return direct LLM response, skip retrieval
   5. Expand query via expander.expand_query()
   6. Generate HyDE embedding in parallel with query expansion
   7. Run retrieval.engine.retrieve() with expanded queries and HyDE embedding
   8. Return {chunks, route, query_variants, hyde_used: true/false}
   ```

**Test:** Run `pytest tests/test_agentic.py -v`. Manually test cache: send the same query twice, confirm second response has `source: "cache"` and latency under 15ms. Test router: send "What is Alice's department?" and confirm route is `MULTI_HOP_GRAPH`.

---

## Day 8 — LLM Generation: Grounded SSE Streaming & Bounding-Box Citation Engine

**Goal:** A query returns a streaming response where every factual claim is cited with chunk ID, page number, and bounding box coordinates in real time.

**Deliverables:**
- `backend/app/generation/prompt_builder.py` — context assembly and prompt construction
- `backend/app/generation/streamer.py` — SSE token streamer with citation extraction
- `backend/app/generation/citation_parser.py` — extracts `[SOURCE:chunk_id:page]` tags from stream
- `backend/app/api/query.py` — `POST /api/v1/query` SSE endpoint
- `backend/tests/test_generation.py` — 4 unit tests

**Tasks:**

1. **Create `backend/app/generation/prompt_builder.py`**. Function `build_prompt(query: str, chunks: list[dict]) -> tuple[str, str]` must:
   - System prompt (static string):
     ```
     You are a precise document Q&A assistant. Answer ONLY based on the provided context.
     If the context does not contain enough information to answer, say exactly:
     "I don't have enough information in the provided documents to answer this question."
     Never fabricate facts. After every sentence containing a factual claim, append a citation
     in this exact format: [SOURCE:{chunk_id}:{page_number}]
     ```
   - User prompt template: format each chunk as `--- Chunk {i+1} (chunk_id: {id}, page: {page_number}) ---\n{content}\n`
   - Return `(system_prompt, user_prompt)`

2. **Create `backend/app/generation/citation_parser.py`**. Function `extract_citations(text: str, chunks: list[dict]) -> list[dict]` must:
   - Find all `[SOURCE:chunk_id:page_number]` patterns via regex
   - For each match, look up `chunk_id` in the `chunks` list
   - Return list of `CitationBlock` dicts: `{chunk_id, document_id, page_number, bounding_box, source_filename, excerpt: content[:200]}`

3. **Create `backend/app/generation/streamer.py`**. Async generator `stream_response(query: str, chunks: list[dict], llm_client) -> AsyncGenerator[dict, None]` must:
   - Record `start_time = time.perf_counter()`
   - Stream tokens from the LLM using `async for token in llm_client.stream(system, user_prompt)`
   - Yield each token as `{"type": "token", "content": token_text}`
   - Record TTFT on first token yielded
   - After stream completes, parse citations from full accumulated text
   - Yield each citation as `{"type": "citation", "citation": CitationBlock}`
   - Yield final event: `{"type": "done", "metadata": {ttft_ms, total_latency_ms, prompt_tokens, completion_tokens, route_used, chunks_retrieved}}`

4. **Create `backend/app/api/query.py`**. The endpoint `POST /api/v1/query` must:
   - Accept `QueryRequest(query: str, session_id: UUID | None)`
   - Call `agentic.pipeline.process_query()` to get chunks and route
   - If answer came from cache, return it as a single SSE `done` event immediately
   - Otherwise, call `generation.streamer.stream_response()` and pipe through `EventSourceResponse`
   - After stream completes, insert a row into `query_interactions` with all metadata
   - Feedback endpoint: `POST /api/v1/query/{interaction_id}/feedback` accepts `{"feedback": 1}` or `{"feedback": -1}` and updates `user_feedback` field

**Test:** Run `pytest tests/test_generation.py -v`. Use `curl -N -X POST http://localhost:8000/api/v1/query -H "Authorization: Bearer {token}" -d '{"query":"What is the leave policy?"}' -H "Content-Type: application/json"` and confirm token events stream to the terminal followed by citation and done events.

---

## Day 9 — Next.js 14 Frontend: Streaming Chat UI, PDF Viewer & Live Citation Highlighting

**Goal:** A user can upload a document, ask a question, watch the answer stream token by token, and see the exact cited text highlighted on the PDF page in real time.

**Deliverables:**
- `frontend/` — Next.js 14 App Router project
- `frontend/app/layout.tsx` — root layout with sidebar and auth guard
- `frontend/app/(auth)/login/page.tsx` — login form
- `frontend/app/chat/page.tsx` — streaming chat interface with message history
- `frontend/app/documents/page.tsx` — document library with drag-and-drop upload
- `frontend/app/documents/[docId]/page.tsx` — PDF viewer with bounding box overlay
- `frontend/components/ChatMessage.tsx` — renders streamed tokens with citation chips
- `frontend/components/PDFViewer.tsx` — react-pdf canvas + highlight overlay
- `frontend/lib/api.ts` — typed API client for all backend endpoints

**Tasks:**

1. **Initialize project**:
   ```bash
   cd frontend
   npx create-next-app@latest . --typescript --app --no-tailwind
   npm install react-pdf @radix-ui/react-dialog framer-motion lucide-react
   ```
   Create a `styles/globals.css` with:
   - CSS custom properties: `--bg: #0A0A0F`, `--surface: #13131A`, `--accent: #6366F1`, `--accent-light: #A78BFA`, `--text: #E4E4F0`, `--muted: #6B6B80`
   - `@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@600;700&display=swap')`
   - Base styles: `body { background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }`
   - `.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; backdrop-filter: blur(8px); }`

2. **Create `frontend/lib/api.ts`**. Must export:
   - `login(email, password) -> Promise<{access_token: string}>`
   - `uploadDocument(file: File, token: string) -> Promise<{document_id: string}>`
   - `getDocumentStatus(id: string, token: string) -> Promise<Document>`
   - `streamQuery(query: string, token: string) -> AsyncGenerator<SSEEvent>` — uses `fetch` + `ReadableStream` to parse SSE events line by line

3. **Create `frontend/components/ChatMessage.tsx`**. It must:
   - Accept `{role: "user"|"assistant", content: string, citations: CitationBlock[], isStreaming: boolean}`
   - Render streaming content with a blinking cursor animation while `isStreaming` is true
   - Render each citation as a chip showing `filename:page` that, when clicked, emits an event to open the PDF viewer at that page and highlight the bounding box
   - Use Framer Motion to animate new messages sliding up from the bottom

4. **Create `frontend/components/PDFViewer.tsx`**. It must:
   - Use `react-pdf` `<Document>` and `<Page>` to render PDF from a URL
   - Maintain a `highlights: CitationBlock[]` state
   - Over each page canvas, render absolutely-positioned `<div>` elements for each bounding box where `page_number` matches
   - Style highlights as `background: rgba(99, 102, 241, 0.3); border: 1px solid rgba(99, 102, 241, 0.8); border-radius: 3px;`
   - Animate new highlights with a pulse effect: keyframe scale `1.0 → 1.02 → 1.0`
   - Show document page navigation controls

5. **Create `frontend/app/chat/page.tsx`** as a Client Component. It must:
   - Maintain state: `messages`, `isStreaming`, `activeCitations`
   - On submit: append user message, call `api.streamQuery()`
   - For each SSE token event: append to the current assistant message content
   - For each SSE citation event: add to `activeCitations` and update the PDF viewer
   - For SSE done event: mark `isStreaming = false`, save interaction metadata

**Test:** Upload a PDF and ask a question about its content. Confirm tokens appear one by one in the chat. Confirm at least one citation chip appears after the stream ends. Click the citation chip and confirm the PDF opens to the correct page with a highlighted bounding box.

---

## Day 10 — Observability: OpenTelemetry Tracing, LangFuse & Admin Metrics Dashboard

**Goal:** Every query produces a complete distributed trace showing latency per component. The admin dashboard shows live p95 TTFT, cache hit rate, and token cost.

**Deliverables:**
- `backend/app/core/telemetry.py` — OpenTelemetry tracer setup
- Updated `backend/app/api/query.py` — spans wrapping every pipeline stage
- `frontend/app/dashboard/page.tsx` — admin metrics dashboard with live charts
- `backend/tests/test_observability.py` — 2 unit tests verifying span attributes

**Tasks:**

1. **Add to `requirements.txt`**: `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-asyncpg`, `langfuse`

2. **Create `backend/app/core/telemetry.py`**:
   ```python
   from opentelemetry import trace
   from opentelemetry.sdk.trace import TracerProvider
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
   
   def setup_telemetry(app):
       provider = TracerProvider()
       exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
       provider.add_span_processor(BatchSpanProcessor(exporter))
       trace.set_tracer_provider(provider)
       FastAPIInstrumentor.instrument_app(app)
       return trace.get_tracer("rag.pipeline")
   ```

3. **Instrument `backend/app/api/query.py`**. Wrap each stage in a named span:
   ```python
   with tracer.start_as_current_span("stage.semantic_cache") as span:
       span.set_attribute("cache.hit", is_hit)
       span.set_attribute("query.length", len(query))
   
   with tracer.start_as_current_span("stage.retrieval") as span:
       with tracer.start_as_current_span("retrieval.bm25"): ...
       with tracer.start_as_current_span("retrieval.vector"): ...
       with tracer.start_as_current_span("retrieval.graph"): ...
       with tracer.start_as_current_span("retrieval.rrf_fusion"): ...
       with tracer.start_as_current_span("retrieval.reranker"): ...
   
   with tracer.start_as_current_span("stage.generation") as span:
       span.set_attribute("llm.model", model_name)
       span.set_attribute("llm.ttft_ms", ttft_ms)
       span.set_attribute("llm.prompt_tokens", prompt_tokens)
   ```

4. **Add Jaeger to `docker-compose.yml`**:
   ```yaml
   jaeger:
     image: jaegertracing/all-in-one:latest
     ports:
       - "16686:16686"  # Jaeger UI
       - "4317:4317"    # OTLP gRPC receiver
   ```

5. **Create `frontend/app/dashboard/page.tsx`**. Must display:
   - Real-time query volume (last 24h) — poll `GET /api/v1/admin/stats` every 30 seconds
   - p50 / p95 / p99 TTFT bar chart (data from `query_interactions` aggregation)
   - Cache hit rate as a percentage gauge
   - Daily token spend (prompt + completion tokens × model price per token)
   - Recent query list with route label, latency, and thumbs up/down indicator
   - System health badges for Postgres, Redis, Celery (from health check endpoints)

6. **Create backend `GET /api/v1/admin/stats`** endpoint. Query `query_interactions` table and return:
   ```json
   {
     "total_queries_24h": 142,
     "avg_ttft_ms": 187,
     "p95_ttft_ms": 340,
     "cache_hit_rate": 0.31,
     "total_tokens_today": 284000,
     "thumbs_up_rate": 0.78
   }
   ```

**Test:** Run a query and open Jaeger UI at `http://localhost:16686`. Search for service `rag.pipeline`. Confirm the trace shows all 6 spans (`stage.semantic_cache`, `retrieval.bm25`, `retrieval.vector`, `retrieval.graph`, `retrieval.rrf_fusion`, `stage.generation`) with correct timing. Open the admin dashboard and confirm all metrics panels render with real data.

---

## Day 11 — RAGAS CI/CD Evaluation: Golden Dataset, Tiered GitHub Actions & Hard-Negative Mining

**Goal:** Every pull request runs a fast eval gate in under 60 seconds. Nightly evals run the full RAGAS suite and store results. Thumbs-down interactions automatically feed the evaluation dataset.

**Deliverables:**
- `evaluation/golden_dataset.json` — 200+ Q&A pairs with difficulty and category labels
- `evaluation/run_ragas.py` — RAGAS evaluation runner
- `evaluation/assert_thresholds.py` — CI threshold assertion script
- `evaluation/hard_negative_miner.py` — Celery task for feedback-driven dataset growth
- `.github/workflows/eval_fast.yml` — PR fast check workflow
- `.github/workflows/eval_nightly.yml` — nightly full RAGAS workflow
- `backend/tests/test_eval.py` — 3 unit tests for eval infrastructure

**Tasks:**

1. **Create `evaluation/golden_dataset.json`**. Populate with 200+ entries. Each entry must have:
   ```json
   {
     "id": "eval_001",
     "query": "What is the maximum annual leave for senior employees?",
     "ground_truth": "Senior employees are entitled to 30 days of annual leave per year.",
     "relevant_chunk_ids": [],
     "difficulty": "easy",
     "category": "HR_Policy"
   }
   ```
   Categories: `HR_Policy`, `Technical_Docs`, `Financial_Reports`, `Legal_Contracts`, `Onboarding`
   Difficulties: `easy` (single chunk answer), `medium` (requires 2-3 chunks), `hard` (multi-hop graph required)
   Distribution: 40% easy, 40% medium, 20% hard

2. **Create `evaluation/run_ragas.py`**. It must:
   - Load `golden_dataset.json`
   - For each sample, call the live API `POST /api/v1/query` and collect the answer and retrieved chunks
   - Build a RAGAS `Dataset` with fields: `question`, `answer`, `contexts`, `ground_truth`
   - Run `evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])`
   - Write results JSON to `evaluation/results/ragas_{timestamp}.json`
   - Print a summary table to stdout
   - Exit with code 1 if any metric falls below minimum threshold

3. **Create `.github/workflows/eval_fast.yml`**:
   ```yaml
   name: Fast Eval Gate
   on: [pull_request]
   jobs:
     fast-eval:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Set up Python
           uses: actions/setup-python@v4
           with: {python-version: '3.11'}
         - name: Install dependencies
           run: pip install -r backend/requirements.txt
         - name: Run unit tests
           run: cd backend && PYTHONPATH=. pytest tests/ -v --tb=short -x
         - name: Retrieval recall@5 check
           run: python evaluation/assert_thresholds.py --metric recall_at_5 --min 0.75
         - name: Latency budget check
           run: python evaluation/assert_thresholds.py --metric max_ttft_ms --max 500
         - name: Citation integrity check
           run: python evaluation/assert_thresholds.py --metric citation_parse_success_rate --min 0.95
   ```

4. **Create `.github/workflows/eval_nightly.yml`**:
   ```yaml
   name: Nightly RAGAS Full Evaluation
   on:
     schedule:
       - cron: '0 2 * * *'
   jobs:
     ragas-eval:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - name: Run Full RAGAS Suite
           run: python evaluation/run_ragas.py --dataset evaluation/golden_dataset.json
           env:
             API_BASE_URL: ${{ secrets.STAGING_API_URL }}
             API_TOKEN: ${{ secrets.STAGING_API_TOKEN }}
         - name: Assert faithfulness > 0.90
           run: python evaluation/assert_thresholds.py --metric faithfulness --min 0.90
         - name: Assert context precision > 0.80
           run: python evaluation/assert_thresholds.py --metric context_precision --min 0.80
         - name: Upload results
           run: python evaluation/upload_results.py
   ```

5. **Create `evaluation/hard_negative_miner.py`**. Celery periodic task `mine_hard_negatives` scheduled every 6 hours:
   - Query `query_interactions WHERE user_feedback = -1 AND created_at > NOW() - INTERVAL '6 hours'`
   - For each negative interaction, send to LLM:
     ```
     Analyze why this RAG response was poor.
     Query: {raw_query}
     Retrieved chunks: {chunk_excerpts}
     Given answer: {answer}
     
     Return JSON: {"failure_mode": "retrieval_fail|hallucination|context_loss|wrong_route", "correct_answer": "..."}
     ```
   - Append valid results to `evaluation/golden_dataset.json` with `"source": "hard_negative_mining"` and `"failure_mode"` field
   - Log count of new entries added per run

**Test:** Create a PR and confirm `eval_fast.yml` workflow completes in under 60 seconds. Verify all three fast checks pass. Give a query a thumbs-down, wait for the 6-hour miner (or trigger manually), and confirm a new entry appears in `golden_dataset.json` with the correct `failure_mode` label.

---

## Day 12 — dbt Analytics, Load Testing, Security Hardening & Production Deploy

**Goal:** The system sustains 100 concurrent SSE streams at under 200ms TTFT (p95). All security controls pass review. dbt models produce accurate daily analytics. Production Docker Compose is clean and repeatable.

**Deliverables:**
- `dbt/models/staging/stg_query_interactions.sql`
- `dbt/models/staging/stg_eval_scores.sql`
- `dbt/models/marts/fct_daily_performance.sql`
- `dbt/models/marts/rpt_eval_dashboard.sql`
- `dbt/dbt_project.yml` — dbt project configuration
- `locustfile.py` — load test definition
- `docker-compose.prod.yml` — production-hardened compose file
- `SECURITY.md` — security controls checklist with verification status

**Tasks:**

1. **Create `dbt/dbt_project.yml`**:
   ```yaml
   name: 'rag_analytics'
   version: '1.0.0'
   profile: 'rag_pipeline'
   model-paths: ["models"]
   models:
     rag_analytics:
       staging:
         +materialized: view
       marts:
         +materialized: table
   ```

2. **Create `dbt/models/staging/stg_query_interactions.sql`**:
   ```sql
   SELECT
       id,
       tenant_id,
       user_id,
       raw_query,
       route_used,
       ttft_ms,
       total_latency_ms,
       prompt_tokens,
       completion_tokens,
       (prompt_tokens + completion_tokens) AS total_tokens,
       user_feedback,
       created_at::DATE AS query_date,
       created_at
   FROM query_interactions
   WHERE created_at >= CURRENT_DATE - INTERVAL '90 days'
   ```

3. **Create `dbt/models/marts/fct_daily_performance.sql`**:
   ```sql
   SELECT
       query_date,
       COUNT(*) AS total_queries,
       AVG(ttft_ms) AS avg_ttft_ms,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ttft_ms) AS p50_ttft_ms,
       PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY ttft_ms) AS p95_ttft_ms,
       PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS p99_ttft_ms,
       SUM(total_tokens) AS total_tokens,
       COUNT(CASE WHEN user_feedback = 1 THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS thumbs_up_rate,
       COUNT(CASE WHEN route_used = 'cache' THEN 1 END)::FLOAT / NULLIF(COUNT(*), 0) AS cache_hit_rate,
       COUNT(CASE WHEN route_used = 'MULTI_HOP_GRAPH' THEN 1 END) AS graph_route_count
   FROM {{ ref('stg_query_interactions') }}
   GROUP BY 1
   ORDER BY 1 DESC
   ```

4. **Create `locustfile.py`** at project root:
   ```python
   from locust import HttpUser, task, between
   
   class RAGUser(HttpUser):
       wait_time = between(1, 3)
   
       def on_start(self):
           r = self.client.post("/api/v1/auth/login", data={
               "username": "loadtest@rag.local",
               "password": "LoadTest2026!"
           })
           self.token = r.json()["access_token"]
           self.headers = {"Authorization": f"Bearer {self.token}"}
   
       @task(8)
       def factual_query(self):
           self.client.post("/api/v1/query",
               json={"query": "What is the annual leave policy?"},
               headers=self.headers,
               stream=True
           )
   
       @task(2)
       def upload_document(self):
           with open("tests/fixtures/sample.pdf", "rb") as f:
               self.client.post("/api/v1/documents/upload",
                   files={"file": f},
                   headers=self.headers
               )
   
   # Run: locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless
   # Pass condition: p95 TTFT < 200ms, error rate < 1%
   ```

5. **Create `docker-compose.prod.yml`**:
   - Remove all `--reload` flags from uvicorn command
   - Add `nginx` service (image `nginx:alpine`) as reverse proxy on ports 80/443
   - Add `deploy.replicas: 2` for backend service
   - Add `deploy.resources.limits: {memory: 1G, cpus: "1.0"}` for backend
   - Set all secrets via environment variable references `${JWT_SECRET}` — never hardcoded
   - Add `restart: unless-stopped` to all services

6. **Complete `SECURITY.md`** as a verifiable checklist. Each item must have a verification command or step:
   - `[ ]` JWT_SECRET is minimum 64 characters: `echo -n "$JWT_SECRET" | wc -c`
   - `[ ]` No secrets in git history: `git log --all --oneline | head -20` + `detect-secrets scan`
   - `[ ]` Security headers present: `curl -I https://your-domain.com/health | grep -E "X-Content|X-Frame|Strict"`
   - `[ ]` RLS blocks cross-tenant access: documented manual test procedure
   - `[ ]` Rate limiting active: `for i in {1..70}; do curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health; done | grep -c 429`
   - `[ ]` Redis password set and port not exposed externally
   - `[ ]` Input max length enforced: send 1001-char query, expect 422
   - `[ ]` No raw HTML in chunk content (XSS prevention): grep stored chunks for `<script`

**Acceptance Gate for Day 12:**
- [ ] `dbt run && dbt test` completes with 0 failures
- [ ] Locust runs 100 concurrent users for 5 minutes — p95 TTFT < 200ms, error rate < 1%
- [ ] All 8 SECURITY.md items are checked and verified with their test command
- [ ] `docker-compose -f docker-compose.prod.yml up -d` brings up all services cleanly
- [ ] All 200+ golden dataset evals pass with faithfulness > 0.90
- [ ] GitHub Actions fast eval workflow passes in under 60 seconds from a clean checkout
- [ ] `GET /docs` returns the full OpenAPI spec
- [ ] A fresh clone of the repo + `docker-compose up` + README instructions produces a working system with no external guidance

---

## Final Architecture Delivered

```
[ Next.js 14 Chat UI ]  ←──── SSE Token Stream + Citation Bounding Boxes
        │
        │ HTTPS
        ▼
[ Nginx Reverse Proxy ]
        │
        ▼
[ FastAPI Gateway ]
  ├─ JWT Auth + RLS Tenant Injection
  ├─ PII Guard (Presidio)
  └─ Rate Limiter (60 req/min/user)
        │
        ├──────────────────────────────────────── [Cache HIT < 15ms]
        │                                                │
        ▼                                        [ Redis Semantic Cache ]
[ Agentic Pipeline ]
  ├─ Strategy Classifier (FACTUAL / GRAPH / SQL / DIRECT)
  ├─ HyDE Embedding Generator
  └─ Multi-Query Expander (3 variants)
        │
        ▼
[ Tri-Hybrid Retrieval — asyncio.gather() ]
  ├─ BM25 TSVector Search      (PostgreSQL)
  ├─ pgvector HNSW Dense Search (PostgreSQL + pgvector)
  └─ GraphRAG Recursive CTE    (PostgreSQL entity_triples)
        │
        ▼
[ Reciprocal Rank Fusion (RRF, k=60) ]
        │
        ▼
[ ONNX Cross-Encoder Reranker — top 40 → top 5, < 35ms ]
        │
        ▼
[ LLMLingua Contextual Compressor — 50% token reduction ]
        │
        ▼
[ LLM Grounded Generation — Gemini 1.5 Pro / GPT-4o ]
        │
        ├──► SSE Token Stream → Frontend
        ├──► Citation BBox Events → PDF Viewer
        └──► OpenTelemetry Spans → Jaeger + LangFuse
                                         │
                                         ▼
                               [ Postgres Interaction Log ]
                                         │
                                         ▼
                               [ dbt Analytics Pipeline ]
                               [ RAGAS Nightly CI/CD Eval ]
                               [ Hard-Negative Mining Worker ]
```

---

## Technology Stack

| Component | Technology | Version |
|:---|:---|:---:|
| API Framework | FastAPI + asyncpg | ≥0.110 |
| Data Validation | Pydantic v2 | ≥2.6 |
| Document Parsing | Docling | latest |
| PII Masking | Microsoft Presidio | latest |
| Embedding | Gemini text-embedding-004 / Sentence-Transformers | - |
| Vector Store | PostgreSQL 16 + pgvector HNSW | pg16 |
| Lexical Search | PostgreSQL TSVector + BM25 | pg16 |
| Knowledge Graph | PostgreSQL Recursive CTE | pg16 |
| Reranking | ONNX ms-marco-MiniLM-L-6-v2 | - |
| Compression | LongLLMLingua2 | latest |
| Cache | Redis 7 + Semantic Vector Cache | 7-alpine |
| Task Queue | Celery 5 + Redis | ≥5.3 |
| LLM | OpenAI GPT-OSS (120B / 20B on Groq) / Google Gemini (2.0/1.5 Flash) | - |
| Frontend | Next.js 14 App Router + TypeScript | 14 |
| Tracing | OpenTelemetry + Jaeger + LangFuse | - |
| Evaluation | RAGAS + 200-pair Golden Dataset | latest |
| Analytics | dbt Core + PostgreSQL Marts | - |
| Load Testing | Locust | latest |
| Infrastructure | Docker Compose → Kubernetes-ready | - |
