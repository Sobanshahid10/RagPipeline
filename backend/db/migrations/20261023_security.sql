-- Run as the migration administrator after provisioning rag_runtime.
BEGIN;
ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_doc_hash_key;
CREATE UNIQUE INDEX IF NOT EXISTS documents_tenant_doc_hash_key ON documents(tenant_id,doc_hash);
ALTER TABLE documents FORCE ROW LEVEL SECURITY;
ALTER TABLE chunks FORCE ROW LEVEL SECURITY;
ALTER TABLE entity_triples FORCE ROW LEVEL SECURITY;
ALTER TABLE query_interactions FORCE ROW LEVEL SECURITY;
-- Legacy embeddings may contain synthetic vectors and have no reliable model provenance.
-- Preserve originals but prevent these documents from being used until reindexed.
UPDATE documents SET status='failed', updated_at=NOW(),
 metadata=metadata || '{"stage":"reindex_required","error":"Reindex required: legacy embeddings have no verified provider provenance."}'::jsonb
WHERE status='indexed' AND metadata->>'embedding_identity' IS NULL;

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

COMMIT;
