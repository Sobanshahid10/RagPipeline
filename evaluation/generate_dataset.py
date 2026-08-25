#!/usr/bin/env python3
"""
Golden Dataset Generator for RAG Pipeline Evaluation.
Generates 205 realistic enterprise Q&A pairs covering:
- Categories: HR_Policy, Technical_Docs, Financial_Reports, Legal_Contracts, Onboarding
- Difficulties: 40% easy (single-chunk), 40% medium (2-3 chunks), 20% hard (multi-hop graph)
"""

import json
from pathlib import Path

HR_EASY = [
    ("What is the standard annual paid time off (PTO) allocation for full-time employees in their first year?",
     "Full-time employees in their first year accrue 20 days of paid time off (PTO) annually, accrued at a rate of 1.67 days per month."),
    ("What is the maximum carry-over limit for unused vacation days into the next calendar year?",
     "Employees are permitted to roll over a maximum of 5 unused vacation days into the following calendar year, which must be utilized by March 31st."),
    ("How many days of paid bereavement leave are provided upon the loss of an immediate family member?",
     "The company provides up to 5 consecutive business days of paid bereavement leave for the loss of an immediate family member."),
    ("What is the waiting period before new hires become eligible for company 401(k) retirement matching?",
     "New hires become eligible for the 401(k) company match on the first day of the calendar month following 30 days of continuous employment."),
    ("What percentage does the employer match on 401(k) contributions up to the first 6%?",
     "The company provides a dollar-for-dollar 100% match on the first 3% contributed, and a 50% match on the next 3%, totaling a maximum 4.5% employer match."),
    ("What is the deadline for submitting flexible spending account (FSA) reimbursement claims each plan year?",
     "FSA reimbursement claims must be submitted no later than April 30 following the end of the plan year."),
    ("What is the core working hours window during which employees are expected to be available?",
     "Core working hours are 10:00 AM to 4:00 PM local time, Monday through Friday, for all active teams."),
    ("What is the standard annual educational reimbursement limit per employee for accredited courses?",
     "The company provides up to $5,250 per calendar year in tuition reimbursement for pre-approved, accredited degree or certification courses."),
    ("How many days in advance must an employee submit a request for consecutive PTO exceeding 5 business days?",
     "Requests for consecutive PTO exceeding 5 business days must be submitted in the HR portal at least 3 weeks prior to the intended start date."),
    ("What is the company policy on jury duty wage continuation?",
     "Full-time employees receive their full regular pay for up to 10 working days of served jury duty upon submitting official court summons verification."),
    ("How frequently are formal employee performance appraisals conducted across the organization?",
     "Formal performance reviews and compensation calibrations are conducted biannually in July (Mid-Year) and January (Year-End)."),
    ("What is the maximum stipend provided for ergonomic home office workstation setup?",
     "Remote and hybrid employees are eligible for a one-time home office ergonomic stipend of up to $750 upon joining."),
    ("What is the reporting timeframe for workplace injuries or safety incidents to HR?",
     "All workplace injuries and safety incidents must be reported to HR and Safety Operations within 24 hours of occurrence."),
    ("What is the eligibility requirement for taking parental bonding leave under company policy?",
     "Employees who have completed at least 6 months of continuous full-time service are eligible for 16 weeks of fully paid parental leave."),
    ("What is the annual allowance for employee wellness and gym membership reimbursements?",
     "Employees are entitled to a $600 annual wellness reimbursement ($50/month) for fitness memberships, mindfulness apps, or physical wellness equipment."),
    ("What is the protocol for logging remote sick days in the HRIS portal?",
     "Employees must mark their status as 'Sick Leave' in Workday and notify their direct team lead via Slack prior to 9:00 AM local time.")
]

HR_MEDIUM = [
    ("How does the parental leave policy coordinate with statutory state disability insurance and FMLA?",
     "Company paid parental leave runs concurrently with FMLA job protection; the company tops off state disability benefits to guarantee 100% of base salary for the full 16-week leave duration."),
    ("What are the differences in severance calculation between voluntary redundancy and involuntary termination without cause?",
     "Voluntary redundancy packages provide 2 weeks of base pay per year of service plus 3 months COBRA subsidy, whereas involuntary termination without cause provides 1 week per year of service with 1 month COBRA subsidy subject to a signed release."),
    ("What steps must be followed when an employee transitions from a US entity to an EMEA entity regarding accrued PTO and benefits?",
     "Accrued US PTO is cashed out upon transfer date, US benefits terminate on the final day of the transfer month, and the employee is re-enrolled into the EMEA statutory pension, healthcare scheme, and local 25-day annual leave plan on day one of the new contract."),
    ("How does the performance improvement plan (PIP) process affect the annual merit increase and stock grant vesting schedule?",
     "Employees placed on an active PIP are ineligible for annual merit salary increases or promotional bonuses during that cycle, and discretionary unvested refresher equity grants are frozen until successful PIP completion."),
    ("What is the procedure for obtaining approval for international remote work lasting between 30 and 90 days?",
     "Employees must submit an International Remote Work application to HR Operations and Corporate Tax 60 days in advance, obtain Director-level approval, and confirm tax residency compliance within the destination country."),
    ("How are annual bonus multipliers calculated when individual performance exceeds expectations but company revenue misses the target?",
     "The overall bonus payout is calculated as Base Target Bonus x (Company Factor 70% + Individual Factor 30%); if company performance is at 80% and individual performance is at 130%, the blended multiplier is (0.80*0.70)+(1.30*0.30) = 0.95 (95% payout)."),
    ("What are the prerequisites and repayment obligations for the employee relocation assistance package?",
     "Relocation assistance requires a signed 2-year retention agreement; leaving within 12 months requires 100% repayment, while leaving between 13 and 24 months requires a prorated 50% repayment."),
    ("How does health insurance coverage continue during an unpaid sabbatical leave of up to 6 months?",
     "During an approved unpaid sabbatical, health benefits remain active for up to 90 days with employee pre-paying standard employee premiums, after which coverage transitions to COBRA continuation at 102% total premium cost."),
    ("What documentation and review stages are required before an employee can be reimbursed for international business travel expenses exceeding $5,000?",
     "Expenses exceeding $5,000 require itemized VAT invoices, Department VP approval, Corporate Travel reconciliation in Expensify, and CFO sign-off prior to wire reimbursement."),
    ("How do the guidelines for intellectual property disclosure differ between personal side projects and core company business domains?",
     "Personal side projects in unrelated fields must be disclosed via the Prior Inventions Addendum and developed entirely on personal equipment outside working hours, while any project related to company IP or data belongs exclusively to the employer."),
    ("What is the dispute resolution escalation path for unaddressed harassment grievances?",
     "Grievances escalate from People Partner to VP of HR, then to an independent third-party ombudsman or external legal mediation if unresolved within 14 business days."),
    ("How is military leave compensation handled for reserve training obligations exceeding 15 consecutive days?",
     "The company provides supplemental differential pay bridging military base pay and regular company salary for up to 90 calendar days per calendar year."),
    ("What are the criteria for changing benefit elections outside the annual open enrollment period?",
     "Changes are permitted only upon a Qualifying Life Event (QLE) such as marriage, divorce, birth or adoption of a child, or loss of alternative coverage, submitted with documentation within 30 days."),
    ("How does the employee referral bonus program structure payouts for senior technical and executive positions?",
     "Referral bonuses for senior engineering (L5+) and director roles pay $5,000 total: $2,500 on the candidate's 30th day and $2,500 after 90 days of continuous active employment."),
    ("What protocols govern return-to-office medical accommodations under the Americans with Disabilities Act (ADA)?",
     "Employees must submit an ADA Interactive Accommodation Request with medical certification to the Benefits Team, followed by an interactive dialogue session within 10 business days to determine reasonable adjustments."),
    ("How do executive non-compete clauses interact with garden leave provisions upon resignation?",
     "During the mandatory 90-day garden leave period, the executive remains on full base salary and benefits while access to systems and client communications is immediately suspended."),
    ("What are the tax implications and withholding policies applied to employee equity vesting events (RSUs)?",
     "RSU vesting triggers statutory tax withholding at supplemental wage rates (22% federal, state equivalent, FICA) satisfied automatically via Net Share Settlement (sell-to-cover).")
]

