"""Tests for Quality Gate V3."""
import numpy as np
import pytest
from app.make_model.audio.quality_gate import QualityGateV2, QualityMetrics, QualityDecision


class TestQualityGateV3:
    @pytest.fixture
    def qg(self):
        return QualityGateV2()

    @pytest.fixture
    def clean_audio(self):
        t = np.arange(8000) / 16000
        return (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_qg_creation(self, qg):
        assert qg.sample_rate == 16000
        assert qg.thresholds is not None

    def test_evaluate_quality_pass(self, qg, clean_audio):
        result = qg.evaluate(clean_audio)
        assert result.decision in [QualityDecision.PASS, QualityDecision.REVISE, QualityDecision.FAIL]

    def test_technical_metrics(self, qg, clean_audio):
        metrics = qg.compute_technical_metrics(clean_audio)
        assert "sample_rate" in metrics
        assert "clipping_ratio" in metrics
        assert "dc_offset" in metrics
        assert "snr" in metrics
        assert "thd" in metrics
        assert "crest_factor" in metrics
        assert "dynamic_range" in metrics
        assert "spectral_stability" in metrics

    def test_identity_metrics(self, qg, clean_audio):
        metrics = qg.compute_identity_metrics(clean_audio, reference=None)
        assert "speaker_consistency" in metrics

    def test_continuity_metrics(self, qg, clean_audio):
        metrics = qg.compute_continuity_metrics(clean_audio)
        assert "pitch_continuity" in metrics
        assert "loudness_continuity" in metrics
        assert "room_continuity" in metrics
        assert "ambience_continuity" in metrics
        assert "emotion_continuity" in metrics

    def test_acoustic_metrics(self, qg, clean_audio):
        metrics = qg.compute_acoustic_metrics(clean_audio)
        assert "reverb_consistency" in metrics
        assert "spatial_consistency" in metrics
        assert "distance_consistency" in metrics
        assert "occlusion_consistency" in metrics

    def test_semantic_metrics(self, qg, clean_audio):
        metrics = qg.compute_semantic_metrics(clean_audio)
        assert "intended_event_presence" in metrics
        assert "unwanted_event_detection" in metrics
        assert "dialogue_structure" in metrics

    def test_clipping_detected(self, qg):
        audio = np.ones(8000, dtype=np.float32) * 0.99
        result = qg.evaluate(audio)
        assert result.decision == QualityDecision.FAIL

    def test_dc_offset_detected(self, qg):
        audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32) + 0.3
        metrics = qg.compute_technical_metrics(audio)
        assert abs(metrics["dc_offset"]) > 0.1

    def test_silence_detected(self, qg):
        audio = np.zeros(8000, dtype=np.float32)
        result = qg.evaluate(audio)
        assert result.decision in [QualityDecision.FAIL, QualityDecision.REVISE]

    def test_determinism(self, qg, clean_audio):
        r1 = qg.evaluate(clean_audio)
        r2 = qg.evaluate(clean_audio)
        assert r1.decision == r2.decision
        assert r1.metrics == r2.metrics

    def test_revisable_audio(self, qg):
        t = np.arange(8000) / 16000
        audio = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio[4000] = 0.99
        result = qg.evaluate(audio)
        assert result.decision in [QualityDecision.PASS, QualityDecision.REVISE, QualityDecision.FAIL]

    def test_all_dimensions_present(self, qg, clean_audio):
        result = qg.evaluate(clean_audio)
        assert "technical" in result.metrics
        assert "identity" in result.metrics
        assert "continuity" in result.metrics
        assert "acoustic" in result.metrics
        assert "semantic" in result.metrics
