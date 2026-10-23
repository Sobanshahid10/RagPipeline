#!/bin/sh
set -eu
: "${RUNTIME_DB_PASSWORD:?Set a unique RUNTIME_DB_PASSWORD}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv runtime_password RUNTIME_DB_PASSWORD
SELECT format('CREATE ROLE rag_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS PASSWORD %L', :'runtime_password')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='rag_runtime') \gexec
SQL
