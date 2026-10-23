GRANT USAGE ON SCHEMA public TO rag_runtime;
GRANT SELECT, INSERT ON tenants, users TO rag_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON documents, chunks, entity_triples, query_interactions TO rag_runtime;
-- Public-book tables are provisioned separately by the repository index CLI.
DO $$ BEGIN
 IF to_regclass('public.public_book_chunks') IS NOT NULL THEN
  GRANT SELECT ON public_book_chunks, public_book_index_manifest TO rag_runtime;
 END IF;
END $$;

GRANT SELECT, INSERT ON document_audit_events TO rag_runtime;
