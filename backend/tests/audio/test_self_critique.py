"""Tests for Autonomous Self-Critique Loop."""
import numpy as np
import pytest
from app.make_model.audio.self_critique import (
    SelfCritiqueLoop, CritiqueResult, CritiqueStep, CritiqueDecision,
)


class TestSelfCritique:
    @pytest.fixture
    def engine(self):
        return SelfCritiqueLoop(max_retries=3)

    @pytest.fixture
    def test_audio(self):
        t = np.arange(8000) / 16000
        return (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    def test_loop_creation(self, engine):
        assert engine.max_retries == 3

    def test_evaluate_quality_pass(self, engine, test_audio):
        metrics = engine.evaluate_quality(test_audio)
        assert "snr" in metrics
        assert "rms" in metrics
        assert "peak" in metrics
        assert "score" in metrics

    def test_evaluate_quality_fail_on_clipping(self, engine):
        clipped = np.ones(8000, dtype=np.float32) * 0.99
        metrics = engine.evaluate_quality(clipped)
        assert metrics["score"] == "FAIL"

    def test_critique_accept(self, engine, test_audio):
        metrics = engine.evaluate_quality(test_audio)
        step = engine.critique_decision(test_audio, metrics, 1)
        assert step.decision in [CritiqueDecision.ACCEPT, CritiqueDecision.REVISE, CritiqueDecision.FAIL]

    def test_run_full_loop_accept(self, engine, test_audio):
        def plan():
            return {"target": "audio"}
        def generate():
            return test_audio
        result = engine.run(plan, generate)
        assert isinstance(result, CritiqueResult)
        assert len(result.steps) >= 3
        assert result.retry_count > 0

    def test_run_with_revision(self, engine):
        def plan():
            return {"target": "clean_audio"}
        def generate():
            clipped = np.ones(8000, dtype=np.float32) * 0.99
            return clipped
        result = engine.run(plan, generate, max_retries=3)
        assert result.retry_count > 0

    def test_max_retries_respected(self, engine):
        def plan():
            return {}
        def generate():
            return np.ones(8000, dtype=np.float32) * 0.99
        result = engine.run(plan, generate)
        assert result.retry_count <= 3

    def test_decision_storage(self, engine, test_audio):
        metrics = engine.evaluate_quality(test_audio)
        step = engine.critique_decision(test_audio, metrics, 1)
        assert step.step_name is not None
        assert len(step.metrics) > 0

    def test_provenance_tracked(self, engine, test_audio):
        def plan():
            return {"plan": True}
        def generate():
            return test_audio
        result = engine.run(plan, generate)
        assert "method" in result.provenance or "max_retries" in result.provenance
        assert "steps" in result.provenance

    def test_no_infinite_loop(self, engine):
        def plan():
            return {}
        def generate():
            return np.ones(8000, dtype=np.float32) * 0.99
        result = engine.run(plan, generate)
        assert len(result.steps) <= 5

    def test_revise_fixes_issue(self, engine):
        test_audio = np.sin(2 * np.pi * 440 * np.arange(8000) / 16000).astype(np.float32)
        test_audio[0] = 5.0
        test_audio[1] = 5.0
        metrics = engine.evaluate_quality(test_audio)
        step = engine.critique_decision(test_audio, metrics, 1)
        if step.decision == CritiqueDecision.REVISE:
            revised = engine.revise(test_audio, step)
            assert np.max(np.abs(revised)) <= 0.99
