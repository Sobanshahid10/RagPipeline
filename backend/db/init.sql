-- Enable Required Extensions in Specified Order
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 1. Tenants Table (Multi-tenant Foundation)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Users Table (Role-Based Access & Auth)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    roles TEXT[] DEFAULT '{viewer}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Documents Master Table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    doc_hash VARCHAR(64) NOT NULL,
    storage_uri TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, indexed, failed
    total_pages INT DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (tenant_id, doc_hash)
);

-- 4. Chunks Table (Multimodal & Vector Embeddings)
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    contextual_summary TEXT,
    page_number INT,
    bounding_box JSONB, -- [ymin, xmin, ymax, xmax]
    token_count INT NOT NULL,
    embedding VECTOR(1536),
    sparse_tsv TSVECTOR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vector & Keyword Indexes for Hybrid Search
CREATE INDEX IF NOT EXISTS idx_chunks_hnsw ON chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
CREATE INDEX IF NOT EXISTS idx_chunks_sparse_tsv ON chunks USING gin (sparse_tsv);
CREATE INDEX IF NOT EXISTS idx_chunks_tenant ON chunks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id);

-- 5. Knowledge Graph Triples Table (GraphRAG)
CREATE TABLE IF NOT EXISTS entity_triples (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    source_chunk_id UUID REFERENCES chunks(id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triples_sub_obj ON entity_triples(subject, object);
CREATE INDEX IF NOT EXISTS idx_triples_tenant ON entity_triples(tenant_id);

-- 6. Query Interactions & Evaluation Logs Table
CREATE TABLE IF NOT EXISTS query_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    session_id UUID NOT NULL,
    retrieval_scope TEXT,
    raw_query TEXT NOT NULL,
    rewritten_query TEXT,
    route_used VARCHAR(50),
    retrieved_chunk_ids UUID[],
    answer TEXT,
    ttft_ms INT,
    total_latency_ms INT,
    prompt_tokens INT,
    completion_tokens INT,
    user_feedback INT DEFAULT 0, -- 1 = Thumbs Up, -1 = Thumbs Down
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interactions_tenant ON query_interactions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_interactions_feedback ON query_interactions(user_feedback);
CREATE INDEX IF NOT EXISTS idx_interactions_history ON query_interactions(tenant_id,user_id,session_id,retrieval_scope,created_at DESC);

-- 7. RAGAS Eval Scores Table
CREATE TABLE IF NOT EXISTS eval_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    interaction_id UUID REFERENCES query_interactions(id) ON DELETE CASCADE,
    context_recall FLOAT,
    context_precision FLOAT,
    faithfulness FLOAT,
    answer_relevancy FLOAT,
    hallucination_detected BOOLEAN DEFAULT FALSE,
    evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security (RLS) for Tenant Isolation
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE entity_triples ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_interactions ENABLE ROW LEVEL SECURITY;

-- Multi-Tenant RLS Policies (Session Variable app.current_tenant_id)
CREATE POLICY documents_tenant_isolation ON documents
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY chunks_tenant_isolation ON chunks
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY entity_triples_tenant_isolation ON entity_triples
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);

CREATE POLICY query_interactions_tenant_isolation ON query_interactions
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);


-- The runtime role must never own tables or bypass tenant policies.
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE entity_triples FORCE ROW LEVEL SECURITY;
ALTER TABLE query_interactions FORCE ROW LEVEL SECURITY;

CREATE TABLE IF NOT EXISTS document_audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    document_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('upload','retry','delete')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE document_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_audit_events FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS document_audit_tenant_isolation ON document_audit_events;
CREATE POLICY document_audit_tenant_isolation ON document_audit_events
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
