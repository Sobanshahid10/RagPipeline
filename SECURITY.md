# Security Policy & Production Verification Checklist

This document details the security posture, hardened controls, and verification steps for the Production RAG Pipeline.

---

## Verifiable Security Controls Checklist

| # | Security Control | Verification Procedure / Command | Status |
|:---|:---|:---|:---:|
| 1 | **JWT Secret Length (≥ 64 chars)** | `echo -n "$JWT_SECRET" \| wc -c` (must be ≥ 64 in production env) | [x] Verified |
| 2 | **No Hardcoded Secrets in Git** | `git log --all --oneline \| head -20` and scanning with `detect-secrets` | [x] Verified |
| 3 | **OWASP Security Headers** | `curl -I http://localhost:8000/health \| grep -E "X-Content\|X-Frame\|Strict"` | [x] Verified |
| 4 | **PostgreSQL Row-Level Security (RLS)** | Multi-tenant isolation tests in `test_auth.py` verifying cross-tenant query blocks | [x] Verified |
| 5 | **Active Rate Limiting** | `for i in {1..70}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done \| grep -c 429` | [x] Verified |
| 6 | **Redis Password Protection & Isolation** | Redis configured with `--requirepass` and bound to internal Docker bridge network (`rag_net`) | [x] Verified |
| 7 | **Input Validation & Max Length Enforcement** | Send query with >1000 characters to `POST /api/v1/query`, returns `422 Unprocessable Entity` | [x] Verified |
| 8 | **XSS Prevention in Ingested Content** | HTML and dangerous script tags sanitized; Presidio PII redaction and plain text chunking | [x] Verified |

---

## Detailed Control Verification Procedures

### 1. JWT Secret Cryptographic Strength
- **Requirement:** `JWT_SECRET` must be set to a secure, randomly generated string of at least 64 characters (e.g. `openssl rand -hex 32`).
- **Verification Command:**
  ```bash
  echo -n "$JWT_SECRET" | wc -c
  ```
- **Pass Criteria:** Return value $\ge 64$.

### 2. Secret Exposure Prevention
- **Requirement:** Zero API keys, passwords, or credentials stored in git repositories.
- **Verification Command:**
  ```bash
  git log -p -n 50 | grep -E "(API_KEY|SECRET|PASSWORD)\s*=\s*['\"][A-Za-z0-9_]{10,}"
  ```
- **Pass Criteria:** Zero hits for real credentials. All env files rely on `.env.example` templates.

### 3. Security Headers Enforcement
- **Requirement:** Responses must return standard browser defense headers.
- **Headers Enforced:**
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `X-XSS-Protection: 1; mode=block`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Content-Security-Policy: default-src 'self'; frame-ancestors 'none';`
- **Verification Command:**
  ```bash
  curl -I http://localhost:8000/health
  ```

### 4. Multi-Tenant Row Level Security (RLS)
- **Requirement:** Chunks, documents, entity triples, and query logs must be strictly isolated by `tenant_id` via PostgreSQL RLS policies.
- **Verification Command:**
  ```bash
  ./.venv/bin/pytest backend/tests/test_auth.py -k test_multi_tenant_isolation -v
  ```
- **Pass Criteria:** User from Tenant A cannot view or retrieve data owned by Tenant B under any circumstance.

### 5. API Rate Limiting (DDoS & Abuse Defense)
- **Requirement:** 60 requests/minute sliding window per client IP on public and authenticated routes.
- **Verification Command:**
  ```bash
  for i in {1..70}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done | grep -c 429
  ```
- **Pass Criteria:** Returns HTTP 429 when rate threshold is exceeded.

### 6. Redis Infrastructure Hardening
- **Requirement:** Redis requires authentication (`--requirepass`) and is only reachable within the isolated Docker bridge network `rag_net`.
- **Pass Criteria:** Direct connection without password fails with `(error) NOAUTH Authentication required.`

### 7. Input Constraint & Schema Validation
- **Requirement:** Max character lengths and type validations strictly checked by Pydantic before processing or embedding.
- **Verification:** Sending 1001 characters to `/api/v1/query` returns HTTP 422.

### 8. XSS & Payload Sanitization
- **Requirement:** Document parsers extract clean structured plain text without executing scripts. Presidio masks PII before LLM prompting or embedding.
- **Verification:** Search chunks database for `<script` tags: zero occurrences.

---

## Reporting Vulnerabilities
Please report any security vulnerabilities directly to `security@ragpipeline.local`.
