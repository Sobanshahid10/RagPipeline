# Production RAG Pipeline

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform designed for enterprise reliability, strict data isolation, and sub-second streaming answers with verifiable bounding-box citations.

Built on **FastAPI**, **PostgreSQL 16 (pgvector + Recursive CTEs)**, **Redis 7**, **Celery**, **Next.js 14**, **OpenTelemetry**, **RAGAS**, and **dbt Core**.

---

## Highlights & Capabilities

- **Strict Multi-Tenant Isolation**: Cryptographically verified JWT bearer tokens inject tenant IDs into database session variables to enforce PostgreSQL Row-Level Security (RLS) across all tables.
- **Tri-Hybrid Retrieval Engine**: Parallel `asyncio.gather()` execution combining:
  1. Lexical search via PostgreSQL `tsvector` + BM25 ranking (`ts_rank_cd`).
  2. Dense semantic vector search via PostgreSQL `pgvector` HNSW cosine similarity.
  3. Knowledge graph multi-hop entity traversal via recursive Common Table Expressions (CTEs).
- **Agentic Pre-Retrieval Layer**:
  - Redis vector semantic cache (sub-15ms hits on semantically duplicate queries).
  - Hypothetical Document Embeddings (HyDE) for intent grounding.
  - Multi-query expansion (3 parallel variants).
  - Dynamic strategy routing (`FACTUAL_VECTOR`, `MULTI_HOP_GRAPH`, `ANALYTICAL_SQL`, `GREETING_DIRECT`).
- **Reciprocal Rank Fusion (RRF) & Cross-Encoder Reranking**: Consensus-based ranking ($k=60$) followed by ONNX cross-encoder reranking and contextual prompt compression.
- **SSE Streaming with Bounding-Box Grounding**: Real-time Server-Sent Events (SSE) emitting token streams and interactive citation chips referencing exact PDF bounding boxes.
- **Next.js 14 Interactive Frontend**: Modern dark-mode interface with streaming chat, document upload library, and an interactive PDF viewer highlighting cited text.
- **Full Observability & Analytics**: Distributed OpenTelemetry tracing with Jaeger UI, live admin metrics dashboard, and dbt analytics marts for latency percentiles (p50/p95/p99) and token consumption.
- **Automated CI/CD Evaluation**: Fast PR evaluation gates, nightly RAGAS suites (Faithfulness, Context Precision/Recall, Answer Relevancy), and feedback-driven hard-negative mining.
- **Production Hardened**: Automated sliding-window rate limiting (60 req/min/IP), OWASP security headers (HSTS, CSP, X-Frame-Options), Nginx reverse proxy load balancer, and 100-user Locust load testing suite.

---

## System Architecture

```
[ Next.js 14 Chat UI ]  ←──── SSE Token Stream + Citation Bounding Boxes
        │
        │ HTTPS
        ▼
[ Nginx Reverse Proxy (Load Balancer) ]
        │
        ▼
[ FastAPI Gateway ]
  ├─ JWT Auth + RLS Tenant Injection (`app.current_tenant_id`)
  ├─ Presidio PII Masking & Anonymization
  └─ Sliding-Window Rate Limiter (60 req/min/IP)
        │
        ├────────────────────────────────────────── [Cache HIT < 15ms]
        │                                                  │
        ▼                                          [ Redis Semantic Cache ]
[ Agentic Query Pipeline ]
  ├─ Strategy Classifier (FACTUAL / GRAPH / SQL / DIRECT)
  ├─ HyDE Document Embedding Generator
  └─ Multi-Query Expander (3 variants)
        │
        ▼
[ Tri-Hybrid Retrieval Engine — asyncio.gather() ]
  ├─ BM25 TSVector Search        (PostgreSQL 16)
  ├─ pgvector HNSW Dense Search  (PostgreSQL 16 + pgvector)
  └─ GraphRAG Recursive CTE      (PostgreSQL entity_triples)
        │
        ▼
[ Reciprocal Rank Fusion (RRF, k=60) ]
        │
        ▼
[ ONNX Cross-Encoder Reranker — ms-marco-MiniLM-L-6-v2 ]
        │
        ▼
[ Contextual Compressor & Prompt Assembly ]
        │
        ▼
[ LLM Grounded Generator (Groq GPT-OSS 120B / Gemini 2.0 Flash) ]
        │
        ├──► SSE Token Stream ──────────────► Next.js Chat UI
        ├──► Citation BBox Events ──────────► PDF Canvas Viewer
        └──► OpenTelemetry Traces ──────────► Jaeger UI + LangFuse
                                                    │
                                                    ▼
                                          [ Postgres Interaction Logs ]
                                                    │
                                                    ▼
                                          [ dbt Analytics Pipeline ]
                                          [ RAGAS Nightly CI/CD Gate ]
                                          [ Hard-Negative Miner Worker ]
```

