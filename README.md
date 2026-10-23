# Production Multi-Tenant RAG & Document Intelligence Platform

A multi-tenant Retrieval-Augmented Generation (RAG) application for questions over uploaded documents and a separate public knowledge book. Answers are checked for citation validity and source support before being delivered. See [security remediation and deployment prerequisites](SECURITY_REMEDIATION.md) before upgrading or deploying.

Built on **FastAPI**, **PostgreSQL 16 (`pgvector` + Recursive CTEs)**, **Redis 7**, **Celery**, **Next.js 16 (App Router)**, **OpenTelemetry**, and **dbt Core**.

---

## Architectural Highlights

- **Dual-Corpus Isolation Architecture**:
  1. **Enterprise Document Library**: Multi-tenant repository supporting PDF, DOCX, and TXT files. Ingests via Celery workers with layout-aware vision parsing, automated Presidio PII anonymization, semantic chunking, 1536-dimensional `gemini-embedding-2` vectors, and knowledge graph extraction using the configured provider.
  2. **Public Knowledge Book Explorer**: Dedicated 9-chapter reference corpus operating on a localized `all-MiniLM-L6-v2` 384-dimensional vector index with reciprocal rank fusion, passage reranking, and line-level citation validation without file uploads.
- **Strict Multi-Tenant Row-Level Security (RLS)**:
  - Verified database users select transaction-scoped tenant context. Document operations require authentication, writes require editor/admin permissions, and tenant tables enforce RLS with a restricted runtime role.
- **Tri-Hybrid Retrieval Engine**:
  - Concurrent `asyncio.gather()` execution combining:
    1. Lexical search via PostgreSQL `tsvector` + full-text ranking (`ts_rank_cd`).
    2. Dense semantic vector search via PostgreSQL `pgvector` HNSW cosine similarity.
    3. Multi-hop knowledge graph traversal via recursive Common Table Expressions (CTEs).
