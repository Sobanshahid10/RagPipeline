-- Run after 20261023_security.sql, using the migration administrator.
-- Legacy turns intentionally have no scope and are excluded from follow-up context.
BEGIN;
ALTER TABLE query_interactions ADD COLUMN IF NOT EXISTS retrieval_scope TEXT;
CREATE INDEX IF NOT EXISTS idx_interactions_history
    ON query_interactions(tenant_id,user_id,session_id,retrieval_scope,created_at DESC);
COMMIT;
