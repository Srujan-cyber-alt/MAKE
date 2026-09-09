"""Tests for MAKE Audio API routes."""

import pytest
import os
import uuid
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers(client):
    email = f"audiosession_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "testpass123"})
    login = client.post("/api/v1/auth/token", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAudioAPI:
    def test_status(self, client, auth_headers):
        resp = client.get("/v1/audio/status", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "voice" in data["available_models"]

    def test_generate_voice(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/voice", json={"text": "hello world", "voice_id": "test"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] != ""
        assert data["sample_rate"] == 16000
        assert os.path.exists(data["audio_path"])

    def test_generate_dialogue(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/dialogue", json={"script": [{"speaker": "A", "text": "hi"}], "voices": {"A": "va"}}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] != ""

    def test_generate_music(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/music", json={"prompt": "ambient", "duration_seconds": 1.0, "genre": "ambient"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] != ""

    def test_generate_soundscape(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/soundscape", json={"environment": "forest", "duration_seconds": 1.0}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] != ""

    def test_generate_foley(self, client, auth_headers):
        resp = client.post("/v1/audio/generate/foley", json={"event_type": "footstep", "timing": 0.0}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] != ""

    def test_mix_tracks(self, client, auth_headers):
        resp = client.post("/v1/audio/mix", json={"tracks": [{"path": "/dev/null", "type": "dialogue"}], "output_format": "wav"}, headers=auth_headers)
        assert resp.status_code == 200

    def test_apply_emotion(self, client, auth_headers):
        resp = client.post("/v1/audio/transform/emotion", json={"audio_path": "/dev/null", "emotion": "happy", "intensity": 1.0}, headers=auth_headers)
        assert resp.status_code == 200

    def test_unauthorized_access(self, client):
        resp = client.get("/v1/audio/status")
        assert resp.status_code == 401
