# Security and reliability remediation — 23 October 2026

The application now authenticates every document operation, derives the workspace from the database user, enforces editor/admin writes, and scopes standalone PostgreSQL transactions. Upload hashes are unique within a tenant. The runtime database role has no superuser or RLS bypass privileges, and production startup rejects privileged runtime connections.

Ingestion uses persistent shared upload storage in both Compose configurations. Upload validation enforces size/type/page/ZIP expansion limits and workspace storage quotas. Queue dispatch failures are visible; failed and stalled documents can be retried. A document lock prevents competing ingestion/delete/retry operations, and retries replace partial chunks rather than appending duplicates. Only indexed documents participate in retrieval. Graph failures are reported separately; provider extraction is capped at 128 chunks per document by default, with a limited status for larger documents. Coordinates are omitted when a reliable chunk-to-region mapping is unavailable.

Provider errors never create synthetic vectors. New cache keys and document metadata identify the actual embedding model/version. Legacy embeddings require reindexing. Unsafe semantic answer caching and unused HyDE/expansion work have been disabled. Selected answer models never silently change provider or append replacement streams.

Document and public-book source selection is explicit. Both paths check citations and use a separate model-based source-support audit before publishing an answer. Draft text is buffered until checks finish. This adds a second generation request and response latency. An LLM auditor is a quality gate, not a proof of truth or a completed formal G-Eval implementation; check the cited evidence for consequential decisions.

Chat history is keyed by verified tenant/user, and tokens use session storage. Account switches cancel pending requests. Local legacy shared history is discarded because it cannot be safely attributed to an account. Settings offer local history clearing and deletion of the current user's server interactions. Original uploaded files are retained until deleted. Identifier-only upload/retry/delete events remain available to workspace administrators.

The UI no longer exposes inert retrieval controls, fabricated tenant values, mock graph triples, demo credentials, hardcoded timing badges, or unconditional security assurances. It shows configured answer providers, actual model information, source scope, job stages, errors, and retry actions. Public-book citations open passages instead of document-file endpoints. Document-scoped questions and bounded, owned conversation context are supported.

Shared Redis counters enforce API/login limits and daily workspace question budgets. Forwarded headers are normalized by Nginx; API processes do not read arbitrary client-supplied X-Forwarded-For headers. Production requires Redis and HTTPS and fails closed when rate/usage accounting is unavailable. Public health is liveness only; authenticated administrator health includes workers and treats missing workers as degraded.

## Existing database upgrade

These are deployment steps, not changes automatically applied to the user's existing data. Back up the database and uploaded originals first. Never delete existing database or upload volumes to apply this upgrade.

1. Put unique values in the ignored root `.env`: `JWT_SECRET` (at least 32 characters, preferably 64 random hex characters), `RUNTIME_DB_PASSWORD`, and production database/Redis administrator passwords. Use URL-safe secrets where Compose interpolates them into connection URLs. Keep real credentials out of Git and the frontend.
2. Preserve and copy any existing container-local uploaded originals into the new shared `uploads` volume, preserving their database paths under `/app/storage/uploads`. Existing files saved outside the configured upload root need a controlled storage-path migration. Containers cannot recover originals already lost when old containers were removed.
3. Recreate the database service using the updated Compose configuration so it receives the runtime-password environment variable and initialization-script mounts. Existing database volumes are preserved. Initialization scripts only run automatically on empty volumes.
4. For existing volumes, run the runtime-role provisioning script explicitly, then the migration and grants as the database administrator. With the development Compose defaults:

   ```sh
   docker compose exec -T postgres sh /docker-entrypoint-initdb.d/00_runtime_role.sh
   docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U rag_user -d rag_db < backend/db/migrations/20261023_security.sql
   docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U rag_user -d rag_db < backend/db/migrations/20261023_review.sql
   docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U rag_user -d rag_db < backend/db/zz_runtime_grants.sql
   ```

   For production use `-f docker-compose.prod.yml` and substitute the configured administrator/database names. New empty databases provision the role, schema, and grants automatically. The role-creation script deliberately does not rotate an existing role's password; coordinate an explicit rotation if it already exists with different credentials.
5. Set host-run services' `DATABASE_URL` to the restricted `rag_runtime` account on development port 5433. Compose services already use this account internally. Restart both API and worker after configuration changes.
6. The migration marks indexed documents without embedding provenance as failed with a reindex-required message. Retry them from Documents after providers and privacy models are configured. Old Redis vector keys are ignored by the new `emb:v2:` namespace. Other indexed documents with a different provider/model identity must also be reindexed before retrieval can resume; use Reindex document in the document details drawer.

No existing user database, original document, credential, or index was changed by the verification work. Migrations were exercised only on an isolated PostgreSQL test database.

## Production prerequisites