- **Multi-Model Inference & Resilience**:
  - Per-request answer model selection supporting **Google Gemini** (`gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-3.5-flash-lite`) and **Groq** (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`).
  - Requests use exactly the selected model/provider. Failures are visible; there is no hidden provider substitution.
- **Evidence-focused UI**:
  - Explicit public-book/document source selection, optional document scope, owned conversation context, and account-scoped browser history.
  - Authenticated original-file previews and source passages; region coordinates are omitted when reliable mapping is unavailable.
  - Real document stages, failure messages, retry actions, configured model choices and measured answer details.
- **Observability & Analytics**:
  - OpenTelemetry HTTP/database tracing with Jaeger UI, live admin performance dashboard (TTFT percentiles p50/p95/p99, cache hit rate, token volume), and dbt Core analytical marts.
- **Comprehensive Quality Gates**:
  - Mocked-provider regression tests, opt-in real PostgreSQL isolation tests, frontend URL/history tests, TypeScript checks and a production build. Formal G-Eval remains incomplete.

---

## System Architecture

```
[ Next.js 16 App Router UI ]
        │
        ├──► Real-Time SSE Token Stream
        ├──► Evidence Coordinates (`LOC // doc.pdf § P.1`)
        └──► Canvas Bounding-Box Overlay [ymin, xmin, ymax, xmax]
        │
        ▼ HTTPS
[ Nginx Reverse Proxy / Load Balancer ]
        │
        ▼
[ FastAPI Gateway ]
  ├─ JWT Bearer Auth & Tenant Resolution
  ├─ PostgreSQL RLS Context Injection (`app.current_tenant_id`)
  ├─ Presidio PII Masking & Payload Sanitization
  └─ Redis-shared API/login limits and daily question budgets
        │
        ▼
[ Bounded owned conversation context and explicit document scope ]
        │
        ▼
[ Tri-Hybrid Retrieval Engine — asyncio.gather() ]
  ├─ TSVector Lexical Search (PostgreSQL 16)
  ├─ pgvector HNSW Dense Vector Search (PostgreSQL 16)
  └─ GraphRAG Recursive CTE Multi-Hop (PostgreSQL entity_triples)
        │
        ▼
[ Reciprocal Rank Fusion (RRF, k=60) & Cross-Encoder Reranking ]
        │
        ▼
[ Prompt Assembly & Context Compression ]
        │
        ▼
[ Multi-Model LLM Generator (Gemini 3.8/3.7 Flash or Groq GPT-OSS 120B/20B) ]
        │
        ├──► Citation + source-support checks, then SSE delivery ► Chat Workbench
        ├──► Citation Coordinates ──────────► PDF Canvas & Margin Inspector
        └──► OpenTelemetry Spans ───────────► Jaeger UI
                                                    │
                                                    ▼
                                          [ PostgreSQL Interaction Logs ]
                                                    │
                                                    ▼
                                          [ dbt Analytics Marts ]
                                          [ Regression Tests ]
```

---

## Technology Stack

| Layer | Technology | Purpose |
|:---|:---|:---|
| **API Framework** | FastAPI 0.110+ & AsyncPG | Asynchronous REST endpoints, SSE streaming, and background task dispatch |
| **Database & Vector Store** | PostgreSQL 16 + `pgvector` | HNSW cosine indexing, native full-text ranking, and recursive CTE graph traversal |
| **Cache & Task Broker** | Redis 7 Alpine | Embedding cache, shared limits, usage accounting and Celery broker |
| **Asynchronous Worker Queue** | Celery 5.3+ (solo / concurrency) | Layout vision parsing, vector embedding generation, and knowledge graph extraction |
| **Document Ingestion** | Docling & Microsoft Presidio | Layout vision parsing, table structure extraction, and PII anonymization |
| **Public Book Index** | `sentence-transformers` (all-MiniLM-L6-v2) | Local 384-dimensional vector embedding space for the public knowledge book |
| **Frontend Framework** | Next.js 16 (App Router) + TypeScript | Editorial index, split-screen PDF viewer, and streaming chat workbench |
| **Observability** | OpenTelemetry & Jaeger UI | HTTP/database traces and retrieval timing logs |
| **Evaluation Suite** | Pytest and evaluation tooling | Citation, provider-failure, isolation and retrieval regressions |
| **Data Warehouse & Marts** | dbt Core (PostgreSQL) | Daily performance marts, latency percentiles, and token accounting |
| **Production Proxy** | Nginx Alpine | Reverse proxy, unbuffered SSE pass-through, and SSL termination |

---

## Directory Structure

```
.
├── backend/
│   ├── Dockerfile                     # Python 3.11 container definition
│   ├── requirements.txt               # Backend dependency requirements
│   ├── pytest.ini                     # Pytest configuration
│   ├── app/
│   │   ├── main.py                    # FastAPI application & security middleware
│   │   ├── config.py                  # Pydantic Settings & environment variables
│   │   ├── celery_app.py              # Celery worker & priority queues
│   │   ├── api/                       # Auth, Documents, Retrieval, Query, Public Book, Admin
│   │   ├── core/                      # Security, Dependencies, Middlewares, Telemetry
│   │   ├── db/                        # Async SQLAlchemy session with RLS context injection
│   │   ├── models/                    # Tenant, User, Document, Chunk, Triple, Interaction ORMs
│   │   ├── schemas/                   # Pydantic validation schemas
│   │   ├── ingestion/                 # Docling parser, Presidio PII, Embedder, Graph extractor
│   │   ├── retrieval/                 # BM25, pgvector HNSW, Graph CTE, RRF fusion, Reranking
│   │   ├── agentic/                   # Hybrid query orchestration; experimental utilities are not used
│   │   └── generation/                # Prompt builder, Citation parser, SSE Streamer
│   ├── db/
│   │   └── init.sql                   # Schema definitions, HNSW/GIN indexes, RLS policies
│   └── tests/                         # Unit, integration, and security tests
├── frontend/                          # Next.js 16 App Router application
│   ├── Dockerfile                     # Multi-stage container definition
│   ├── app/
│   │   ├── (auth)/login/              # Authentication with system specification briefing
│   │   ├── chat/                      # Streaming chat workbench with context rail & inspector
│   │   ├── public-book/               # Editorial Index & research workbench
│   │   ├── documents/                 # Document library with layout status & manifest
│   │   ├── dashboard/                 # Real-time telemetry, latency percentiles, SLA marts
│   │   └── globals.css                # Monochrome architectural design system
│   ├── components/                    # ChatMessage, PDFViewer, Sidebar, DocumentDrawer
│   └── lib/                           # Typed API client (`api.ts`) and model registry (`models.ts`)
├── docs/                              # Step 1–11 public book architectural guides
├── dbt/                               # dbt Core analytics models and marts
├── evaluation/                        # Public book benchmark suites and live test harnesses
├── nginx/                             # Nginx reverse proxy configuration
├── storage/
│   └── knowledge/                     # Normalized public book artifacts and embeddings
├── docker-compose.yml                 # Development compose specification
├── docker-compose.prod.yml            # Production-hardened compose specification
├── locustfile.py                      # 100-user concurrent load test suite
├── SECURITY.md                        # Production security verification checklist
└── README.md
```

---

## Quickstart

### Prerequisites
- [Docker](https://www.docker.com/) and [Docker Compose](https://docs.docker.com/compose/) installed.
- (Optional for local development) Python 3.11+ and Node.js 24 LTS.

### 1. Clone & Configure Environment
```bash
git clone https://github.com/Sobanshahid10/RagPipeline.git
cd RagPipeline

# Create environment configuration from template
cp .env.example .env
```

Fill the required `DATABASE_URL`, `REDIS_URL`, and a unique `JWT_SECRET` in `.env`; uncomment and populate optional names as needed. For host development use ports 5433/6380; use the restricted `rag_runtime` database role. Compose also needs `RUNTIME_DB_PASSWORD` (production requires administrator/Redis passwords and HTTPS origins). See the remediation guide for existing volumes and public-book deployment. Configure your provider keys:
```env
# Generation & Embeddings
GEMINI_API_KEY="your-gemini-api-key"
GROQ_API_KEY="your-groq-api-key"
LLM_PROVIDER="gemini"
LLM_MODEL="gemini-3.8-flash"
EMBEDDING_MODEL="gemini-embedding-2"
```

### 2. Start the Development Stack
```bash
docker-compose up -d --build
```

Services will be live at:
- **Next.js Web Application**: [http://localhost:3000](http://localhost:3000) (or `http://localhost:3005` in standalone dev)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs) (or `http://localhost:8001/docs`)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Jaeger Tracing UI**: [http://localhost:16686](http://localhost:16686)
- **PostgreSQL Database**: `localhost:5432` (`rag_db`)
- **Redis Broker**: `localhost:6379`

### 3. Start the Production Stack
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
The production stack provisions Nginx on ports `80`/`443`, backend replicas with resource constraints (1 CPU / 1GB RAM), password-authenticated Redis, and non-reloading uvicorn workers.

---

## Public Knowledge Book Learning Track

The public book track provides a source-linked, grounded reference corpus with explicit educational step-by-step guides in [`docs/`](docs/):

1. **Step 1: Load and Parse** — Lossless structural parser preserving line ranges ([`docs/STEP_01_LOAD_PARSE.md`](docs/STEP_01_LOAD_PARSE.md)).
2. **Step 2: Clean and Normalize** — Deterministic normalization preserving source anchors ([`docs/STEP_02_CLEAN_NORMALIZE.md`](docs/STEP_02_CLEAN_NORMALIZE.md)).
3. **Step 3: Chunk** — Source-linked retrieval units with boundary protection ([`docs/STEP_03_CHUNK.md`](docs/STEP_03_CHUNK.md)).
4. **Step 4: Add Metadata** — Section paths, integrity hashes, and citation anchors ([`docs/STEP_04_ADD_METADATA.md`](docs/STEP_04_ADD_METADATA.md)).
5. **Step 5: Embed** — Local 384-dimensional dense vectors using `all-MiniLM-L6-v2` ([`docs/STEP_05_EMBED.md`](docs/STEP_05_EMBED.md)).
6. **Step 6: Store and Index** — Dedicated `public_book_chunks` table with pgvector HNSW cosine indexing ([`docs/STEP_06_STORE_INDEX.md`](docs/STEP_06_STORE_INDEX.md)).
7. **Step 7: Retrieve** — Hybrid candidate search with cosine similarity scoring ([`docs/STEP_07_RETRIEVE.md`](docs/STEP_07_RETRIEVE.md)).
8. **Step 8: Rerank and Filter** — Reciprocal rank fusion and section-scoped filtering ([`docs/STEP_08_RERANK_FILTER.md`](docs/STEP_08_RERANK_FILTER.md)).
9. **Step 9: Build Context** — Provenance validation and bounded evidence assembly ([`docs/STEP_09_BUILD_CONTEXT.md`](docs/STEP_09_BUILD_CONTEXT.md)).
10. **Step 10: Assemble Prompt** — Provider-neutral prompt construction with strict citation and abstention rules ([`docs/STEP_10_PROMPT_LLM.md`](docs/STEP_10_PROMPT_LLM.md)).
11. **Step 11: Generate Answers** — Grounded answer generation with Gemini or Groq ([`docs/STEP_11_GENERATE_GEMINI.md`](docs/STEP_11_GENERATE_GEMINI.md)).

---

## Authentication & Multi-Tenancy

Every tenant organization is isolated in PostgreSQL via hardware-enforced Row-Level Security.

### 1. Register a Tenant & Admin User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@acme.corp",
       "password": "SecurePassword2026!",
       "tenant_name": "Acme Corporation"
     }'
