# Production RAG Pipeline

A production-grade, multi-tenant Retrieval-Augmented Generation (RAG) platform designed for reliability, strict data isolation, and low-latency retrieval. Built on **FastAPI**, **PostgreSQL 16 (pgvector)**, **Redis**, **Celery**, and **Docker**.

---

## Highlights & Capabilities

- **Strict Multi-Tenant Isolation**: Tenant data separation enforced at the database layer using PostgreSQL Row-Level Security (RLS) and cryptographically signed JWTs.
- **Tri-Hybrid Retrieval Engine**: Fuses lexical BM25 (`tsvector`), dense semantic vector search (`pgvector` HNSW cosine), and entity-relationship GraphRAG via Reciprocal Rank Fusion (RRF).
- **Sub-35ms Late-Interaction Reranking**: ColBERTv2 / cross-encoder token-level late interaction matrix scoring to maximize precision before LLM generation.
- **Layout-Aware Vision Ingestion**: Document parsing via Docling with table structure preservation and Microsoft Presidio automated PII masking.
- **Asynchronous Processing**: Background document chunking, embedding generation, and graph extraction powered by Celery and Redis.
- **Continuous Quality Evaluation**: Query latency tracking (TTFT), hallucination detection, and RAGAS metrics (Faithfulness, Context Precision, Answer Relevancy).

---

## System Architecture

The platform operates across three decoupled planes sharing PostgreSQL and Redis infrastructure:

```
                      ┌─────────────────────────────────────────┐
                      │           Next.js / Client UI           │
                      └────────────────────┬────────────────────┘
                                           │
                                  REST API / SSE Stream
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. Serving Plane (FastAPI Gateway)                                                     │
│                                                                                        │
│   [Auth & RLS Context] ──► [Presidio PII Masking] ──► [Redis Semantic Vector Cache]    │
│                                                                     │ (Cache Miss)     │
│                                                                     ▼                  │
│   [RRF Fusion & ColBERT Reranker] ◄── [Tri-Hybrid Engine (BM25 + pgvector + GraphRAG)] │
│                 │                                                                      │
│                 ▼                                                                      │
│   [LLM Generator (Gemini / GPT-4o)] ──► [SSE Token Streamer with Bounding Boxes]       │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. Asynchronous Ingestion Plane (Celery + Redis)                                       │
│                                                                                        │
│   [Raw PDF / DOCX] ──► [Docling Vision Parser] ──► [Sentence-Aware Semantic Chunker]   │
│                                                              │                         │
│                                                              ▼                         │
│   [PostgreSQL HNSW & TSVector Indexer] ◄── [Contextual Summary Injection & Embeddings] │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. Observability & Evaluation Plane                                                    │
│                                                                                        │
│   [OpenTelemetry Traces] ──► [Query Interaction Logs] ──► [RAGAS LLM-as-a-Judge Evals] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart

### Prerequisites

- **Docker** & **Docker Compose** (recommended)
- Alternatively: **Python 3.11+**, PostgreSQL 16 with pgvector extension, and Redis 7+

### 1. Clone & Configure Environment

```bash
git clone https://github.com/Sobanshahid10/RagPipeline.git
cd RagPipeline

# Copy sample environment configuration
cp .env.example .env
```

### 2. Start the Infrastructure (Docker Compose)

Start all services (PostgreSQL with pgvector, Redis, FastAPI Backend, Celery Worker):

```bash
docker-compose up -d --build
```

Verify service status:

```bash
docker-compose ps
```

Once running, the services are available at:
- **FastAPI Backend & API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **PostgreSQL Database**: `localhost:5432` (`rag_db`)
- **Redis Cache & Broker**: `localhost:6379`

---

## Local Development Setup

If running or developing without Docker:

```bash
# 1. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install backend dependencies
pip install --upgrade pip
pip install -r backend/requirements.txt

# 3. Launch the FastAPI development server
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Authentication & Multi-Tenancy

Every tenant organization is fully isolated in PostgreSQL. Requests require a signed JWT bearer token containing tenant and user metadata, which automatically activates the database session variable `app.current_tenant_id` for Row-Level Security (RLS).

### 1. Register a New Organization & Admin Account

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
     -H "Content-Type: application/json" \
     -d '{
       "email": "admin@acme.corp",
       "password": "SuperSecretPassword123!",
       "tenant_name": "Acme Corporation"
     }'