HR_HARD = [
    ("How do the multi-jurisdictional compliance rules resolve when an employee living in France, employed by a UK subsidiary, is seconded to a US project for 8 months regarding pension, social security, and tax equalization?",
     "Under the UK-US and UK-France bilateral treaties, the employee maintains UK National Insurance contributions via an A1/Certificate of Coverage for up to 12 months, applies US dual-status alien tax withholding for US-sourced income, receives full tax equalization under the Global Mobility Policy, and accrues statutory French congés payés top-ups if secondment exceeds 180 continuous days."),
    ("In the event of an acquisition where Company A acquires Company B under a stock purchase agreement, how do unvested double-trigger RSUs vest if an employee is terminated without cause within 12 months following a change in control, and how does the Golden Parachute Section 280G gross-up calculate?",
     "Under double-trigger acceleration clauses, 100% of unvested RSUs immediately vest on the termination effective date; if total severance and equity value exceeds 2.99x base amount under IRC Section 280G, the company applies the 'better-of' cutback provision rather than a gross-up unless an explicit Tier-1 executive indemnity agreement was executed prior to acquisition close."),
    ("When an employee on an H-1B visa undergoes role relocation from a California office to an Austin remote hub during an active PERM labor certification, what legal, LCA, and prevailing wage steps must HR execute to maintain immigration status without resetting PERM?",
     "HR must file a new Labor Condition Application (LCA) for the Austin Metropolitan Statistical Area (MSA), post LCA notices locally for 10 days, file an H-1B Amendment petition with USCIS before relocation, and evaluate whether the PERM recruitment must be refiled if the work location change falls outside the original normal commuting radius."),
    ("How does the company harmonize intellectual property assignments, GDPR subject access rights, and employee privacy rights when conducting an internal forensics audit across corporate Slack, GitHub, and personal Bring-Your-Own-Device (BYOD) accounts?",
     "The audit is constrained by the BYOD MDM Policy: corporate data partitions and MDM logs are subject to full review under enterprise IP rights, while personal communication partitions remain inaccessible; in EU jurisdictions, works council notification and GDPR Article 6(1)(f) legitimate interest assessments must precede any personal identifier data collection."),
    ("How does cross-border executive compensation clawback apply across dual-listed UK/US subsidiaries when restated financial metrics affect multi-year performance share units (PSUs) previously settled?",
     "Under SEC Rule 10D-1 and UK Corporate Governance Code clawback clauses, the Remuneration Committee issues a demand to recover the pre-tax excess PSU shares delivered over the prior 3 fiscal years; unvested tranches are forfeited immediately and realized gains are subject to offset against deferred compensation."),
    ("What are the detailed procedures for resolving a conflicting whistleblower complaint involving cross-entity executive malfeasance that implicates Audit Committee members and international transfer pricing records?",
     "The whistleblower report bypasses internal management and routes to the Lead Independent Director and external Special Legal Counsel; all relevant document destruction holds are frozen across global subsidiaries, and forensic accountants audit cross-entity transfer pricing ledgers independently of internal finance leadership."),
    ("How does the termination of a remote employee in Germany operate under the KSchG (Dismissal Protection Act) when company-wide restructuring eliminates an entire distributed infrastructure team?",
     "HR must conduct a statutory Social Selection (Sozialauswahl) evaluating tenure, age, dependent obligations, and disability across comparable employees, notify the Works Council (Betriebsrat) with detailed justification before notice issuance, and observe the statutory 3-to-7 month notice period without immediate unilateral termination."),
    ("How do equity clawbacks, non-solicitation covenants, and deferred cash bonuses interact when a Senior Director departs to join a direct competitor in a jurisdiction that voids non-competes (e.g., California)?",
     "While California Business and Professions Code 16600 invalidates the non-compete restraint, non-disclosure of trade secrets remains enforceable, unvested equity and deferred cash retention bonuses with active service conditions are forfeited, and bad-faith customer list misappropriation triggers Delaware-governed equity forfeiture remedies.")
]

TECH_EASY = [
    ("What is the default authentication mechanism used by the backend REST API endpoints?",
     "The backend REST API uses Bearer Token authentication via RS256-signed JSON Web Tokens (JWT) passed in the HTTP Authorization header."),
    ("What is the default time-to-live (TTL) for cached query results stored in Redis?",
     "Cached query responses and semantic search results have a default TTL of 3600 seconds (1 hour) in Redis."),
    ("Which embedding model is utilized for generating dense vector representations in the pipeline?",
     "The pipeline utilizes the `BAAI/bge-large-en-v1.5` model (1024 dimensions) for generating dense vector embeddings."),
    ("What distance metric is used in Qdrant / pgvector vector similarity searches?",
     "Vector similarity searches use Cosine Distance (or Cosine Similarity) as the primary index distance metric."),
    ("What is the maximum allowed payload size for document uploads via the `/api/v1/documents` endpoint?",
     "The maximum allowed file upload payload size is 50MB per single document request."),
    ("What HTTP status code is returned when an API request exceeds configured rate limits?",
     "Requests exceeding rate limits return HTTP 429 Too Many Requests with a `Retry-After` header indicating wait time in seconds."),
    ("Which database system is used as the primary relational metadata store in the architecture?",
     "PostgreSQL 16 with Row Level Security (RLS) enabled serves as the primary relational and metadata store."),
    ("What is the default chunk size and overlap configuration used by the hierarchical chunking engine?",
     "The hierarchical chunking engine uses a default parent chunk size of 1024 tokens with 128 token overlap, and child chunks of 256 tokens with 32 token overlap."),
    ("Which framework powers the asynchronous background task workers in the ingestion pipeline?",
     "Celery with Redis as broker and result backend handles asynchronous background task processing."),
    ("What streaming transport protocol is used to deliver real-time token responses to the frontend?",
     "Server-Sent Events (SSE) via `sse-starlette` over HTTP/2 or HTTP/1.1 is used for real-time token streaming."),
    ("Where are document binary files and raw PDF uploads persisted in local development?",
     "Raw document files are stored in the local `/storage/documents/` directory partitioned by tenant ID."),
    ("What is the default port exposed by the FastAPI backend server?",
     "The FastAPI backend server listens on port 8000 by default."),
    ("Which observability library is integrated to collect distributed traces and metrics?",
     "OpenTelemetry SDK (OTel) is used with OTLP gRPC exporters to collect traces and metrics."),
    ("What is the target Time-to-First-Token (TTFT) latency SLA for non-graph queries?",
     "The target p95 Time-to-First-Token latency SLA for standard semantic retrieval queries is under 200ms."),
    ("What tool is used for automated database schema migrations in the backend service?",
     "Alembic (SQLAlchemy migration tool) is used for version-controlled schema migrations."),
    ("What is the timeout threshold configured for OpenAI LLM chat completion requests?",
     "OpenAI LLM API calls are configured with a 30-second client timeout and exponential backoff retry logic.")
]

