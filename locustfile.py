"""Locust load testing suite for the Production RAG Engine.

Simulates 100 concurrent users performing factual queries (80% weight) and
document ingestion uploads (20% weight).
"""

from __future__ import annotations

import os
from locust import HttpUser, between, task


class RAGUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Authenticate and obtain JWT access token for the simulated user."""
        response = self.client.post(
            "/api/v1/auth/login",
            data={
                "username": "loadtest@rag.local",
                "password": "LoadTest2026!",
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Fallback headers if test user not seeded
            self.headers = {}

    @task(8)
    def factual_query(self) -> None:
        """Stream factual query endpoint (80% of traffic)."""
        self.client.post(
            "/api/v1/query",
            json={"query": "What is the annual leave policy?"},
            headers=self.headers,
            stream=True,
            name="/api/v1/query",
        )

    @task(2)
    def upload_document(self) -> None:
        """Upload test document (20% of traffic)."""
        fixture_path = "tests/fixtures/sample.pdf"
        if os.path.exists(fixture_path):
            with open(fixture_path, "rb") as f:
                self.client.post(
                    "/api/v1/documents/upload",
                    files={"file": ("sample.pdf", f, "application/pdf")},
                    headers=self.headers,
                    name="/api/v1/documents/upload",
                )
        else:
            dummy_content = (
                b"Load testing document: Standard operating policy for enterprise engineering. "
                b"Employees receive 25 days paid time off per calendar year."
            )
            self.client.post(
                "/api/v1/documents/upload",
                files={"file": ("sample_policy.txt", dummy_content, "text/plain")},
                headers=self.headers,
                name="/api/v1/documents/upload",
            )


# CLI Usage:
# locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m --headless --host http://localhost:8000
# Target Pass Criteria: p95 TTFT < 200ms, overall error rate < 1%
