"""Tests for Audio Forensics V2."""
import numpy as np
import pytest
from app.make_model.audio.forensics import AudioForensics, ForensicReport


class TestForensicsV2:
    @pytest.fixture
    def forensics(self):
        return AudioForensics(sample_rate=16000)

    @pytest.fixture
    def clean_audio(self):
        t = np.arange(8000) / 16000
        return (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_forensics_creation(self, forensics):
        assert forensics.sample_rate == 16000

    def test_analyze_clean_audio(self, forensics, clean_audio):
        report = forensics.analyze(clean_audio)
        assert isinstance(report, ForensicReport)
        assert report.total_samples == len(clean_audio)

    def test_detect_clipping(self, forensics):
        audio = np.ones(8000, dtype=np.float32) * 0.99
        report = forensics.analyze(audio)
        assert report.clipping is not None

    def test_detect_dc_offset(self, forensics):
        audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32) + 0.5
        report = forensics.analyze(audio)
        assert abs(report.dc_offset) > 0.1

    def test_detect_abnormal_silence(self, forensics):
        audio = np.zeros(8000, dtype=np.float32)
        report = forensics.analyze(audio)
        assert report.abnormal_silence is not None

    def test_detect_spectral_spikes(self, forensics):
        t = np.arange(8000) / 16000
        audio = (0.1 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio[1000] = 0.9
        report = forensics.analyze(audio)
        assert report.spectral_anomalies is not None

    def test_detect_discontinuity(self, forensics):
        audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32)
        audio[4000] = 1.0
        audio[4001] = -1.0
        report = forensics.analyze(audio)
        assert report.discontinuities is not None

    def test_format_detection(self, forensics, clean_audio):
        report = forensics.analyze(clean_audio)
        assert report.format is not None
        assert report.sample_rate == 16000

    def test_sha256_computed(self, forensics, clean_audio):
        report = forensics.analyze(clean_audio)
        assert len(report.sha256) > 0

    def test_full_report(self, forensics, clean_audio):
        report = forensics.analyze(clean_audio)
        assert report.to_dict() is not None
        d = report.to_dict()
        assert "total_samples" in d
        assert "sha256" in d

    def test_determinism(self, forensics, clean_audio):
        r1 = forensics.analyze(clean_audio)
        r2 = forensics.analyze(clean_audio)
        assert r1.sha256 == r2.sha256
        assert r1.dc_offset == r2.dc_offset