TECH_MEDIUM = [
    ("How does the hybrid search retriever balance dense semantic vector scores and sparse BM25 keyword scores?",
     "Hybrid search applies Reciprocal Rank Fusion (RRF) with a smoothing constant k=60: RRF_score = 1/(60 + rank_dense) + 1/(60 + rank_sparse), followed by a Cross-Encoder reranker on the top-50 candidates."),
    ("What is the step-by-step pipeline executed when a PDF document is uploaded via `/api/v1/documents`?",
     "The upload pipeline: 1) validates MIME type and tenant quota, 2) extracts text and layout tables using Docling, 3) anonymizes PII using Microsoft Presidio, 4) executes hierarchical chunking, 5) generates dense embeddings, 6) extracts entity triples for knowledge graph, and 7) indexes chunks into Qdrant/pgvector."),
    ("How does tenant isolation work in the PostgreSQL database using Row-Level Security (RLS)?",
     "Every tenant query initializes the connection with `SET LOCAL app.current_tenant_id = 'tenant-uuid'`, and Postgres RLS policies enforce `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)` on all table operations."),
    ("How does the token-level streaming SSE handler manage citation annotations during real-time generation?",
     "The generation engine buffers trailing tokens to identify citation markdown markers `[^chunk_id]`, resolves chunk metadata (page, doc title) in real time, and sends a structured SSE event `citation` followed by the final `done` metadata event."),
    ("What is the fallback mechanism when the primary vector database cluster experiences a transient network outage?",
     "The retrieval client employs a circuit breaker pattern (3 failed attempts within 10s opens circuit): requests fail over to PostgreSQL pgvector keyword fallback search while a background health probe polls the vector database."),
    ("How does the query router determine whether to execute a Direct LLM, Semantic Search, Hybrid Search, or Multi-Hop Graph route?",
     "A lightweight classification model (or function-calling prompt) evaluates query complexity: conversational greetings use Direct LLM, single-fact queries use Semantic/Hybrid Search, and multi-entity relationship questions route to Graph RAG."),
    ("How are entity triples stored and queried for knowledge graph multi-hop traversal in Postgres?",
     "Triples are stored in the `entity_triples(subject, predicate, object, chunk_id, tenant_id)` table, indexed on `(subject, object)` and queried using recursive Common Table Expressions (CTEs) or Apache AGE Cypher graph queries up to depth 3."),
    ("What caching strategy is used for semantic query deduplication using vector embeddings?",
     "Incoming queries are embedded and compared against cached queries in Redis Vector Store; if cosine similarity exceeds 0.96 and TTL is valid, the pre-computed response is returned with a `cache_hit` flag."),
    ("How does the context compressor (LLMLingua) optimize retrieved chunks before passing them to the generator LLM?",
     "LLMLingua computes token perplexity against a small distilled model, filters low-information tokens and filler phrases, achieving a 2-3x compression ratio while preserving key factual entities and relationships."),
    ("How does the application manage Celery worker task priorities and concurrency for heavy OCR vs fast queries?",
     "Celery is configured with separate queues: `high_priority` (query reranking, real-time embeddings) with 8 worker threads, and `low_priority` (bulk Docling PDF OCR, graph extraction) with 2 worker threads."),
    ("What is the mechanism for rotating JWT signing keys without invalidating existing user sessions?",
     "The auth service maintains a JWKS (JSON Web Key Set) endpoint containing the active `kid` and previous `kid`; incoming tokens are verified against their specified `kid`, allowing a 24-hour overlap period during key rotation."),
    ("How does the PII anonymization pipeline handle named entity recognition and reversible de-anonymization?",
     "Presidio Analyzer detects PII entities (names, emails, SSNs), Presidio Anonymizer replaces them with cryptographic surrogates `<PERSON_1>`, storing an encrypted lookup table in tenant session memory for response restoration."),
    ("How is database connection pooling configured to prevent exhaustion under high concurrent SSE streams?",
     "Asyncpg pool is configured with `min_size=10`, `max_size=50`, and `max_inactive_connection_lifetime=300s`, utilizing SQLAlchemy async engine with scoped sessions per HTTP request lifecycle."),
    ("How does Langfuse capture prompt versions, LLM latency, and user feedback metrics?",
     "Langfuse SDK wraps OpenAI client calls using decorators, recording span generation trace IDs, prompt template IDs, input/output token counts, and binds user thumbs-up/down feedback via the `/feedback` API hook."),
    ("What are the resilience settings for handling rate limits on third-party LLM providers?",
     "Tenacity retry decorator handles `openai.RateLimitError` and `openai.APITimeoutError` with exponential backoff (initial=1s, multiplier=2, max=30s, stop=5 attempts) with jitter."),
    ("How does the system ensure idempotent document ingestion when identical files are uploaded multiple times?",
     "The ingestion pipeline computes a SHA-256 hash of the raw document content; if the hash exists in the tenant's `documents` table, previous chunk records are updated or the upload returns existing document ID.")
]

TECH_HARD = [
    ("Explain the end-to-end multi-hop graph RAG algorithm when answering queries requiring multi-document synthesis across disparate entities.",
     "The system: 1) extracts named entities from the user prompt via NER, 2) queries `entity_triples` using a recursive CTE up to 3 hops to build a local subgraph, 3) computes graph centrality (PageRank) to identify anchor nodes, 4) fetches associated text chunks from `chunks` table, 5) performs Cross-Encoder reranking over graph-derived chunks merged with hybrid vector results, 6) structures a synthesized prompt with entity relationship schemas, and 7) generates a structured multi-citation response."),
    ("How does the system maintain zero data leakage in a multi-tenant shared-cluster vector database architecture with dynamic tenant filtering?",
     "Every vector upsert attaches a payload `tenant_id: str`; vector search queries enforce hard metadata filtering `Filter(must=[FieldCondition(key='tenant_id', match=MatchValue(value=current_tenant_id))])` at the vector engine core before ANN graph traversal, combined with database RLS checks on retrieved chunk IDs to prevent index bleed-through."),
    ("How does the streaming response generator handle backpressure, client disconnects, and transaction rollback during SSE delivery?",
     "The FastAPI endpoint wraps the generator in `request.is_disconnected()` checks; on client abort, the generator halts immediately, closes the active database cursor, logs partial tokens to OpenTelemetry spans with status `CANCELLED`, and skips query interaction finalization without blocking worker threads."),
    ("What is the mathematical formulation and parameter tuning strategy for Reciprocal Rank Fusion combined with semantic Cross-Encoder reranking?",
     "Given ranked candidate lists D_vector and D_bm25, the RRF score is S_RRF(d) = sum_{m in {vector, bm25}} w_m / (k + rank_m(d)) with k=60, w_vec=0.7, w_bm25=0.3; the top 50 candidates are scored by Cross-Encoder `ms-marco-MiniLM-L-6-v2` yielding logits sigma(z), normalized via softmax, and truncated at score threshold tau=0.35."),
    ("How does the distributed tracing architecture propagate trace contexts across FastAPI HTTP requests, Celery asynchronous jobs, and external LLM calls?",
     "The OpenTelemetry `TraceContextTextMapPropagator` injects `traceparent` headers into Celery task metadata headers; Celery task runners extract the context via `propagators.extract()`, setting the active parent span so document ingestion and evaluation spans link seamlessly in Jaeger/Langfuse."),
    ("Describe the disaster recovery and active-active replication topology for PostgreSQL and vector store across two cloud regions.",
     "PostgreSQL operates with streaming synchronous replication to a hot standby in Region 2; vector indices use raft-based multi-node replication (RF=3) with cross-region snapshot synchronization to S3/GCS every 15 minutes, with Route53 latency-based DNS failover and automated read-replica promotion."),
    ("How are custom Presidio NLP recognizers trained and hot-reloaded into the running pipeline without restarting FastAPI worker pods?",
     "Custom regex and spaCy pattern recognizers are stored in PostgreSQL; a Redis Pub/Sub channel `recognizer_updates` notifies worker pods upon configuration change, triggering dynamic instantiation and registration into `AnalyzerEngine.registry` at runtime."),
    ("What strategies are employed to prevent prompt injection and indirect jailbreaks embedded within ingested third-party documents?",
     "Ingested text passes through an adversarial prompt detector model, system prompts utilize strict delimiters `<<<UNTRUSTED_DOCUMENT_CONTEXT>>>`, and the generator LLM is instructed with role-boundary guardrails enforcing strict adherence only to factual extraction.")
]

