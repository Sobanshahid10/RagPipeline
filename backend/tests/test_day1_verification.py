import pytest
from app.config import settings
from app.main import app, get_health, get_info
from app.celery_app import celery_app
import os


def test_settings_loaded():
    """Verify Pydantic settings are correctly populated with Day 1 defaults/env values."""
    assert settings.PROJECT_NAME == "Production RAG Engine"
    assert settings.API_V1_STR == "/api/v1"
    assert "postgresql" in settings.DATABASE_URL
    assert "redis" in settings.REDIS_URL
    assert settings.JWT_SECRET != ""
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440


def test_fastapi_app_metadata():
    """Verify FastAPI application title, docs URL, and OpenAPI specs."""
    assert app.title == settings.PROJECT_NAME
    assert app.docs_url == "/docs"
    assert app.openapi_url == f"{settings.API_V1_STR}/openapi.json"
    
    # Verify routes exist
    routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            routes.append(route.path)
        elif hasattr(route, "routes"):
            for sub_route in route.routes:
                if hasattr(sub_route, "path"):
                    routes.append(sub_route.path)
    assert "/health" in routes
    assert f"{settings.API_V1_STR}/info" in routes
    assert "/docs" in routes
    assert f"{settings.API_V1_STR}/openapi.json" in routes



@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify /health response structure and values."""
    res = await get_health()
    assert res.status == "healthy"
    assert res.version == "1.0.0"


@pytest.mark.asyncio
async def test_info_endpoint():
    """Verify /api/v1/info response structure and values."""
    res = await get_info()
    assert res.project == settings.PROJECT_NAME
    assert res.environment == "development"


def test_celery_worker_configuration():
    """Verify Celery app setup, broker, and multi-priority queue routes."""
    assert celery_app.main == "rag_worker"
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True
    assert "high_priority" in celery_app.conf.task_routes["app.tasks.high_priority.*"]["queue"]
    assert "low_priority" in celery_app.conf.task_routes["app.tasks.low_priority.*"]["queue"]


def test_init_sql_integrity():
    """Verify SQL init script contains all required extensions, tables, indexes, and RLS statements."""
    init_sql_path = os.path.join(os.path.dirname(__file__), "..", "db", "init.sql")
    assert os.path.exists(init_sql_path), "init.sql must exist"
    
    with open(init_sql_path, "r") as f:
        sql = f.read()

    # Check required extensions
    assert 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"' in sql
    assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in sql
    assert 'CREATE EXTENSION IF NOT EXISTS "pg_trgm"' in sql

    # Check extension order
    pos_uuid = sql.find('"uuid-ossp"')
    pos_vec = sql.find('"vector"')
    pos_trgm = sql.find('"pg_trgm"')
    assert pos_uuid < pos_vec < pos_trgm, "Extensions must be created in order: uuid-ossp, vector, pg_trgm"

    # Check tables
    required_tables = [
        "tenants",
        "users",
        "documents",
        "chunks",
        "entity_triples",
        "query_interactions",
        "eval_scores",
    ]
    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql, f"Table {table} missing in init.sql"

    # Check vector column definition
    assert "VECTOR(1536)" in sql
    assert "TSVECTOR" in sql

    # Check HNSW and GIN indexes
    assert "idx_chunks_hnsw" in sql
    assert "vector_cosine_ops" in sql
    assert "m = 16, ef_construction = 64" in sql
    assert "idx_chunks_sparse_tsv" in sql
    assert "gin (sparse_tsv)" in sql

    # Check RLS statements
    assert "ALTER TABLE documents ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE chunks ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE entity_triples ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE query_interactions ENABLE ROW LEVEL SECURITY;" in sql


def test_dockerfile_and_compose_integrity():
    """Verify docker-compose.yml and Dockerfile specifications."""
    root_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    compose_path = os.path.join(root_dir, "docker-compose.yml")
    dockerfile_path = os.path.join(os.path.dirname(__file__), "..", "Dockerfile")
    
    with open(compose_path, "r") as f:
        compose_content = f.read()
    
    assert "pgvector/pgvector:pg16" in compose_content
    assert "redis:7-alpine" in compose_content
    assert "rag_postgres" in compose_content
    assert "rag_redis" in compose_content
    assert "rag_backend" in compose_content
    assert "rag_celery_worker" in compose_content
    assert "pg_isready -U rag_user -d rag_db" in compose_content
    assert "redis-cli" in compose_content
    assert "service_healthy" in compose_content
    assert "high_priority,low_priority" in compose_content

    with open(dockerfile_path, "r") as f:
        df_content = f.read()

    assert "python:3.11-slim" in df_content
    assert "build-essential" in df_content
    assert "requirements.txt" in df_content
    assert "uvicorn" in df_content
    assert "app.main:app" in df_content