---

## Technology Stack

| Layer | Technology | Description |
|:---|:---|:---|
| **API Framework** | FastAPI 0.110+ & AsyncPG | High-performance asynchronous REST & SSE streaming |
| **Database & Vector Store** | PostgreSQL 16 + `pgvector` | HNSW cosine indexing, BM25 TSVector, and Recursive CTEs |
| **Cache & Task Broker** | Redis 7 Alpine | Semantic vector cache and Celery task broker |
| **Worker Queue** | Celery 5.3+ | Background vision parsing, embedding batching, and graph extraction |
| **Document Ingestion** | Docling & Microsoft Presidio | Layout-aware vision parsing and automated PII anonymization |
| **Frontend Application** | Next.js 14 (App Router) + TypeScript | Streaming chat UI, react-pdf viewer, and admin dashboard |
| **Observability** | OpenTelemetry & Jaeger | Distributed span tracing per pipeline stage |
| **Evaluation Suite** | RAGAS & Pytest | Automated LLM-as-a-judge quality metrics |
| **Data Warehouse / Marts** | dbt Core (PostgreSQL) | Daily performance marts, latency percentiles, and token accounting |
| **Load Testing** | Locust | 100-user concurrent streaming and ingestion load testing |
| **Production Proxy** | Nginx Alpine | Reverse proxy, unbuffered SSE pass-through, and SSL termination |

---

## Quickstart

### Prerequisites
- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/) installed.
- (Optional for local development) Python 3.11+ and Node.js 20+.

### 1. Clone & Configure Environment
```bash
git clone https://github.com/Sobanshahid10/RagPipeline.git
cd RagPipeline

# Create environment configuration
cp .env.example .env
```

### 2. Run the Development Stack
```bash
docker-compose up -d --build
```

