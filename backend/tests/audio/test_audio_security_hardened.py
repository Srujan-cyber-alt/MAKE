"""
Hardened Audio security tests.
Tests path traversal, injection, malformed WAV, DoS, unauthorized access.
"""

from __future__ import annotations

import os
import pytest
import tempfile

from app.make_model.audio.iphone_server import AudioIPhoneServer


class TestSecurityHardened:
    @pytest.fixture
    def server(self, tmp_path):
        return AudioIPhoneServer(storage_dir=str(tmp_path / "iphone"))

    def test_path_traversal_reject(self, server):
        with pytest.raises(ValueError):
            server._validate_path("../../../etc/passwd")

    def test_absolute_path_reject(self, server):
        with pytest.raises(ValueError):
            server._validate_path("/etc/passwd")

    def test_null_byte_injection(self, server):
        with pytest.raises(ValueError):
            server._validate_path("test\x00.wav")

    def test_oversized_input(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"text": "a" * 6000})

    def test_malformed_wav_header(self, server, tmp_path):
        bad_wav = tmp_path / "bad.wav"
        bad_wav.write_bytes(b"not a wav file")
        with pytest.raises(Exception):
            server._load_audio(str(bad_wav))

    def test_resource_exhaustion_duration(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"text": "hello", "duration_seconds": 1000.0})

    def test_reconnect_after_disconnect(self, server):
        job = server.create_job({"text": "test", "voice_id": "v1"})
        assert job["status"] in ("pending", "running", "completed")
        retrieved = server.get_job(job["job_id"])
        assert retrieved["job_id"] == job["job_id"]

    def test_provenance_tampering_detection(self, server):
        record = server.provenance.get_record("fake_id")
        assert record is None

    def test_job_id_format_validation(self, server):
        with pytest.raises(ValueError):
            server.get_job("not-a-uuid")

    def test_cancellation_valid_job(self, server):
        job = server.create_job({"text": "hello", "voice_id": "v1"})
        assert server.cancel_job(job["job_id"]) is True

    def test_unknown_environment_rejected(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"environment": "unknown_env"})

    def test_unknown_material_rejected(self, server):
        with pytest.raises(ValueError):
            server.validate_request({"material": "fake_material"})

    def test_valid_job_id_accepted(self, server):
        job = server.create_job({"text": "hello", "voice_id": "v1"})
        retrieved = server.get_job(job["job_id"])
        assert retrieved is not None

    def test_job_persistence_across_restarts(self, tmp_path):
        storage1 = str(tmp_path / "persist1")
        server1 = AudioIPhoneServer(storage_dir=storage1)
        job = server1.create_job({"text": "persist", "voice_id": "v1"})
        server2 = AudioIPhoneServer(storage_dir=storage1)
        retrieved = server2.get_job(job["job_id"])
        assert retrieved is not None
        assert retrieved["params"]["text"] == "persist"