FIN_EASY = [
    ("What was the reported total consolidated revenue for Q3 Fiscal Year 2024?",
     "Total consolidated revenue for Q3 FY2024 was $142.8 million, representing a 16.4% year-over-year increase."),
    ("What was the gross profit margin achieved in the second quarter of 2024?",
     "The company achieved a gross profit margin of 68.5% in Q2 2024, compared to 65.2% in Q2 2023."),
    ("What was the total cash and cash equivalents balance at the end of the last fiscal quarter?",
     "Cash and cash equivalents totaled $315.4 million as of the fiscal quarter ended September 30, 2024."),
    ("What is the company's fiscal year end date?",
     "The company's fiscal year ends on December 31st of each calendar year."),
    ("What was the diluted earnings per share (EPS) reported in Q1 2024?",
     "Diluted earnings per share (EPS) for Q1 2024 was $0.42, exceeding consensus estimates of $0.38."),
    ("What percentage of total revenue was derived from recurring SaaS subscriptions in FY2023?",
     "Subscription and recurring SaaS revenue accounted for 84.2% of total consolidated revenue in FY2023."),
    ("What was the total research and development (R&D) expenditure in FY2023?",
     "Research and development expenses totaled $48.6 million in FY2023, representing 11.2% of net revenue."),
    ("What was the effective corporate tax rate reported in the annual financial statements?",
     "The company reported an effective corporate income tax rate of 19.8% for the fiscal year."),
    ("What is the maximum credit facility available under the revolving credit agreement with JPMorgan?",
     "The senior secured revolving credit facility provides up to $150.0 million in available borrowing capacity."),
    ("What was the Net Retention Rate (NRR) reported for enterprise customers in Q3 2024?",
     "Enterprise dollar-based Net Retention Rate (NRR) was 118.5% for the trailing twelve months ended Q3 2024."),
    ("How much capital expenditure (CapEx) was allocated to cloud infrastructure expansion in 2023?",
     "Capital expenditures for cloud infrastructure and data center expansion totaled $22.3 million in 2023."),
    ("What was the operating cash flow generated during the first half of 2024?",
     "Operating cash flow for the six months ended June 30, 2024 was $64.2 million, an increase of 28% year-over-year."),
    ("What was the reported headcount and personnel expense in the European operations division?",
     "The European division employed 420 full-time employees with total personnel expenditure of $38.9 million."),
    ("What was the total provision for doubtful accounts recorded in the recent 10-K filing?",
     "The allowance for doubtful accounts was recorded at $3.2 million, or 1.1% of gross accounts receivable."),
    ("What dividend per share was approved by the Board of Directors for Q4 2023?",
     "The Board of Directors approved a quarterly cash dividend of $0.15 per common share for Q4 2023."),
    ("What was the total deferred revenue balance recorded on the balance sheet as of June 30, 2024?",
     "Deferred revenue was $98.7 million as of June 30, 2024, of which $89.2 million was recognized as current.")
]

FIN_MEDIUM = [
    ("How did operating margin expand between FY2022 and FY2023, and what were the primary cost drivers?",
     "Operating margin expanded by 340 basis points from 14.2% in FY2022 to 17.6% in FY2023, driven by a 12% reduction in customer acquisition cost (CAC) and efficiency gains in automated cloud hosting operations."),
    ("What are the key financial covenants and debt-to-EBITDA ratio limits under the 2023 Term Loan facility?",
     "The loan agreement requires maintaining a minimum Interest Coverage Ratio of 3.50:1.00 and a maximum Consolidated Leverage Ratio (Total Net Debt / EBITDA) of 2.75:1.00 evaluated quarterly."),
    ("How is deferred revenue recognized under ASC 606 for multi-year enterprise contracts with bundled professional services?",
     "Under ASC 606, contract transaction price is allocated based on standalone selling prices (SSP); SaaS license revenue is recognized ratably over the subscription term, while professional implementation services are recognized over time using percentage-of-completion based on direct labor hours."),
    ("What was the impact of foreign currency exchange headwinds on EMEA region constant currency revenue growth in Q3 2024?",
     "Foreign exchange headwinds reduced reported EMEA revenue growth by 3.2 percentage points (reported growth was 14.1% vs. 17.3% on a constant currency basis), primarily driven by USD appreciation against the Euro and British Pound."),
    ("How did working capital components change during the last fiscal year, specifically Days Sales Outstanding (DSO) and Inventory Turnover?",
     "Days Sales Outstanding (DSO) improved from 58 days to 51 days due to automated receivables collection, while Days Payable Outstanding (DPO) remained steady at 44 days, generating an additional $14.5 million in free cash flow."),
    ("What was the EBITDA reconciliation breakdown from GAAP Operating Income for FY2023?",
     "GAAP Operating Income of $76.2 million was adjusted for $18.4 million in depreciation & amortization, $24.1 million in stock-based compensation, and $3.5 million in acquisition restructuring costs, resulting in Adjusted EBITDA of $122.2 million."),
    ("How are capitalized software development costs amortized, and what amount was capitalized during 2023?",
     "Capitalized internal-use software development totaled $14.8 million in 2023, which is amortized on a straight-line basis over an estimated useful life of 3 years beginning when the asset is ready for its intended use."),
    ("What are the maturity schedules and interest rate spreads for the company's outstanding convertible senior notes due in 2028?",
     "The $250 million convertible senior notes mature on September 15, 2028, bearing a fixed coupon of 1.25% per annum payable semi-annually with an initial conversion price of $48.50 per share."),
    ("How does customer concentration risk break down across top-10 enterprise accounts in the recent fiscal year?",
     "The top-10 customers accounted for 21.4% of total revenue in FY2023, with no single individual customer representing more than 4.2% of total consolidated revenue."),
    ("What were the major components of Sales & Marketing expense growth in the North American segment in 2023?",
     "Sales & Marketing expenses increased by $16.2 million (+18%), attributable to $9.5 million in sales commission expansions, $4.2 million in digital lead-generation campaigns, and $2.5 million in enterprise partner summit events."),
    ("How did the adoption of new leasing accounting standards (ASC 842) affect total balance sheet assets and liabilities?",
     "Under ASC 842, the company recorded $42.8 million in Operating Lease Right-of-Use (ROU) assets and $46.1 million in corresponding lease liabilities as of the adoption date."),
    ("What is the share repurchase authorization remaining, and how many shares were repurchased in the first nine months of 2024?",
     "Under the $100 million Board authorization, the company repurchased 1.8 million shares for $54.2 million at an average price of $30.11, leaving $45.8 million in remaining repurchase capacity."),
    ("How did Free Cash Flow (FCF) conversion rate relative to Adjusted EBITDA evolve over the past three fiscal years?",
     "FCF conversion was 62% in 2021, 68% in 2022, and 74% in 2023, reflecting disciplined capital expenditure and improved working capital optimization."),
    ("What were the financial results and revenue contribution from the recent acquisition of CloudAnalytics Inc.?",
     "CloudAnalytics Inc. contributed $18.6 million in revenue and $3.2 million in Adjusted EBITDA during the 8 months post-closing included in FY2023 results."),
    ("What tax valuation allowances are currently maintained against deferred tax assets in foreign jurisdictions?",
     "A valuation allowance of $12.4 million is maintained against net operating loss (NOL) carryforwards in certain European jurisdictions where future profitability is not deemed more likely than not."),
    ("What is the sensitivity of interest expense to a 100-basis-point increase in SOFR on floating-rate debt obligations?",
     "A 100-basis-point increase in benchmark SOFR rates would increase annual pre-tax interest expense by approximately $1.5 million based on $150 million in unhedged variable-rate borrowings."),
    ("What were the key line-item drivers in the General & Administrative (G&A) expense reduction in Q2 2024?",
     "G&A expenses declined by 7.4% year-over-year due to a $2.1 million reduction in external legal and consulting fees and automated back-office workflow deployments.")
]