Services will be live at:
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Next.js Web UI**: [http://localhost:3000](http://localhost:3000)
- **Jaeger Tracing UI**: [http://localhost:16686](http://localhost:16686)
- **PostgreSQL Database**: `localhost:5432` (`rag_db`)
- **Redis Broker**: `localhost:6379`

### 3. Run the Production Stack
```bash
docker-compose -f docker-compose.prod.yml up -d --build
```
The production stack boots Nginx on ports `80`/`443`, 2 backend replicas with resource limits (1 CPU / 1GB RAM), password-authenticated Redis, and non-reloading production uvicorn workers.

---

## Authentication & Multi-Tenancy

Every tenant organization is fully isolated in PostgreSQL via Row-Level Security (RLS).

### Register a New Tenant & Admin User
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@acme.corp",
       "password": "SuperSecretPassword123!",
       "tenant_name": "Acme Corporation"
     }'
```

### Obtain a JWT Bearer Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@acme.corp&password=SuperSecretPassword123!"
```

---

## Core API Endpoints

| Method | Endpoint | Description | Auth Required |
|:---|:---|:---|:---:|
| `GET` | `/health` | Service health status | No |
| `GET` | `/api/v1/info` | System metadata and environment | No |
| `POST` | `/api/v1/auth/register` | Create tenant and admin account | No |
| `POST` | `/api/v1/auth/login` | Obtain JWT access token | No |
| `GET` | `/api/v1/auth/me` | Current authenticated user profile | Yes |
| `POST` | `/api/v1/documents/upload` | Upload document for async parsing and indexing | Yes |
| `GET` | `/api/v1/documents/{id}` | Check document parsing/indexing status | Yes |
| `POST` | `/api/v1/retrieval/search` | Tri-hybrid retrieval endpoint (BM25 + Vector + Graph) | Yes |
| `POST` | `/api/v1/query` | SSE streaming grounded query with citations | Yes |
| `POST` | `/api/v1/query/{id}/feedback` | Record thumbs-up / thumbs-down interaction feedback | Yes |
| `GET` | `/api/v1/admin/stats` | Latency percentiles, cache hit rate, token volume | Yes |

---

## Evaluation & Quality Gates (RAGAS & CI/CD)

The pipeline includes a 200+ sample golden dataset ([evaluation/golden_dataset.json](file:///Users/muhammadomerfarooq/Desktop/GitHub%20Repositories/RAG%20Pipeline/evaluation/golden_dataset.json)) spanning 5 domains (`HR_Policy`, `Technical_Docs`, `Financial_Reports`, `Legal_Contracts`, `Onboarding`) across easy, medium, and hard multi-hop queries.

### Run Fast Quality Gate (< 60s)
```bash
python evaluation/assert_thresholds.py --metric recall_at_5 --min 0.75
python evaluation/assert_thresholds.py --metric max_ttft_ms --max 500
python evaluation/assert_thresholds.py --metric citation_parse_success_rate --min 0.95
```

### Run Full RAGAS Suite
```bash
python evaluation/run_ragas.py --dataset evaluation/golden_dataset.json
```

### Hard-Negative Mining
The periodic worker ([evaluation/hard_negative_miner.py](file:///Users/muhammadomerfarooq/Desktop/GitHub%20Repositories/RAG%20Pipeline/evaluation/hard_negative_miner.py)) queries thumbs-down interactions every 6 hours, prompts the LLM to diagnose failure modes (`retrieval_fail`, `hallucination`, `context_loss`, `wrong_route`), and automatically appends corrected samples to the golden dataset.

---

## Analytics Pipeline (dbt Core)

Analytics models transform raw query logs and evaluation scores into daily performance tables and executive reporting marts:

```bash
cd dbt
dbt run
dbt test
```

- **`stg_query_interactions`**: 90-day cleaned query logs.
- **`stg_eval_scores`**: Staging evaluation metrics.
- **`fct_daily_performance`**: Daily aggregates including total queries, avg/p50/p95/p99 TTFT, token totals, thumbs-up satisfaction rate, and cache hit rate.
- **`rpt_eval_dashboard`**: Evaluation reporting mart for faithfulness, relevancy, and hallucination rates.

---

## Load Testing (Locust)

Load test the platform under 100 concurrent streaming users:

```bash
locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless --host http://localhost:8000
```
- **Pass Criteria**: p95 TTFT < 200ms, error rate < 1%.

---

## Security Hardening

Security controls are documented and verified in [SECURITY.md](file:///Users/muhammadomerfarooq/Desktop/GitHub%20Repositories/RAG%20Pipeline/SECURITY.md):
- Minimum 64-character JWT secrets.
- Zero secrets committed to git.
- OWASP security headers (`HSTS`, `CSP`, `X-Frame-Options`, `X-Content-Type-Options`).
- PostgreSQL Row-Level Security tenant isolation.
- Active sliding-window rate limiting (60 req/min/IP).
- Password-authenticated Redis on internal Docker networks.
- Input validation enforcing a maximum query length of 1000 characters (`422 Unprocessable Entity`).
- Strict PII masking with Presidio and XSS payload sanitization.

---

## Directory Structure

```
.
├── backend/
│   ├── Dockerfile                 # Python 3.11 production container definition
│   ├── requirements.txt           # Pinned dependencies
│   ├── pytest.ini                 # Pytest configuration
│   ├── app/
│   │   ├── main.py                # FastAPI entry point & security middleware
│   │   ├── config.py              # Pydantic Settings
│   │   ├── celery_app.py          # Celery worker & priority queues
│   │   ├── api/                   # Auth, Documents, Retrieval, Query, Admin routers
│   │   ├── core/                  # Security, Auth dependencies, Middlewares, Telemetry
│   │   ├── db/                    # Async SQLAlchemy session with RLS injection
│   │   ├── models/                # Tenant, User, Document, Chunk, Triple, Interaction ORMs
│   │   ├── schemas/               # Pydantic validation schemas
│   │   ├── ingestion/             # Parser, Presidio PII, Chunker, Contextual, Embedder, Graph
│   │   ├── retrieval/             # BM25, Vector, Graph traversal, RRF fusion, Reranker, Compressor
│   │   ├── agentic/               # Semantic cache, HyDE, Expander, Router, Pipeline
│   │   └── generation/            # Prompt builder, Citation parser, SSE Streamer
│   ├── db/
│   │   └── init.sql               # PostgreSQL extensions, schema, HNSW/GIN indexes, RLS
│   └── tests/                     # 74 comprehensive unit and integration tests
├── frontend/                      # Next.js 14 App Router application
│   ├── Dockerfile                 # Multi-stage production container
│   ├── app/                       # Chat, Documents, Document Detail, Login, Dashboard
│   ├── components/                # ChatMessage, PDFViewer with highlights, Sidebar, Layout
│   └── lib/api.ts                 # Typed client API library
├── dbt/                           # dbt analytics project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   └── models/                    # Staging views, marts tables, schema tests
├── evaluation/                    # RAGAS eval runners, golden dataset & hard-negative miner
├── nginx/                         # Nginx load balancer reverse proxy configuration
├── docker-compose.yml             # Development compose
├── docker-compose.prod.yml        # Production-hardened compose
├── locustfile.py                  # Load testing definition
├── SECURITY.md                    # Verifiable security checklist
├── PLAN.md                        # Complete 12-day execution roadmap
└── README.md
```

---

## Running the Automated Test Suite

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all 74 unit and integration tests
pytest backend/tests/ -v

# Run Next.js frontend production build check
cd frontend && npm run build
```

---

## License

This project is licensed under the MIT License.
