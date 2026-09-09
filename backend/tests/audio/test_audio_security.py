"""Security tests for MAKE Audio subsystem."""

import pytest
import os
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client):
    import uuid
    email = f"audiosec_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAudioSecurity:
    def test_unauthorized_status(self, client):
        resp = client.get("/v1/audio/status")
        assert resp.status_code == 401

    def test_unauthorized_voice_generation(self, client):
        resp = client.post("/v1/audio/generate/voice", json={"text": "test"})
        assert resp.status_code == 401

    def test_unauthorized_dialogue(self, client):
        resp = client.post("/v1/audio/generate/dialogue", json={"script": [], "voices": {}})
        assert resp.status_code == 401

    def test_invalid_emotion(self, client, auth_headers):
        resp = client.post("/v1/audio/transform/emotion", json={"audio_path": "/dev/null", "emotion": "nonexistent"}, headers=auth_headers)
        assert resp.status_code == 400

    def test_invalid_foley_event(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/foley", json={"event_type": "", "timing": 0.0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_negative_timing(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/foley", json={"event_type": "footstep", "timing": -1.0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_long_text(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/voice", json={"text": "x" * 5001, "voice_id": "test"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_empty_text(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/voice", json={"text": "", "voice_id": "test"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_invalid_duration(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/voice", json={"text": "test", "voice_id": "test", "duration_seconds": 0.0}, headers=auth_headers)
        assert resp.status_code == 422

    def test_provenance_not_found(self, client, auth_headers):
        resp = client.get("/v1/audio/provenance/nonexistent_id", headers=auth_headers)
        assert resp.status_code == 404

    def test_path_traversal_in_provenance(self, client, auth_headers):
        resp = client.get("/v1/audio/provenance/../../etc/passwd", headers=auth_headers)
        assert resp.status_code == 404
