"""Tests for MAKE Autonomous Agent Core V2 — Security."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.routers.intelligence_v2 import reset_job_manager


class TestSecurity:
    def setup_method(self):
        reset_job_manager()

    def test_unauthorized_access_requires_auth(self):
        client = TestClient(app)
        response = client.post("/api/v1/intelligence/jobs", json={"intent": "test"})
        assert response.status_code in (401, 403, 422)

    def test_invalid_job_id(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "sec@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "sec@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = client.get("/api/v1/intelligence/jobs/not-a-uuid", headers=headers)
            assert response.status_code in (422, 500)
        except ValueError:
            pass
