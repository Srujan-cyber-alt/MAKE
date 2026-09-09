"""
Tests for Audio Quality Gate.

Tests PASS/REVISE/FAIL decisions and individual measurements.
"""

from __future__ import annotations

import numpy as np
import pytest
import scipy.io.wavfile as wavfile
import asyncio

from app.make_model.audio.quality import AudioQualityEvaluator


def _make_wav(path: str, sr: int = 16000, audio: np.ndarray = None, amplitude: float = 0.5):
    if audio is None:
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = amplitude * np.sin(2 * np.pi * 220.0 * t)
    wavfile.write(path, sr, (audio * 32767).astype(np.int16))


class TestQualityGate:
    @pytest.fixture
    def clean_wav(self, tmp_path):
        path = str(tmp_path / "clean.wav")
        _make_wav(path, amplitude=0.5)
        return path

    @pytest.fixture
    def clipped_wav(self, tmp_path):
        path = str(tmp_path / "clipped.wav")
        sr = 16000
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = np.ones_like(t, dtype=np.float32)
        _make_wav(path, audio=audio)
        return path

    @pytest.fixture
    def silent_wav(self, tmp_path):
        path = str(tmp_path / "silent.wav")
        sr = 16000
        audio = np.zeros(sr, dtype=np.float32)
        _make_wav(path, audio=audio)
        return path

    def test_clean_audio_passes(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert report.snr_db > 0
        assert report.clipping_ratio < 0.1
        assert report.silence_ratio < 0.3
        assert report.details["crest_factor"] > 1.0
        assert report.details["peak"] > 0.3
        assert 0.0 <= report.overall_score <= 1.0

    def test_clean_audio_quality_fields(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert "sample_rate" in report.details
        assert "samples" in report.details
        assert "duration_seconds" in report.details
        assert "crest_factor" in report.details
        assert "dc_offset" in report.details
        assert "dynamic_range" in report.details
        assert "rms" in report.details
        assert "thd" in report.details

    def test_clipped_audio_fails(self, clipped_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clipped_wav))
        assert report.clipping_ratio > 0.5
        assert report.passed is False

    def test_silent_audio_fails(self, silent_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(silent_wav))
        assert report.silence_ratio > 0.9
        assert report.passed is False

    def test_gate_decision_pass(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        decision, report = evaluator.gate(clean_wav)
        assert decision in ("PASS", "REVISE")

    def test_gate_decision_fail(self, clipped_wav):
        evaluator = AudioQualityEvaluator()
        decision, report = evaluator.gate(clipped_wav)
        assert decision in ("FAIL", "REVISE")

    def test_crest_factor(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert report.details["crest_factor"] > 1.0

    def test_dc_offset(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert abs(report.details["dc_offset"]) < 0.1

    def test_dynamic_range(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert report.details["dynamic_range"] > 0

    def test_overall_score_range(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert 0.0 <= report.overall_score <= 1.0

    def test_snr_calculation(self, clean_wav):
        evaluator = AudioQualityEvaluator()
        report = asyncio.run(evaluator.evaluate(clean_wav))
        assert report.snr_db > 0