- Mount a valid TLS certificate and key at `nginx/certs/fullchain.pem` and `nginx/certs/privkey.pem`; this directory is ignored by Git. HTTP redirects to HTTPS. Certificates must be provisioned for the deployment's hostname.
- Set `CORS_ORIGINS` to a JSON array of the allowed HTTPS frontend origins and `ENVIRONMENT=production`. Required passwords and signing secrets have no production fallback. Do not expose the backend directly: its production proxy trust assumes the internal network and normalized Nginx headers.
- Install the Presidio English NLP model for host-run workers: `python -m spacy download en_core_web_sm`. The backend image installs it during build. Missing privacy protection stops ingestion by default. Do not disable required privacy protection for production.
- Configure an embedding provider and the answer providers you intend to use. Available model choices mean the provider is configured, not that a live quota check has succeeded. Provider availability/quota calls were mocked during verification.
- The generic backend image still does not include the public-book source, generated artifacts, cached MiniLM model, or PostgreSQL public-book index. Provision those separately for `/public-book`. Reapply the SELECT grants after creating its two public tables; indexing uses a separate migration/admin connection.
- Optional negative-interaction mining is no longer scheduled or imported by the generic worker. Manual mining defaults to ignored `storage/private/evaluation/`; do not publish tenant interactions as a public evaluation corpus.

## Dependency updates

The frontend image uses [Node.js 24 LTS](https://nodejs.org/en/about/previous-releases). Docker build contexts exclude local dependencies, generated builds, environment files, and backend uploads.

Next.js and its ESLint configuration were upgraded to 16.4.3, and compatible transitive packages were refreshed; npm audit reported no known vulnerabilities afterward. The maintainer's [image optimization advisory](https://github.com/vercel/next.js/security/advisories/GHSA-2464-fhr4-w9xw) describes one of the patched issues.

JWT handling now uses PyJWT with a fixed HS256 allowlist and required expiration/issued-at/subject claims. This removes the unpatched python-jose dependency and its ecdsa dependency from the application; see the [python-jose advisory](https://github.com/advisories/GHSA-3qf3-8w2g-rqmx). Existing properly issued HS256 tokens remain compatible. Backend image builds upgrade pip/setuptools before installing dependencies. The isolated Python verification environment was audited separately; that does not cover heavy optional parser/model dependencies absent from that environment.

## Verification

- Backend unit/contract/security suite, with all provider credentials disabled or mocked.
- Isolated real PostgreSQL tests for RLS under a restricted role, cross-tenant API operations, tenant-scoped deduplication, retries, graph degradation, deletion, audit/history isolation, and document filters in lexical/vector/graph searches.
- Frontend TypeScript, production build, URL/history regression tests, and browser checks of sign-in, chat, source scope, settings, and an authenticated PDF preview. PDF workers are served from the local application bundle. The Node 24 frontend image built successfully and served HTTP 200 on its configured container port.

Verification completed with 158 backend tests (including five real PostgreSQL scenarios), two frontend security tests, TypeScript and the production build. npm audit reported zero known vulnerabilities, as did the separate Python test-environment audit. The live worker check exercised visible failure without a configured provider.

No paid provider calls were made. Deployment certificate provisioning, actual provider quota/availability, and migration/reindexing of existing user data remain environment-specific rollout steps.

## Implementation follow-up — 24 October 2026

A second review corrected queued-job races using a unique attempt ID on every upload/reindex. Older deliveries cannot process newer attempts, and late queue errors cannot overwrite active or completed processing. API and worker must be restarted together. Pending uploads interrupted before publication remain visible and can be retried once marked stalled; dispatch is not a transactional outbox.

File deletion now commits the database removal before removing the original. A failed database commit preserves the original. An operating-system cleanup failure is logged and can leave an inaccessible file requiring operator cleanup; database and filesystem changes are not a distributed transaction. Uploads preserve originals when cancellation makes the commit outcome uncertain.

Every graph traversal edge now comes from indexed documents within the selected scope. Conversation turns persist their document scope; follow-up retrieval excludes turns from other scopes and legacy turns whose scope is unknown. Apply `20261023_review.sql` on existing databases before restarting the API. Clearing a chat rotates its conversation ID. The document picker refreshes in the background and ignores account-stale responses.

Citation checks now require citations for each prose paragraph/list item on both RAG paths. Evidence audits require the JSON boolean `true`, rather than accepting the number `1`. These remain structural and model-based checks, not a formal guarantee of semantic grounding. Public-book requests check deployment prerequisites and provider configuration before reserving daily quota.

Authentication publishes a token only after its account profile is verified, and cancelled restores/sign-ins cannot revive a logged-out identity. Password hashing/verification runs outside the API event loop. Registration slugs fit the database limit, whitespace-only workspace names are rejected, and conflicting registrations roll back cleanly.

Follow-up verification includes real isolated PostgreSQL tests for stale deliveries, late dispatch failures, scoped graph bridges, and conversation scope, plus isolated Redis tests for shared rate limits and concurrent tenant budgets. No existing user database or credentials were changed, and no paid provider requests were made.

The follow-up suite passed **180 backend tests**, including eight PostgreSQL scenarios and three Redis/security scenarios. Both frontend security tests, TypeScript, and the production build passed. Local checks returned API health 200, unauthenticated documents 401, and the chat route 200; isolated live registration/sign-in/profile/document-list checks also passed. Temporary verification services were removed afterward.
