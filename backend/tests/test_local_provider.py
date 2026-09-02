"""
Tests for LocalProvider — REAL local generation (not deterministic, not mock).
"""

import pytest
import os
import subprocess
import hashlib
import asyncio
from typing import Optional

from app.providers.local_provider import LocalProvider, LocalRuntimeStatus
from app.providers.base import LegacyGenerationRequest, GenerationStage


class TestLocalProvider:
    def test_provider_initialization(self):
        provider = LocalProvider()
        assert provider.name == "local"
        assert provider.api_key is None
        assert provider.get_runtime_status() in [s.value for s in LocalRuntimeStatus]

    def test_capabilities(self):
        provider = LocalProvider()
        from app.providers.base import ProviderCapability
        caps = provider.get_capabilities()
        assert ProviderCapability.TEXT_TO_VIDEO in caps
        assert ProviderCapability.IMAGE_TO_VIDEO in caps

    def test_supported_models(self):
        provider = LocalProvider()
        models = provider.get_supported_models()
        assert len(models) >= 1
        assert models[0].id == "local_cinematic_v1"
        assert "no_api_key" in models[0].metadata
        assert models[0].metadata["no_api_key"] is True
        assert models[0].metadata["no_cloud"] is True
        assert models[0].metadata["type"] == "real_local"

    def test_health_check(self):
        provider = LocalProvider()
        health = asyncio.run(provider.health_check())
        if provider.get_runtime_status() == "available":
            assert health.status == "available"
        else:
            assert health.status == "unavailable"

    def test_ffmpeg_runtime_detection(self):
        provider = LocalProvider()
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            assert provider.get_runtime_status() == "available"
        else:
            assert provider.get_runtime_status() != "available"

    def test_real_local_generation_produces_artifact(self):
        if not os.path.exists("/usr/bin/ffmpeg") and not _which("ffmpeg"):
            pytest.skip("FFmpeg not available")
        provider = LocalProvider()
        if provider.get_runtime_status() != "available":
            pytest.skip("FFmpeg runtime unavailable")

        req = LegacyGenerationRequest(
            prompt="Test cinematic product shot",
            duration_seconds=2.0,
            width=640,
            height=480,
            fps=24,
        )
        result = asyncio.run(provider.submit_generation(req, "local_cinematic_v1"))

        assert result.status == GenerationStage.COMPLETED.value
        assert result.video_url is not None
        assert os.path.exists(result.video_url), f"Output file missing: {result.video_url}"
        size = os.path.getsize(result.video_url)
        assert size > 0, "Output file is empty"

        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_format", "-show_streams", result.video_url],
            capture_output=True, text=True, timeout=10,
        )
        assert probe.returncode == 0, f"ffprobe failed: {probe.stderr}"
        output = probe.stdout
        assert "codec_name=h264" in output
        assert "width=640" in output
        assert "height=480" in output
        assert "duration=2.000000" in output
        assert "r_frame_rate=24/1" in output

        assert result.metadata["runtime"] == "ffmpeg"
        assert result.metadata["type"] == "real_local"
        assert result.metadata["no_api_key"] is True
        assert result.metadata["no_cloud"] is True
        assert "file_size_bytes" in result.metadata
        assert "file_hash_sha256" in result.metadata
        assert result.metadata["file_size_bytes"] == size

    def test_real_local_generation_provenance(self):
        if not _which("ffmpeg"):
            pytest.skip("FFmpeg not available")
        provider = LocalProvider()
        if provider.get_runtime_status() != "available":
            pytest.skip("FFmpeg runtime unavailable")

        req = LegacyGenerationRequest(
            prompt="Provenance test",
            duration_seconds=1.0,
            width=320,
            height=240,
        )
        result = asyncio.run(provider.submit_generation(req, "local_cinematic_v1"))
        assert result.status == GenerationStage.COMPLETED.value
        file_hash = result.metadata["file_hash_sha256"]
        actual_hash = hashlib.sha256(open(result.video_url, "rb").read()).hexdigest()
        assert file_hash == actual_hash, "File hash mismatch"

    def test_no_api_key_required(self):
        provider = LocalProvider()
        assert provider.api_key is None
        health = asyncio.run(provider.health_check())
        assert health is not None

    def test_cancellation(self):
        provider = LocalProvider()
        result = asyncio.run(provider.cancel_job("fake-job-id"))
        assert result is True

    def test_failed_generation_returns_failed_status(self):
        if not _which("ffmpeg"):
            pytest.skip("FFmpeg not available")
        provider = LocalProvider()
        if provider.get_runtime_status() != "available":
            pytest.skip("FFmpeg runtime unavailable")
        req = LegacyGenerationRequest(
            prompt="x" * 100000,
            duration_seconds=1.0,
            width=320,
            height=240,
        )
        result = asyncio.run(provider.submit_generation(req, "local_cinematic_v1"))
        assert result is not None


def _which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)
