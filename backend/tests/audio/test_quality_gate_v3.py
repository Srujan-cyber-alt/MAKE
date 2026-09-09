"""Tests for Quality Gate V3 - V2 enhanced with array support and V3 metrics."""
import numpy as np
import scipy.io.wavfile as wavfile
import pytest
from app.make_model.audio.quality_gate import QualityGateV2, QualityReportV2, QualityDimension


class TestQualityGateV3:
    @pytest.fixture
    def qg(self):
        return QualityGateV2(sample_rate=16000)

    @pytest.fixture
    def clean_audio(self):
        t = np.arange(8000) / 16000
        return (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    @pytest.fixture
    def clean_audio_path(self, clean_audio, tmp_path):
        path = str(tmp_path / "clean.wav")
        wavfile.write(path, 16000, (clean_audio * 32767).astype(np.int16))
        return path

    def test_qg_creation(self, qg):
        assert qg.sample_rate == 16000
        assert qg.weights is not None

    def test_evaluate_quality_pass(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path)
        assert isinstance(report, QualityReportV2)
        assert report.decision in ["PASS", "REVISE", "FAIL"]

    def test_technical_metrics(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path)
        assert "sample_rate" in report.details
        assert "clipping_ratio" in report.details
        assert "dc_offset" in report.details
        assert "snr_db" in report.details
        assert "thd" in report.details
        assert "crest_factor" in report.details

    def test_continuity_dimension(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path, continuity_score=1.0)
        cont_dim = [d for d in report.dimensions if d.name == "continuity"]
        assert len(cont_dim) == 1
        assert cont_dim[0].score == 1.0

    def test_identity_dimension(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path, identity_score=0.9)
        id_dim = [d for d in report.dimensions if d.name == "identity"]
        assert len(id_dim) == 1

    def test_acoustic_dimension(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path, room_rt60=0.5)
        ac_dim = [d for d in report.dimensions if d.name == "acoustic"]
        assert len(ac_dim) == 1

    def test_semantic_dimension(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path, semantic_match=True)
        sem_dim = [d for d in report.dimensions if d.name == "semantic"]
        assert len(sem_dim) == 1
        assert sem_dim[0].score == 1.0

    def test_clipping_detected(self, qg, tmp_path):
        clipped = np.ones(8000, dtype=np.float32) * 0.99
        path = str(tmp_path / "clipped.wav")
        wavfile.write(path, 16000, (clipped * 32767).astype(np.int16))
        report = qg.evaluate(path)
        assert report.details["clipping_ratio"] > 0.01

    def test_determinism(self, qg, clean_audio_path):
        r1 = qg.evaluate(clean_audio_path)
        r2 = qg.evaluate(clean_audio_path)
        assert r1.decision == r2.decision
        assert r1.overall_score == r2.overall_score

    def test_all_dimensions_present(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path)
        assert "technical" in [d.name for d in report.dimensions]
        assert "continuity" in [d.name for d in report.dimensions]
        assert "identity" in [d.name for d in report.dimensions]
        assert "acoustic" in [d.name for d in report.dimensions]
        assert "semantic" in [d.name for d in report.dimensions]

    def test_to_dict(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path)
        d = report.to_dict()
        assert "overall_score" in d
        assert "decision" in d
        assert "dimensions" in d
        assert "reasons" in d

    def test_dynamic_range(self, qg, clean_audio_path):
        report = qg.evaluate(clean_audio_path)
        assert "dynamic_range_db" in report.details
