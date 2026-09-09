"""
Tests for Audio Forensics module.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import numpy as np
import pytest
import scipy.io.wavfile as wavfile
from pathlib import Path

from app.make_model.audio.audio_forensics import AudioForensics, ForensicReport


def _make_wav(path: str, sr: int = 16000, duration: float = 1.0, freq: float = 220.0, amplitude: float = 0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    audio = amplitude * np.sin(2 * np.pi * freq * t)
    wavfile.write(path, sr, (audio * 32767).astype(np.int16))


class TestForensics:
    @pytest.fixture
    def sample_wav(self, tmp_path):
        path = str(tmp_path / "test.wav")
        _make_wav(path, sr=16000, duration=2.0, freq=440.0, amplitude=0.5)
        return path

    @pytest.fixture
    def clipped_wav(self, tmp_path):
        path = str(tmp_path / "clipped.wav")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = np.ones_like(t, dtype=np.float32)
        wavfile.write(path, sr, (audio * 32767).astype(np.int16))
        return path

    @pytest.fixture
    def silent_wav(self, tmp_path):
        path = str(tmp_path / "silent.wav")
        sr = 16000
        audio = np.zeros(int(sr * 1.0), dtype=np.float32)
        wavfile.write(path, sr, (audio * 32767).astype(np.int16))
        return path

    def test_basic_analysis(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert report.sample_rate == 16000
        assert report.num_channels == 1
        assert report.duration_seconds == pytest.approx(2.0, abs=0.1)
        assert report.bit_depth == 16
        assert report.total_samples == 32000
        assert report.peak <= 1.0
        assert report.rms > 0

    def test_sha256_verification(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        with open(sample_wav, "rb") as f:
            expected = hashlib.sha256(f.read()).hexdigest()
        assert report.sha256 == expected

    def test_clipping_detection(self, clipped_wav):
        report = AudioForensics.analyze(clipped_wav)
        assert report.clipping_count > 0
        assert report.clipping_ratio > 0.5
        assert "high_clipping" in report.anomalies

    def test_silence_detection(self, silent_wav):
        report = AudioForensics.analyze(silent_wav)
        assert report.silence_ratio > 0.9
        assert "high_silence_ratio" in report.anomalies

    def test_crest_factor(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert report.crest_factor > 1.0
        assert report.crest_factor < 10.0

    def test_dc_offset(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert abs(report.dc_offset) < 0.1

    def test_dynamic_range(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert report.dynamic_range_db > 0

    def test_spectral_center(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert report.spectral_center_hz > 0
        assert report.spectral_center_hz < 8000

    def test_report_to_dict(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        d = report.to_dict()
        assert "file_path" in d
        assert "sha256" in d
        assert "provenance" in d
        assert "anomalies" in d

    def test_discontinuity_detection(self, tmp_path):
        path = str(tmp_path / "discontinuous.wav")
        sr = 16000
        audio = np.zeros(int(sr * 1.0), dtype=np.float32)
        audio[sr // 2] = 1.0
        wavfile.write(path, sr, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert report.discontinuities > 0

    def test_file_size(self, sample_wav):
        report = AudioForensics.analyze(sample_wav)
        assert report.file_size_bytes > 0
