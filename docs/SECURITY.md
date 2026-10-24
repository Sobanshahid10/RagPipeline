# Security policy and verification

Security controls are implemented in source and tested locally; deployment configuration must also be verified. See [upgrade and rollout instructions](SECURITY_REMEDIATION.md) before exposing an existing installation.

| Control | Implementation and verification |
|---|---|
| JWT Secret Length | Production requires an explicitly configured unique secret of at least 32 characters; 64 random hex characters are recommended. Known development secrets are rejected. |
| No Hardcoded Secrets | Credentials belong in ignored `.env`. `.env.example` lists names only. Production Compose requires explicit passwords. TLS keys are ignored. Development-only database defaults must never be used for production. |
| OWASP Security Headers | Backend and frontend return browser protection headers. Nginx terminates TLS using deployment-provided certificates. Local development uses HTTP. |
| Row-Level Security | Tenant tables enforce RLS. The restricted runtime role cannot bypass it. Every standalone tenant transaction sets its own context; authentication uses the current database user rather than trusting a caller-supplied workspace. Tests exercise actual PostgreSQL roles. |
| Rate Limiting | Redis-shared counters enforce 60 API requests/minute/IP and 10 login/register requests/minute/IP. Health liveness and preflight are exempt. Nginx replaces forwarded client headers. Production fails closed if Redis is unavailable; the development fallback has bounded memory. |
| Redis Password | Production Redis requires the configured password and has no public port. Development ports bind to loopback. |
| Input Validation | Backend uploads validate supported file types, bytes, page/ZIP expansion limits and workspace quota; worker execution and text/chunk counts are bounded. Password registration rejects inputs exceeding bcrypt's 72-byte limit. |
| XSS Prevention | React renders text without raw HTML. Markdown link protocols are allowlisted. PDF originals require authenticated downloads. PII masking is a separate privacy control, not HTML sanitization. |

Document writes require an editor or administrator role. Administrator telemetry is authenticated. Upload/retry/delete audit events contain identifiers, not extracted document contents. Users can delete their own stored interactions. Raw exceptions are not returned to clients; error responses carry a request ID.

Public-book and tenant-upload retrieval remain distinct. The selected corpus and generation provider never change silently. Structural citation validation and a model-based source-support audit run before output is published. This is not a mathematical grounding guarantee or completed formal G-Eval. Answer caching is disabled until permission, corpus, model, and provenance boundaries can be implemented safely.

Report vulnerabilities privately to the repository maintainers through an established contact channel. Do not put credentials or private documents in public issues.
