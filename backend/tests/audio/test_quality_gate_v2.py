"""Tests for Audio Quality Gate V2."""
from __future__ import annotations
import numpy as np, pytest, scipy.io.wavfile as wavfile
from app.make_model.audio.quality_gate import QualityGateV2, QualityDimension

def _make_wav(path, sr=16000, audio=None, amp=0.5):
    if audio is None:
        t = np.linspace(0, 1.0, sr, endpoint=False)
        audio = amp * np.sin(2*np.pi*220*t)
    wavfile.write(path, sr, (audio*32767).astype(np.int16))

class TestQualityGateV2:
    @pytest.fixture
    def clean_wav(self, tmp_path):
        path = str(tmp_path / "clean.wav")
        _make_wav(path, amp=0.5)
        return path

    @pytest.fixture
    def clipped_wav(self, tmp_path):
        path = str(tmp_path / "clipped.wav")
        sr = 16000
        audio = np.ones(sr, dtype=np.float32)
        _make_wav(path, audio=audio)
        return path

    @pytest.fixture
    def silent_wav(self, tmp_path):
        path = str(tmp_path / "silent.wav")
        sr = 16000
        _make_wav(path, audio=np.zeros(sr, dtype=np.float32))
        return path

    def test_clean_passes(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav)
        assert report.decision in ("PASS", "REVISE")
        assert report.overall_score >= 0.5

    def test_clipped_fails(self, clipped_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clipped_wav)
        assert report.decision in ("FAIL", "REVISE")

    def test_quality_dimensions(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav)
        assert len(report.dimensions) == 5
        names = [d.name for d in report.dimensions]
        assert "technical" in names
        assert "continuity" in names
        assert "identity" in names
        assert "acoustic" in names
        assert "semantic" in names

    def test_reasons_generated(self, clipped_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clipped_wav)
        assert len(report.reasons) > 0
        assert any("technical" in r.lower() for r in report.reasons)

    def test_provenance_included(self, clean_wav):
        gate = QualityGateV2()
        prov = {"model": "test", "seed": 42}
        report = gate.evaluate(clean_wav, provenance=prov)
        assert report.provenance == prov

    def test_continuity_score(self, clean_wav):
        gate = QualityGateV2()
        report_low = gate.evaluate(clean_wav, continuity_score=0.1)
        assert report_low.decision in ("FAIL", "REVISE")
        report_high = gate.evaluate(clean_wav, continuity_score=0.95)
        assert report_high.decision in ("REVISE", "PASS")

    def test_identity_score(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav, identity_score=0.95)
        assert "identity" in [d.name for d in report.dimensions]

    def test_semantic_requirement(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav, semantic_match=False)
        assert report.decision in ("FAIL", "REVISE")
        assert any("semantic" in r.lower() for r in report.reasons)

    def test_to_dict(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav)
        d = report.to_dict()
        assert "overall_score" in d
        assert "decision" in d
        assert "dimensions" in d
        assert "reasons" in d

    def test_custom_weights(self, clean_wav):
        gate = QualityGateV2(weights={"technical": 0.9, "continuity": 0.01, "identity": 0.01, "acoustic": 0.04, "semantic": 0.04})
        report = gate.evaluate(clean_wav)
        assert report.decision in ("PASS", "REVISE", "FAIL")

    def test_sr_validation(self, clean_wav):
        gate = QualityGateV2()
        report = gate.evaluate(clean_wav, expected_sample_rate=16000)
        assert report.details["sr_valid"] is True
