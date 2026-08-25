"""Tests for Day 12 deliverables: Security hardening, dbt analytics, load testing, and production infrastructure."""

from __future__ import annotations

import os
import yaml
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.query import QueryRequest
from pydantic import ValidationError


@pytest.fixture
def client():
    return TestClient(app)


def test_security_headers_middleware(client):
    """Test that OWASP security headers are present on all HTTP responses."""
    response = client.get("/health")
    assert response.status_code == 200
    headers = response.headers

    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in headers
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in headers


def test_rate_limiting_middleware():
    """Test that the rate limiter triggers 429 when threshold is exceeded."""
    from fastapi import FastAPI
    from app.core.security_middleware import RateLimitingMiddleware

    test_app = FastAPI()
    test_app.add_middleware(RateLimitingMiddleware, requests_per_minute=5, window_seconds=60)

    @test_app.get("/test-rate")
    def rate_endpoint():
        return {"status": "ok"}

    c = TestClient(test_app)
    # First 5 calls pass
    for _ in range(5):
        resp = c.get("/test-rate")
        assert resp.status_code == 200

    # 6th call should be rate-limited
    resp_blocked = c.get("/test-rate")
    assert resp_blocked.status_code == 429
    assert "Rate limit exceeded" in resp_blocked.json()["detail"]
    assert "Retry-After" in resp_blocked.headers


def test_query_input_max_length_validation():
    """Test that queries exceeding 1000 characters trigger validation errors."""
    valid_query = QueryRequest(query="a" * 1000)
    assert len(valid_query.query) == 1000

    with pytest.raises(ValidationError):
        QueryRequest(query="a" * 1001)


def test_dbt_project_configuration_and_models():
    """Verify dbt project configuration, profiles, and SQL model integrity."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    dbt_dir = os.path.join(project_root, "dbt")

    dbt_project_path = os.path.join(dbt_dir, "dbt_project.yml")
    assert os.path.exists(dbt_project_path), "dbt_project.yml must exist"

    with open(dbt_project_path, "r", encoding="utf-8") as f:
        dbt_config = yaml.safe_load(f)
    assert dbt_config["name"] == "rag_analytics"
    assert "staging" in dbt_config["models"]["rag_analytics"]
    assert "marts" in dbt_config["models"]["rag_analytics"]

    # Verify model SQL files exist and contain required keywords
    models_dir = os.path.join(dbt_dir, "models")
    stg_query = os.path.join(models_dir, "staging", "stg_query_interactions.sql")
    stg_eval = os.path.join(models_dir, "staging", "stg_eval_scores.sql")
    fct_perf = os.path.join(models_dir, "marts", "fct_daily_performance.sql")
    rpt_eval = os.path.join(models_dir, "marts", "rpt_eval_dashboard.sql")
    schema_file = os.path.join(models_dir, "schema.yml")

    for path in [stg_query, stg_eval, fct_perf, rpt_eval, schema_file]:
        assert os.path.exists(path), f"File {path} must exist"

    with open(fct_perf, "r", encoding="utf-8") as f:
        content = f.read()
        assert "p95_ttft_ms" in content
        assert "PERCENTILE_CONT" in content
        assert "thumbs_up_rate" in content


def test_locustfile_structure():
    """Verify locustfile contains RAGUser class and defined tasks."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    locust_path = os.path.join(project_root, "locustfile.py")
    assert os.path.exists(locust_path), "locustfile.py must exist at project root"

    with open(locust_path, "r", encoding="utf-8") as f:
        content = f.read()
        assert "class RAGUser" in content
        assert "factual_query" in content
        assert "upload_document" in content


def test_docker_compose_prod_configuration():
    """Verify production docker-compose configuration."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    prod_compose_path = os.path.join(project_root, "docker-compose.prod.yml")
    assert os.path.exists(prod_compose_path), "docker-compose.prod.yml must exist"

    with open(prod_compose_path, "r", encoding="utf-8") as f:
        compose_cfg = yaml.safe_load(f)

    services = compose_cfg.get("services", {})
    assert "nginx" in services
    assert "postgres" in services
    assert "redis" in services
    assert "backend" in services
    assert "celery_worker" in services

    backend_svc = services["backend"]
    assert backend_svc.get("deploy", {}).get("replicas") == 2
    assert backend_svc.get("restart") == "unless-stopped"
    assert "--reload" not in backend_svc.get("command", "")


def test_security_markdown_checklist_completeness():
    """Verify SECURITY.md contains all 8 required checklist items."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    sec_path = os.path.join(project_root, "SECURITY.md")
    assert os.path.exists(sec_path), "SECURITY.md must exist"

    with open(sec_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_keywords = [
        "JWT Secret Length",
        "No Hardcoded Secrets",
        "OWASP Security Headers",
        "Row-Level Security",
        "Rate Limiting",
        "Redis Password",
        "Input Validation",
        "XSS Prevention",
    ]
    for kw in required_keywords:
        assert kw.lower() in content.lower(), f"Missing security item keyword: {kw}"