FIN_HARD = [
    ("Synthesize the impact of the CloudAnalytics acquisition on the company's pro-forma debt leverage ratio, Goodwill impairment testing, and tax loss carryforward amortization over the next 5 years.",
     "The $180 million CloudAnalytics acquisition was financed with $100M cash and $80M drawn from the term loan, temporarily elevating the leverage ratio from 1.8x to 2.5x EBITDA (within the 2.75x covenant). Goodwill of $112M passed annual qualitative impairment testing under ASC 350 with zero write-downs. Under IRC Section 382, CloudAnalytics' $34M in federal NOL carryforwards are limited to an annual utilization cap of $4.8M over the next 7.1 years, yielding an estimated $1.0M annual cash tax savings."),
    ("Analyze how changes in interest rate swap fair values, derivative hedges under ASC 815, and foreign currency balance sheet re-measurements affected Comprehensive Income versus GAAP Net Income.",
     "While GAAP Net Income was $52.4 million, Total Comprehensive Income was $46.1 million; the $6.3 million discrepancy resulted from a $4.1 million unrealized loss on interest rate cash flow hedges reclassified into Other Comprehensive Income (OCI) and a $2.2 million negative foreign currency translation adjustment from European subsidiary balance sheet remeasurement under ASC 830."),
    ("Evaluate the revenue waterfall and ARR progression across Enterprise vs Mid-Market cohorts, factoring in Gross Retention, Expansion ARR, and Contraction churn for FY2023.",
     "Ending ARR reached $480M (+22% YoY). The Enterprise cohort ($100k+ ARR) demonstrated 96% Gross Retention and 124% Net Retention, adding $68M in new/expansion ARR against $4M in contraction. In contrast, Mid-Market experienced 88% Gross Retention and 104% Net Retention, with $22M in new ARR offset by $12M in churn/downsell, demonstrating that Enterprise expansion accounted for 81% of net ARR growth."),
    ("What is the complex accounting treatment for multi-element customer contracts including hardware appliances, embedded SaaS licenses, and 24/7 premium support SLAs under IFRS 15 / ASC 606?",
     "Under ASC 606, the contract is separated into three distinct performance obligations: hardware (recognized at point of delivery upon transfer of control), SaaS license (recognized ratably over the subscription term), and support SLAs (recognized on a straight-line basis over the service term). Standalone Selling Price (SSP) is established using the residual approach or observable standalone transactions."),
    ("How does the capital allocation framework balance R&D reinvestment, debt paydown, M&A reserves, and share repurchases under various macroeconomic stress-test scenarios?",
     "Under base case, 45% of operating cash flow is allocated to internal R&D, 25% to debt reduction targeting <1.5x leverage, 20% to tuck-in M&A, and 10% to opportunistic share buybacks; in a severe recession scenario, buybacks and M&A are paused, capital expenditures are trimmed by 35%, and liquidity preservation prioritizes maintaining a minimum $200M unencumbered cash cushion."),
    ("Detail the calculation and dilutive impact of treasury stock method on stock options, RSUs, and convertible note settlement upon diluted EPS calculations.",
     "Under the treasury stock method, 4.2 million in-the-money options (weighted avg strike $22.50) and 2.1 million unvested RSUs generate 3.1 million net incremental dilutive shares assuming an average market price of $42.00; the convertible notes are evaluated under the if-converted method, adding 5.15 million potential shares unless net-share settled in cash."),
    ("How does the cross-border transfer pricing structure between the US parent and Irish IP holding entity distribute taxable operating income under OECD BEPS Pillar Two rules?",
     "The Irish principal company licenses core IP to US and EMEA operating subsidiaries under a Cost Sharing Agreement (CSA) with arm's-length markups of 8% on operational costs; under OECD Pillar Two minimum tax rules (15% GloBE rate), any Irish effective tax rate shortfall below 15% triggers a top-up tax payable in Ireland or via the US Ultimate Parent Entity IIR mechanism."),
    ("Assess the liquidity runway, debt refinancing risk, and working capital cash burn trajectory under a hypothetical 20% top-line contraction scenario.",
     "In a 20% revenue decline scenario ($114M annual contraction), gross profit drops by $78M; counterbalanced by $35M in variable sales commission and cloud hosting reductions, net cash burn would be $18M annually. With $315M cash and $150M undrawn credit facility, total available liquidity provides over 15 years of runway, with no debt maturing before the 2028 convertible notes.")
]

LEGAL_EASY = [
    ("What is the standard mutual confidentiality term length specified in the Master Services Agreement (MSA)?",
     "The mutual confidentiality obligations endure for a period of three (3) years from the date of disclosure, except for trade secrets which remain protected in perpetuity."),
    ("What is the governing law and jurisdiction specified in the standard Master Subscription Agreement?",
     "The agreement is governed by and construed in accordance with the laws of the State of Delaware, without regard to conflict of law principles."),
    ("How many days written notice is required for termination for convenience under the standard vendor contract?",
     "Either party may terminate the contract for convenience by providing at least sixty (60) days prior written notice to the other party."),
    ("What is the standard aggregate liability cap for direct damages under the enterprise customer terms?",
     "Each party's total aggregate liability arising out of or related to the agreement is capped at the total amount paid or payable by customer in the twelve (12) months preceding the claim."),
    ("What is the mandatory timeline for notifying customers of a confirmed personal data security breach under the DPA?",
     "The data processor must notify the customer in writing without undue delay and in any event within forty-eight (48) hours of becoming aware of a confirmed personal data breach."),
    ("What constitutes a material breach that permits immediate contract termination with cause?",
     "A material breach that remains uncured for thirty (30) days after written notice allows the non-breaching party to immediately terminate the agreement for cause."),
    ("Are punitive and consequential damages waivable under the mutual limitation of liability clause?",
     "Yes, both parties mutually waive any liability for indirect, incidental, special, consequential, or punitive damages, including loss of profits or business interruption."),
    ("What is the standard SLA uptime guarantee provided in the Service Level Schedule?",
     "The company guarantees a monthly service availability uptime of at least 99.9%, excluding scheduled maintenance windows announced 72 hours in advance."),
    ("What remedy is provided to customers if monthly uptime falls below 99.0%?",
     "Customers are entitled to a service credit equal to 25% of the monthly subscription fee for the affected billing cycle upon submitting a claim within 30 days."),
    ("Who retains ownership of Intellectual Property created prior to the execution of the services contract?",
     "Each party retains sole and exclusive ownership of its pre-existing background intellectual property and any independent enhancements made outside the scope of the agreement."),
    ("What is the non-solicitation duration restricting recruitment of the other party's personnel?",
     "Neither party may actively solicit or hire the other party's employees or contractors during the contract term and for twelve (12) months thereafter."),
    ("What are the mandatory dispute resolution steps before either party can initiate litigation?",
     "The parties must engage in good-faith executive escalation for twenty (20) business days, followed by non-binding mediation before filing a lawsuit in court."),
    ("What is the formal definition of Force Majeure events in the commercial contract?",
     "Force Majeure events include acts of God, war, terrorism, civil unrest, natural disasters, national power grid failures, and government embargoes beyond reasonable control."),
    ("How must formal legal notices be delivered under the notice provision of the agreement?",
     "Notices must be in writing and delivered by nationally recognized overnight courier or certified mail (return receipt requested) to the designated legal addresses."),
    ("Does the agreement permit assignment of rights upon a merger or acquisition without prior consent?",
     "Yes, either party may assign the agreement without consent in connection with a merger, acquisition, or sale of substantially all assets, provided the assignee is not a direct competitor."),
    ("What is the time limit for asserting a warranty claim regarding software defects after initial delivery?",
     "Warranty claims must be submitted in writing within ninety (90) days following initial provisioning or delivery of the software services.")
]

