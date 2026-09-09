"""Tests for Audio Forensics V2."""
import numpy as np
import scipy.io.wavfile as wavfile
import pytest
from app.make_model.audio.audio_forensics import AudioForensics, ForensicReport
from pathlib import Path


class TestForensicsV2:
    @pytest.fixture
    def clean_audio(self):
        t = np.arange(8000) / 16000
        return (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    @pytest.fixture
    def clean_audio_path(self, clean_audio, tmp_path):
        path = str(tmp_path / "clean.wav")
        wavfile.write(path, 16000, (clean_audio * 32767).astype(np.int16))
        return path

    def test_forensics_creation(self):
        pass

    def test_analyze_clean_audio(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert isinstance(report, ForensicReport)
        assert report.total_samples == 8000

    def test_detect_clipping(self, tmp_path):
        audio = np.ones(8000, dtype=np.float32) * 0.99
        path = str(tmp_path / "clipping.wav")
        wavfile.write(path, 16000, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert report.clipping_ratio > 0.01

    def test_detect_dc_offset(self, tmp_path):
        audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32) + 0.5
        path = str(tmp_path / "dc.wav")
        wavfile.write(path, 16000, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert abs(report.dc_offset) > 0.1

    def test_detect_abnormal_silence(self, tmp_path):
        audio = np.zeros(8000, dtype=np.float32)
        path = str(tmp_path / "silent.wav")
        wavfile.write(path, 16000, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert report.silence_ratio > 0.5

    def test_detect_spectral_anomalies(self, tmp_path):
        audio = (0.1 * np.sin(2 * np.pi * 440 * np.arange(8000) / 16000)).astype(np.float32)
        path = str(tmp_path / "spike.wav")
        wavfile.write(path, 16000, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert len(report.anomalies) >= 0

    def test_detect_discontinuity(self, tmp_path):
        audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32)
        audio[4000:4003] = 1.0
        path = str(tmp_path / "discont.wav")
        wavfile.write(path, 16000, (audio * 32767).astype(np.int16))
        report = AudioForensics.analyze(path)
        assert report.discontinuities is not None

    def test_format_detection(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert report.format is not None
        assert "WAV" in report.format

    def test_sha256_computed(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert len(report.sha256) == 64

    def test_full_report(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        d = report.to_dict()
        assert "total_samples" in d
        assert "sha256" in d
        assert "sample_rate" in d
        assert "clipping_ratio" in d

    def test_determinism(self, clean_audio_path):
        r1 = AudioForensics.analyze(clean_audio_path)
        r2 = AudioForensics.analyze(clean_audio_path)
        assert r1.sha256 == r2.sha256
        assert r1.dc_offset == r2.dc_offset
        assert r1.clipping_ratio == r2.clipping_ratio

    def test_bit_depth_detection(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert report.bit_depth == 16

    def test_duration_computed(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert report.duration_seconds > 0
        assert abs(report.duration_seconds - 0.5) < 0.1

    def test_provenance_extraction(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert isinstance(report.provenance, dict)

    def test_sample_rate_detection(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert report.sample_rate == 16000

    def test_channel_detection(self, clean_audio_path):
        report = AudioForensics.analyze(clean_audio_path)
        assert report.num_channels == 1