```

### 2. Obtain a JWT Access Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@acme.corp&password=SecurePassword2026!"
```

---

## Core API Endpoints

| Method | Endpoint | Description | Auth Required |
|:---|:---|:---|:---:|
| `GET` | `/health` | Service health and component status | No |
| `GET` | `/api/v1/info` | System metadata and active configuration | No |
| `POST` | `/api/v1/auth/register` | Register new tenant and administrator | No |
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT Bearer access token | No |
| `GET` | `/api/v1/auth/me` | Current authenticated user profile | Yes |
| `POST` | `/api/v1/documents/upload` | Upload document for async layout parsing and indexing | Yes |
| `GET` | `/api/v1/documents` | List tenant documents with parsing and chunk status | Yes |
| `GET` | `/api/v1/documents/{id}` | Inspect document chunks and layout metadata | Yes |
| `POST` | `/api/v1/documents/{id}/retry` | Retry failed or stalled ingestion (editor/admin) | Yes |
| `GET` | `/api/v1/query/models` | Configured answer providers and models | Yes |
| `DELETE` | `/api/v1/query/history` | Delete the current user’s saved interactions | Yes |
| `POST` | `/api/v1/query` | SSE streaming query with bounding-box citations | Yes |
| `POST` | `/api/v1/public-book/ask` | Grounded query against the public knowledge index | Yes |
| `POST` | `/api/v1/query/{id}/feedback` | Record thumbs-up / thumbs-down interaction feedback | Yes |
| `GET` | `/api/v1/admin/stats` | Real-time TTFT percentiles, cache hit rate, token volume | Yes |