LEGAL_MEDIUM = [
    ("What categories of claims are expressly carved out from the standard mutual limitation of liability cap?",
     "The liability cap does not apply to: 1) breaches of confidentiality obligations, 2) third-party intellectual property indemnification claims, 3) gross negligence or willful misconduct, and 4) payment obligations owed under executed Order Forms."),
    ("How does the Data Processing Addendum (DPA) address international personal data transfers from the EU/EEA to the US post-Schrems II?",
     "Transfers rely on EU Standard Contractual Clauses (SCCs Module 2 & 3) combined with the EU-U.S. Data Privacy Framework certification, supplemented by technical Transfer Impact Assessments (TIAs) including end-to-end TLS 1.3 encryption and zero-access key management."),
    ("What are the specific indemnification obligations and defense procedures when a customer is sued for patent infringement by a third party?",
     "The vendor defends and holds customer harmless against third-party IP infringement claims at vendor's sole expense, provided customer gives prompt written notice (within 15 days), grants sole control of legal defense and settlement, and cooperates reasonably."),
    ("How are sub-processors vetted and approved, and what objection rights do customers have under the DPA?",
     "The vendor maintains an up-to-date sub-processor list and provides thirty (30) days advance email notice before engaging new sub-processors; customers have the right to object on reasonable data protection grounds within 14 days."),
    ("What are the legal distinctions between Customer Data, Aggregated/De-identified Data, and Usage Metadata under the platform terms?",
     "Customer Data remains the exclusive property of the customer; Aggregated Data is anonymized data stripped of all personal and customer identifiers used for benchmarking; Usage Metadata includes telemetry metrics owned by the vendor for service optimization."),
    ("How does the contract define intellectual property ownership of custom custom-developed integrations vs core platform extensions?",
     "Custom integration scripts created specifically for customer are owned by customer as work-for-hire, whereas any generic connectors, APIs, or improvements to core underlying software remain the exclusive IP of the platform vendor."),
    ("What audit rights are granted to enterprise financial services customers under regulatory compliance addendums (e.g., SOC 2, HIPAA)?",
     "Enterprise customers may request annual third-party SOC 2 Type II reports and ISO certifications, and may conduct on-site security audits once per year with 30 days prior notice, during normal business hours, at customer's sole expense."),
    ("What restrictions govern the use of customer trade names and logos for vendor marketing and press releases?",
     "The vendor may use customer's name and logo in standard customer lists on websites; standalone press releases, case studies, or quote endorsements require prior written approval from customer's corporate communications team."),
    ("How are source code escrow release conditions structured in the enterprise software license addendum?",
     "Source code is deposited with NCC Group / Iron Mountain; escrow release triggers only if the vendor ceases operations, files for Chapter 7 liquidation bankruptcy, or formally discontinues core support without a successor product."),
    ("What legal rights and obligations exist regarding data deletion and return upon contract termination?",
     "Upon contract expiration, customer has thirty (30) days to export all Customer Data via API/secure bucket; after 30 days, vendor permanently deletes and purges all customer data across live and backup systems within 90 days, providing written certification upon request."),
    ("How does the contract address compliance with export control laws and OFAC sanctions regulations?",
     "Both parties warrant compliance with US Export Administration Regulations (EAR), EU dual-use regulations, and OFAC sanctions, prohibiting platform access by denied parties or in embargoed destinations (e.g., Cuba, Iran, North Korea)."),
    ("What warranty disclaimers apply to artificial intelligence and large language model generated outputs?",
     "Outputs generated by AI/LLM components are provided 'AS IS' without warranty of accuracy, completeness, or non-infringement; customer acknowledges that AI outputs may contain hallucinations and assumes responsibility for verifying mission-critical decisions."),
    ("What are the requirements for enforcing non-disparagement and confidentiality in executive separation agreements?",
     "Non-disparagement must be mutual, protect corporate reputations while exempting truthful testimony under subpoena or protected whistleblower disclosures to government bodies (SEC, EEOC)."),
    ("How do the terms govern open-source software license compliance and copyleft isolation within the proprietary codebase?",
     "The platform uses only permissive open-source licenses (MIT, Apache 2.0, BSD); no GPL/AGPL copyleft libraries are linked or distributed in a manner that would subject proprietary source code to mandatory open-source disclosure."),
    ("What remedies and procedures govern insurance coverage requirements (Cyber Liability, Errors & Omissions) under vendor contracts?",
     "Vendor must maintain at least $5M Cyber Liability / Data Breach insurance and $5M Errors & Omissions coverage with an A-rated carrier, naming customer as additional insured upon request."),
    ("What constitutes valid electronic signature and counterparts execution under the E-SIGN Act and UETA?",
     "Signatures executed via DocuSign, Adobe Sign, or scanned PDF exchange are deemed original binding counterparts with full legal force under the federal E-SIGN Act and Delaware UETA."),
    ("How are tax liabilities and withholding responsibilities allocated between buyer and seller in cross-border software licensing?",
     "All fees are exclusive of VAT, GST, and sales taxes; customer is responsible for applicable local sales taxes, while payments are made free of foreign withholding taxes or accompanied by official tax residency treaty exemption certificates.")
]

LEGAL_HARD = [
    ("Analyze the legal interplay between GDPR Article 28 data processor obligations, US CLOUD Act subpoena compliance, and Standard Contractual Clauses (SCCs) when a US cloud provider hosts EU citizen data.",
     "A direct conflict arises when US authorities issue a CLOUD Act warrant: the provider is compelled under US law to disclose data, while GDPR Article 48 prohibits foreign court orders without an MLAT treaty. Under Schrems II and EDPB guidelines, the provider must challenge foreign orders that lack judicial oversight, implement end-to-end encryption where keys are held exclusively in the EU by an independent trustee, and notify the customer unless prohibited by a statutory gag order, with breach of SCC obligations subjecting the transfer to suspension."),
    ("Synthesize the patent infringement indemnification defense strategy, willful infringement treble damages risk, and indemnification caps when an open-source library within a commercial RAG pipeline is targeted by a non-practicing entity (NPE).",
     "The vendor must assert third-party indemnification defense within statutory answer deadlines, evaluate whether open-source components fall within the 'Open Source Software Exclusion' in the MSA, conduct prior-art invalidity searches to counter willful infringement claims under 35 U.S.C. 284, and if liability is established, invoke indemnification subrogation rights against upstream commercial contributors while ensuring the claim falls within the uncapped IP indemnity carveout."),
    ("Evaluate the enforceability of liquidated damages clauses versus unenforceable penalty doctrines under Delaware and English law in large enterprise IT delivery contracts.",
     "Under Delaware law, liquidated damages are enforceable if anticipated damages from breach are uncertain and the specified amount is a reasonable forecast of just compensation at contract signing. Under English law (Cavendish v El Makdessi), the test is whether the clause is a secondary obligation imposing a detriment disproportionate to the legitimate interest of the innocent party in contract performance; penalty clauses exceeding actual loss without legitimate commercial interest are void."),
    ("How do enterprise software contracts structure tiered warranty remedies, exclusive remedy clauses, and failure of essential purpose doctrines under UCC Section 2-719?",
     "Contracts establish a tiered remedy: 1) vendor commercially reasonable efforts to repair or replace non-conforming software, 2) if uncured within 60 days, customer right to terminate and receive a prorated refund of prepaid unused fees as the 'sole and exclusive remedy'. Under UCC 2-719(2), if the repair remedy fails of its essential purpose, the exclusive remedy is invalidated, potentially reviving general contract damage remedies unless the consequential damages waiver is explicitly drafted as an independent covenant."),
    ("What are the cross-jurisdictional legal and antitrust risks associated with M&A non-compete covenants and non-solicitation pacts under FTC regulations and EU Article 101 TFEU?",
     "Under FTC non-compete rulemaking and EU Article 101/102 guidelines, non-compete clauses in M&A are permitted only if strictly necessary and proportionate (ancillary restraints) limited to 2-3 years and geographical markets where seller operated; non-solicitation pacts between non-merging competitors constitute per se illegal wage-fixing agreements subject to criminal antitrust prosecution."),
    ("How do liability allocations, business associate agreements (BAA), and OCR breach notification penalties operate when HIPAA protected health information (PHI) is processed by multi-tenant AI pipelines?",
     "Under HIPAA Omnibus Rule and BAA terms, the AI vendor operates as a Business Associate with direct statutory liability for Security Rule violations; if unencrypted PHI is exposed, breach notification to HHS OCR, affected individuals, and media (if >500 records in a state) is mandatory within 60 days, triggering Tier 4 willful neglect statutory civil monetary penalties up to $2.0M annually."),
    ("Detail the jurisdictional enforceability and arbitration carveouts for emergency injunctive relief, intellectual property theft, and trade secret misappropriation under AAA / ICC / LCIA rules.",
     "While commercial disputes route to mandatory binding arbitration under AAA/ICC rules, agreements insert an explicit judicial carveout allowing either party to seek temporary restraining orders (TROs) and preliminary injunctive relief in Delaware Chancery Court or English High Court to halt ongoing trade secret theft (DTSA/Defend Trade Secrets Act) without waiving the agreement to arbitrate remaining damages."),
    ("Assess the compliance architecture required for financial institution customers subject to DORA (Digital Operational Resilience Act) and EBA Outsourcing Guidelines.",
     "The vendor must guarantee continuous ICT incident monitoring, support mandatory participation in client threat-led penetration testing (TLPT), grant unrestricted supervisory audit rights to European financial regulators (ECB/EBA), maintain robust exit plans with tested data transition within 90 days, and guarantee multi-region ICT disaster redundancy within the EU.")
]

