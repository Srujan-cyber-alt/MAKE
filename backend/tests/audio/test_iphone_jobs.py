"""
iPhone job management tests - reconnect, progress, cancellation.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import pytest

from app.make_model.audio.iphone_server import AudioIPhoneServer, AudioJob


class TestiPhoneJobManagement:
    @pytest.fixture
    def server(self, tmp_path):
        return AudioIPhoneServer(storage_dir=str(tmp_path / "iphone"))

    def test_create_job(self, server):
        job = server.create_job({"text": "hello", "voice_id": "v1"})
        assert job["status"] == "pending"
        assert "job_id" in job

    def test_get_job(self, server):
        job = server.create_job({"text": "hello", "voice_id": "v1"})
        retrieved = server.get_job(job["job_id"])
        assert retrieved is not None
        assert retrieved["job_id"] == job["job_id"]

    def test_cancel_job(self, server):
        job = server.create_job({"text": "hello", "voice_id": "v1"})
        assert server.cancel_job(job["job_id"]) is True

    def test_cancel_invalid_job(self, server):
        from uuid import uuid4
        valid_id = str(uuid4())
        assert server.cancel_job(valid_id) is False

    def test_job_persistence(self, tmp_path):
        storage = str(tmp_path / "persist")
        server = AudioIPhoneServer(storage_dir=storage)
        job = server.create_job({"text": "persist", "voice_id": "v1"})
        server2 = AudioIPhoneServer(storage_dir=storage)
        retrieved = server2.get_job(job["job_id"])
        assert retrieved is not None
        assert retrieved["params"]["text"] == "persist"

    def test_job_cancellation_persists(self, tmp_path):
        storage = str(tmp_path / "persist2")
        server = AudioIPhoneServer(storage_dir=storage)
        job = server.create_job({"text": "test", "voice_id": "v1"})
        server.cancel_job(job["job_id"])
        server2 = AudioIPhoneServer(storage_dir=storage)
        retrieved = server2.get_job(job["job_id"])
        assert retrieved is not None
        assert retrieved["status"] == "cancelled"

    def test_invalid_job_id_format(self, server):
        with pytest.raises(ValueError):
            server.get_job("not-a-uuid")

    def test_validate_request_text_too_long(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"text": "a" * 6000})

    def test_validate_request_duration_too_long(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"text": "hello", "duration_seconds": 1000.0})

    def test_validate_unknown_environment(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"environment": "unknown_env"})

    def test_validate_unknown_material(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"material": "fake_material"})

    def test_reconnect_get_job(self, tmp_path):
        storage = str(tmp_path / "reconnect")
        server = AudioIPhoneServer(storage_dir=storage)
        job = server.create_job({"text": "reconnect", "voice_id": "v1"})
        client = AudioIPhoneServer(storage_dir=storage)
        retrieved = client.get_job(job["job_id"])
        assert retrieved is not None

    def test_path_traversal_rejected(self, server):
        with pytest.raises(ValueError):
            server._validate_path("../../../etc/passwd")

    def test_absolute_path_rejected(self, server):
        with pytest.raises(ValueError):
            server._validate_path("/etc/passwd")

    def test_null_byte_rejected(self, server):
        with pytest.raises(ValueError):
            server._validate_path("test\x00.wav")

    def test_job_progress(self, server):
        job = server.create_job({"text": "progress_test", "voice_id": "v1"})
        db = job["job_id"]
        internal = server._jobs[db]
        internal.progress = 0.5
        assert server.get_job(db)["progress"] == 0.5
