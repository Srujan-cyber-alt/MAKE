"""Tests for MAKE Autonomous Agent Core V2 — API."""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.routers.intelligence_v2 import reset_job_manager


class TestIntelligenceV2API:
    def setup_method(self):
        reset_job_manager()

    def test_create_job(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2api@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2api@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/intelligence/jobs", json={"intent": "test api"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "test api"
        assert data["status"] == "pending"

    def test_get_job(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2get@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2get@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "get test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/intelligence/jobs/{job_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["intent"] == "get test"

    def test_list_jobs(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2list@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2list@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/intelligence/jobs", json={"intent": "job1"}, headers=headers)
        client.post("/api/v1/intelligence/jobs", json={"intent": "job2"}, headers=headers)
        response = client.get("/api/v1/intelligence/jobs", headers=headers)
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) >= 2

    def test_cancel_job(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2cancel@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2cancel@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "cancel test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.post(f"/api/v1/intelligence/jobs/{job_id}/cancel", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_get_job_events(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2events@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2events@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "events test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/intelligence/jobs/{job_id}/events", headers=headers)
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "job_created"

    def test_get_job_artifacts(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2artifacts@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2artifacts@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "artifacts test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/intelligence/jobs/{job_id}/artifacts", headers=headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_get_job_trace(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2trace@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2trace@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "trace test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/intelligence/jobs/{job_id}/trace", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "trace test"

    def test_get_job_status(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2status@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2status@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "status test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.get(f"/api/v1/intelligence/jobs/{job_id}/status", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_resume_job(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2resume@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2resume@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        create_resp = client.post("/api/v1/intelligence/jobs", json={"intent": "resume test"}, headers=headers)
        job_id = create_resp.json()["job_id"]
        response = client.post(f"/api/v1/intelligence/jobs/{job_id}/resume", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] == "resumed"

    def test_get_project_state_not_found(self):
        client = TestClient(app)
        client.post("/api/v1/auth/register", json={"email": "v2proj@test.com", "password": "testpass123"})
        login = client.post("/api/v1/auth/token", data={"username": "v2proj@test.com", "password": "testpass123"})
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get(f"/api/v1/intelligence/projects/{uuid4()}/state", headers=headers)
        assert response.status_code == 404