ONBOARD_EASY = [
    ("What is the first step new hires must complete on their first day of employment?",
     "New hires must complete their identity verification and log into the single sign-on (SSO) portal using their temporary credentials provided by IT."),
    ("How do new employees request their hardware workstation and laptop accessories?",
     "Hardware requests are submitted through the IT Service Desk portal (ServiceNow) during the pre-boarding phase or on day one."),
    ("What is the timeline for completing mandatory cybersecurity awareness training after start date?",
     "All new employees must complete the mandatory online cybersecurity awareness and data protection training modules within their first 14 calendar days."),
    ("Where can new hires find the official company directory and organizational chart?",
     "The organizational chart, team directories, and reporting hierarchies are accessible on the internal intranet at `go/org` or within Workday."),
    ("What is the designated Slack channel for general IT support and troubleshooting?",
     "General IT support requests and real-time troubleshooting assistance are handled in the `#it-helpdesk` Slack channel."),
    ("How does a new hire set up multi-factor authentication (MFA) on their mobile device?",
     "Employees download the Okta Verify / Google Authenticator app and scan the QR code generated during their initial SSO login on their workstation."),
    ("What is the window for selecting health, dental, and vision insurance benefit plans?",
     "New hires have thirty (30) calendar days from their official start date to finalize their benefits elections in the benefits enrollment portal."),
    ("Who is assigned to support a new hire with informal day-to-day questions during their first month?",
     "Each new hire is paired with an Onboarding Buddy from their team or adjacent department to provide informal guidance during the first 90 days."),
    ("How do new hires submit their direct deposit banking information for payroll?",
     "Direct deposit details and tax withholding forms (W-4) must be entered directly into the Workday Payroll portal under 'Payment Elections'."),
    ("What is the deadline for submitting Section 2 of Form I-9 employment eligibility verification?",
     "Section 2 of Form I-9 with physical document inspection must be completed within three (3) business days of the employee's first day of work."),
    ("Where are software development environment setup guides and engineering docs located?",
     "Engineering setup guides, repository access instructions, and local dev container scripts are maintained in the Engineering Wiki at `wiki.internal/eng-onboarding`."),
    ("How do remote employees request reimbursement for initial home office supplies?",
     "Home office supplies are submitted through the Expensify expense reporting tool under the 'Home Office Stipend' policy category with itemized receipts."),
    ("What is the company policy regarding setting up emergency contacts?",
     "Employees must provide at least two emergency contacts with phone numbers and relationships in their Workday profile during their first week."),
    ("What is the protocol for obtaining an office building security access badge?",
     "New hires pick up their physical RFID badge at the Facilities Security Desk on their first in-office day after presenting a valid government-issued photo ID."),
    ("How do team members schedule their introductory 1-on-1 meetings with their manager?",
     "Managers initiate a recurring weekly 1-on-1 calendar invite during week one, and new hires are encouraged to schedule 15-minute introductory coffee chats across cross-functional partners."),
    ("Where are corporate brand assets, presentation templates, and logos located?",
     "Official slide templates, logos, design assets, and brand guidelines are hosted on the Marketing Hub at `go/brand`.")
]

ONBOARD_MEDIUM = [
    ("What are the key milestones and deliverables expected in the 30-60-90 day onboarding roadmap for software engineers?",
     "30 Days: complete dev environment setup, ship first pull request to staging, pass security trainings. 60 Days: own a feature ticket end-to-end, participate in on-call shadow rotation. 90 Days: lead sprint story reviews, contribute to architectural RFCs, and operate as an autonomous on-call engineer."),
    ("How does an engineer obtain access to production database read-replicas, Kubernetes clusters, and AWS IAM roles?",
     "Engineers submit a Role-Based Access Control (RBAC) request in Jira Service Management with manager approval, complete the Production Access Security training, and utilize Teleport / Okta Privileged Access for temporary short-lived certificate sessions."),
    ("What is the procedure for configuring SSH keys, GPG commit signing, and GitHub enterprise 2FA for source code contributions?",
     "Engineers generate an Ed25519 SSH key and GPG signing key on their company YubiKey, upload public keys to their GitHub Enterprise profile, enforce commit signature verification, and link GitHub 2FA to their hardware security token."),
    ("How do new team leads navigate the requisition, interview loop design, and hiring approval process in Greenhouse?",
     "Hiring managers complete the Inclusive Hiring workshop, define the job rubric and scorecard with the Talent Partner, secure Finance headcount approval in Ashby/Greenhouse, and configure standard structured interview stages."),
    ("What steps must be followed when setting up a local Docker development container connected to cloud staging dependencies?",
     "Developers clone `infra/dev-environment`, populate `.env.local` using Doppler secrets injection, run `make setup-containers` to launch Postgres and Redis, and connect local services via WireGuard VPN to the staging VPC."),
    ("How are annual compliance refresher certifications tracked, and what happens if deadlines are missed?",
     "Training modules are tracked via the LMS platform with automated email reminders at 30, 14, and 3 days before deadline; failing to complete training within 30 days results in temporary suspension of GitHub and production access."),
    ("What is the protocol for reporting lost, stolen, or damaged corporate IT hardware while traveling?",
     "Employees must immediately notify the IT Security Incident Response Team at `security@company.com` within 2 hours, enabling remote MDM wipe of the device, and file a formal police report for insurance replacement."),
    ("How does the performance goal-setting process operate for new hires in their first quarterly review cycle?",
     "Within the first 30 days, the employee and manager collaborate in Lattice to establish 3-4 SMART Objectives and Key Results (OKRs), aligned with team OKRs, which are reviewed at mid-quarter check-in."),
    ("What are the guidelines for utilizing enterprise AI coding assistants (e.g., GitHub Copilot, internal LLM portals)?",
     "Engineers must use only company-provisioned enterprise accounts with telemetry and public code matching disabled; pasting customer PII, secret keys, or unreleased source code into unauthorized public AI tools is strictly prohibited."),
    ("How does a newly hired remote employee order ergonomic office furniture through the corporate vendor portal?",
     "Employees log into the Herman Miller / Fully corporate portal using SSO, select pre-approved ergonomic chairs and sit-stand desks within the $750 allocation, with direct corporate billing and home delivery."),
    ("What is the escalation procedure when encountering blockers during cross-functional project onboarding?",
     "Blockers are flagged in daily standup and recorded on the team sprint board; if unresolved within 24 hours, the engineer escalates to the Tech Lead and Product Manager for cross-team alignment."),
    ("How do new hires join employee resource groups (ERGs) and community Slack channels?",
     "Employees can browse open ERGs (e.g., Women in Tech, Pride, Black at Co) via the Culture Wiki and join their respective public Slack channels `#erg-*` to participate in events and mentorship circles."),
    ("What are the travel and expense booking procedures using the corporate TravelPerk platform?",
     "All business flights and hotels must be booked through TravelPerk to ensure corporate discounted rates, automatic duty-of-care tracking, and direct integration with Expensify expense reports."),
    ("How does an engineer configure local linters, pre-commit hooks, and CI/CD pipeline triggers for new microservice repositories?",
     "Engineers install `pre-commit`, run `pre-commit install` to register Black/Ruff and ESLint hooks, and ensure `.github/workflows/ci.yml` passes formatting, unit tests, and SonarQube quality gates before requesting PR review."),
    ("What are the protocols for handling customer support escalations during on-call rotation training?",
     "During on-call shadow week, new engineers join the primary on-call in the `#oncall-active` channel, review incident runbooks, observe PagerDuty alert triage, and document incident retrospective notes."),
    ("How do employees schedule personal development 1-on-1s and career matrix reviews with department leadership?",
     "Career progression discussions occur quarterly outside regular sprint reviews, referencing the engineering competency matrix levels (IC1 through IC6) to assess growth areas and promotion readiness.")
]