---

## Automated Verification & Testing

### Run Backend Unit & Integration Tests
```bash
# Run the complete test suite
PYTHONPATH=".:backend" pytest backend/tests -v
```
Provider calls are mocked; no live credentials or provider quota are needed. Set `RAG_TEST_ADMIN_URL` and `RAG_TEST_RUNTIME_URL` only to a dedicated disposable PostgreSQL database to enable the real RLS/ingestion tests. Never point these variables at production.

### Run Frontend Static Type Check
```bash
cd frontend && ./node_modules/.bin/tsc --noEmit
```
Strict TypeScript compilation with zero type errors.

### Run Analytics Pipeline (dbt Core)
```bash
cd dbt
dbt run
dbt test
```

### Run Load Testing (Locust)
```bash
locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless --host http://localhost:8000
```
- **Performance Targets**: p95 TTFT < 200ms, error rate < 1%.

---

## Security & Isolation Controls

- **Row-Level Security (RLS)**: Enforced in PostgreSQL via `tenant_id` session variables.
- **Credential Protection**: Zero secrets committed to source control; `.env` is ignored.
- **Defense in Depth**: OWASP security headers (`HSTS`, `CSP`, `X-Frame-Options`, `X-Content-Type-Options`).
- **Rate Limiting**: Sliding-window rate limiting (60 requests/minute/IP).
- **PII Protection**: Automated Presidio PII entity detection and redaction prior to vector indexing.
- **Input Validation**: Strict schema validation with 1,000-character maximum query limits.

---

## License

This project is licensed under the MIT License.