```

**Response (200 OK):**
```json
{
  "id": "7b0a8520-7f2a-4a8f-b989-13834eb7b6f1",
  "email": "admin@acme.corp",
  "tenant_id": "90e0c3ab-09b3-469a-bdfd-7c2db95c8ec2",
  "roles": ["admin"],
  "is_active": true,
  "created_at": "2026-08-16T00:58:00Z",
  "tenant": {
    "id": "90e0c3ab-09b3-469a-bdfd-7c2db95c8ec2",
    "name": "Acme Corporation",
    "slug": "acme-corporation",
    "created_at": "2026-08-16T00:58:00Z"
  }
}
```

### 2. Obtain an Access Token (OAuth2 Login)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@acme.corp&password=SuperSecretPassword123!"
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Fetch Current Authenticated User Profile

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
     -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

## PostgreSQL Row-Level Security (RLS)

Multi-tenancy is guaranteed at the database engine level via RLS policies defined in `backend/db/init.sql`.

```sql
-- RLS Policy Example on Chunks Table
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;

CREATE POLICY chunks_tenant_isolation ON chunks
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
```

When an authenticated user issues a request, FastAPI sets the session variable before executing queries:
```sql
SET LOCAL app.current_tenant_id = '<user_tenant_id>';
```
Any query executed in that transaction will only see rows belonging to `<user_tenant_id>`, making cross-tenant data leaks impossible even if application filters are omitted.

---

## Directory Structure

```
.
├── backend/
│   ├── Dockerfile                 # Python 3.11 container definition
│   ├── requirements.txt           # Pinned production dependencies
│   ├── pytest.ini                 # Pytest configuration
│   ├── app/
│   │   ├── main.py                # FastAPI entry point & router mounting
│   │   ├── config.py              # Pydantic Settings (.env loader)
│   │   ├── celery_app.py          # Celery worker & priority queues
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # /register, /login, /me endpoints
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # Bcrypt password hashing & JWT handlers
│   │   │   └── dependencies.py    # get_current_user auth dependency
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── session.py         # Async SQLAlchemy engine & RLS session provider
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py            # SQLAlchemy DeclarativeBase
│   │   │   └── user.py            # Tenant & User ORM models
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── auth.py            # Pydantic request/response schemas
│   │   ├── ingestion/
│   │   │   └── chunking.py        # Sentence-aware chunking & token counter
│   │   └── retrieval/
│   │       ├── fusion.py          # Reciprocal Rank Fusion (RRF)
│   │       └── reranker.py        # Cross-encoder late-interaction reranker
│   ├── db/
│   │   └── init.sql               # PostgreSQL extensions, schema, indexes, RLS
│   └── tests/
│       ├── conftest.py            # Async test database fixtures & client
│       ├── test_api.py            # Health & system info tests
│       ├── test_auth.py           # Registration, login, token, and RLS tests
│       ├── test_chunking.py       # Sentence segmentation and chunking tests
│       ├── test_day1_verification.py # Day 1 scaffold integrity tests
│       └── test_retrieval.py      # RRF fusion & reranker unit tests
├── docker-compose.yml             # Orchestrates Postgres, Redis, App, Celery
├── PLAN.md                        # 12-Day Step-by-Step Execution Plan
└── README.md
```

---

## Running the Automated Test Suite

All test suites can be executed inside the virtual environment:

```bash
# Run all tests with verbose output
pytest backend/tests/ -v

# Run authentication and multi-tenancy tests specifically
pytest backend/tests/test_auth.py -v
```

### Verified Test Cases

- **Authentication Suite (`tests/test_auth.py`)**:
  - `test_register_new_user`: Organization & admin user creation with hashed credentials
  - `test_login_correct_credentials`: OAuth2 login and JWT bearer token issuance
  - `test_login_wrong_password`: 401 Unauthorized on credential mismatch
  - `test_get_me_with_valid_token`: Profile retrieval for authenticated sessions
  - `test_get_me_without_token`: 401 Unauthorized rejection on missing headers
  - `test_get_me_with_malformed_token`: 401 Unauthorized rejection on invalid JWT signatures
  - `test_register_duplicate_email`: 400 Bad Request prevention on duplicate accounts
  - `test_multi_tenant_isolation`: Cross-tenant boundary and token claim verification
- **Ingestion & Retrieval Suite**:
  - Sentence-aware semantic boundary chunking
  - Reciprocal Rank Fusion (RRF) merging
  - Cross-encoder reranking score validation
  - Day 1 scaffold and database schema integrity verification

---

## License

This project is licensed under the MIT License.