ONBOARD_HARD = [
    ("Outline the complete security clearance, cryptographic key escrow, and infrastructure access onboarding workflow for a Principal Site Reliability Engineer with root infrastructure privileges.",
     "The workflow requires: 1) Tier-3 background check and executive sponsor sign-off, 2) hardware provisioning of dual FIPS 140-2 Level 3 YubiKeys, 3) registration into HashiCorp Vault and Teleport PAM cluster with multi-party quorum authorization, 4) in-person (or recorded secure video) cryptographic ceremony for GPG root key generation and offline cold-storage backup, 5) completion of Red Team simulation and break-glass emergency response drills, and 6) assignment of zero-trust ephemeral IAM roles with mandatory peer-reviewed session auditing."),
    ("How does a cross-functional technical lead onboard a newly acquired engineering team, migrating their legacy monorepo, CI/CD pipelines, and IAM infrastructure into the parent enterprise ecosystem?",
     "The technical lead executes a 4-stage migration: Phase 1 (Identity & Security): federate acquired team identities into Okta SSO, enforce MDM enrollments, and audit codebases for embedded secrets via TruffleHog. Phase 2 (Infrastructure): establish VPC peering and Transit Gateway between cloud accounts, deploy Teleport proxies for secure access. Phase 3 (CI/CD): migrate Jenkins pipelines to GitHub Actions with reusable workflow templates and containerized runners. Phase 4 (Code & Data): consolidate monorepos or establish semantic microservice boundary registries, aligning coding standards, SonarQube quality gates, and automated deployment canary testing."),
    ("Synthesize the complete onboarding curriculum, regulatory compliance audits, and data governance certifications required for an algorithmic quantitative analyst dealing with MNPI (Material Non-Public Information).",
     "The analyst must: 1) complete FINRA / SEC Market Abuse and MNPI compliance modules, 2) execute personal securities trading disclosure agreements and connect personal brokerage accounts to Schwab Compliance Technologies for automated pre-clearance, 3) receive access to isolated Clean Room data analytics enclaves where egress traffic is blocked and clipboard copy is disabled, 4) obtain approval from the Information Barrier Compliance Officer for specific restricted issuer data rooms, and 5) pass quarterly ethical wall audits tracking communications and research log timestamps."),
    ("Describe the end-to-end disaster recovery and business continuity onboarding drill required for distributed incident commanders across three global time zones.",
     "Incident commanders undergo simulated regional failure drills (Chaos Engineering GameDay): 1) simulate complete AWS us-east-1 outage, 2) trigger automated DNS failover via Route 53 to us-west-2, 3) coordinate triage war room in dedicated backup communication channels (backup Matrix/Signal), 4) manage cross-regional customer status page updates every 15 minutes, 5) execute database point-in-time recovery (PITR) validation, and 6) conduct a blameless post-mortem retrospective within 48 hours establishing preventative Jira action items."),
    ("How does an enterprise architect onboard and align disparate business unit data schemas into a centralized multi-tenant Data Mesh architecture?",
     "The architect: 1) establishes domain-oriented Data Product boundaries and semantic contracts using OpenMetadata / dbt, 2) defines centralized governance policies including row-level and column-level masking for PII via Apache Ranger/BigQuery policy tags, 3) deploys federated data discovery catalog with automated lineage tracking, 4) configures self-serve data infrastructure templates (Kafka topics, Iceberg tables), and 5) institutes SLO/SLA data quality metrics enforced via Great Expectations in CI/CD pipeline tests."),
    ("Explain the complex compliance, security clearance, and technical onboarding protocol for an AI Research Scientist developing proprietary foundation models on distributed GPU superclusters.",
     "The scientist must: 1) sign proprietary Model IP and AI Safety agreements, 2) complete training on model alignment, red-teaming, and unlearning protocols, 3) configure Slurm / Kubernetes GPU cluster access via mTLS with dedicated high-speed InfiniBand network partitions, 4) establish dataset provenance tracking conforming to EU AI Act copyright transparency rules, 5) configure Weights & Biases / MLflow experiment tracking with automated model checkpoint encryption, and 6) establish safety evaluation gates before releasing weights to internal inference tiers."),
    ("What are the procedures for onboarding international contractor engineering firms to ensure strict compliance with IP assignment, source code segregation, and export regulations?",
     "The company: 1) executes Corporate Services Agreements (CSA) with explicit IP assignment and foreign jurisdiction dispute clauses, 2) provisions virtual desktop infrastructure (Amazon WorkSpaces / GCP Workstations) without local data download capabilities, 3) restricts repository visibility strictly to assigned service repositories using GitHub fine-grained team permissions, 4) disables USB storage and external email attachments on VDI sessions, and 5) audits contractor commits with automated static security analysis and mandatory internal staff code review approval."),
    ("How does an engineering director design an onboarding program for 50+ engineers joining simultaneously following a major enterprise expansion?",
     "The director deploys a Cohort-Based Onboarding Architecture: 1) organizes new hires into cross-functional Pods with dedicated Technical Leads, 2) implements a structured 2-week Engineering Bootcamp combining live workshops with self-paced coding labs, 3) utilizes automated dev-environment provisioning (Codespaces/Devcontainers) ensuring day-one build capabilities, 4) tracks progress via an Onboarding LMS dashboard monitoring PR velocity and training completion, and 5) gathers weekly anonymous feedback retrospectives to dynamically optimize curriculum pacing."),
    ("Describe the onboarding and access provisioning protocol for third-party external penetration testers conducting an authorized black-box and white-box security audit.",
     "The protocol entails: 1) execution of Rules of Engagement (RoE) specifying allowed IP ranges, testing windows, and prohibited Denial of Service vectors, 2) establishment of an encrypted out-of-band communication channel (Signal group) for urgent critical vulnerability reporting, 3) provisioning of dedicated test tenant environments populated with synthetic non-production data, 4) issuance of ephemeral OAuth test credentials and Postman API collections, and 5) daily alignment syncs to confirm testing boundaries and coordinate WAF/DDoS defense bypass rules.")
]

def generate_golden_dataset():
    categories_data = [
        ("HR_Policy", HR_EASY, HR_MEDIUM, HR_HARD),
        ("Technical_Docs", TECH_EASY, TECH_MEDIUM, TECH_HARD),
        ("Financial_Reports", FIN_EASY, FIN_MEDIUM, FIN_HARD),
        ("Legal_Contracts", LEGAL_EASY, LEGAL_MEDIUM, LEGAL_HARD),
        ("Onboarding", ONBOARD_EASY, ONBOARD_MEDIUM, ONBOARD_HARD),
    ]
    
    dataset = []
    global_counter = 1
    
    for cat_name, easy_list, med_list, hard_list in categories_data:
        # Easy
        for q, gt in easy_list:
            dataset.append({
                "id": f"eval_{global_counter:03d}",
                "query": q,
                "ground_truth": gt,
                "relevant_chunk_ids": [],
                "difficulty": "easy",
                "category": cat_name
            })
            global_counter += 1
            
        # Medium
        for q, gt in med_list:
            dataset.append({
                "id": f"eval_{global_counter:03d}",
                "query": q,
                "ground_truth": gt,
                "relevant_chunk_ids": [],
                "difficulty": "medium",
                "category": cat_name
            })
            global_counter += 1
            
        # Hard
        for q, gt in hard_list:
            dataset.append({
                "id": f"eval_{global_counter:03d}",
                "query": q,
                "ground_truth": gt,
                "relevant_chunk_ids": [],
                "difficulty": "hard",
                "category": cat_name
            })
            global_counter += 1

    return dataset

if __name__ == "__main__":
    out_path = Path("/Users/muhammadsoban/Desktop/Pipeline/evaluation/golden_dataset.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    dataset = generate_golden_dataset()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
        
    total = len(dataset)
    easy_c = sum(1 for d in dataset if d["difficulty"] == "easy")
    med_c = sum(1 for d in dataset if d["difficulty"] == "medium")
    hard_c = sum(1 for d in dataset if d["difficulty"] == "hard")
    
    print(f"Generated {total} evaluation samples.")
    print(f"Easy: {easy_c} ({easy_c/total*100:.1f}%)")
    print(f"Medium: {med_c} ({med_c/total*100:.1f}%)")
    print(f"Hard: {hard_c} ({hard_c/total*100:.1f}%)")
