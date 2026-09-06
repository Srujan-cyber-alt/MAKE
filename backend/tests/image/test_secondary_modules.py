"""Tests for MAKE Image Engine generation, editing, reconstruction, quality, provenance."""

from __future__ import annotations

import numpy as np
import pytest

from app.make_model.image.generation import GenerationEngine, ResolutionCascade
from app.make_model.image.editing import EditingEngine, EditOperation, IntentBrush
from app.make_model.image.reconstruction import RealityReconstruction, VisualForensics, ImpossibleSceneEngine
from app.make_model.image.quality import QualityGate, QualityMetrics, PhotographicRealismEngine, DetailRecoveryEngine
from app.make_model.image.provenance import ProvenanceSystem, ProvenanceRecord


def test_resolution_cascade():
    cascade = ResolutionCascade()
    stages = cascade.stages_for(1024)
    assert stages[-1]["short_side"] == 1024


def test_generation_engine():
    engine = GenerationEngine()
    result = engine.text_to_image("test", None, None, seed=42, short_side=256)
    assert result.seed == 42
    assert result.resolution == (256, 256)


def test_editing_engine():
    engine = EditingEngine()
    op = engine.create_operation("lighting_change", "scene1", {"key_intensity": 0.8})
    assert op.op_type == "lighting_change"


def test_intent_brush():
    brush = IntentBrush()
    op = EditOperation(operation_id="op1", op_type="test", target="t1", order=0)
    brush.add(op)
    popped = brush.pop()
    assert popped is not None
    assert popped.operation_id == "op1"


def test_reality_reconstruction():
    rec = RealityReconstruction()
    img = np.random.rand(64, 64, 3).astype(np.float32)
    result = rec.reconstruct(img)
    assert result.geometry_confidence >= 0.0


def test_visual_forensics():
    forensics = VisualForensics()
    img = np.random.rand(64, 64, 3).astype(np.float32)
    report = forensics.forensic_report(img)
    assert "lighting" in report
    assert "composition" in report


def test_impossible_scene_engine():
    engine = ImpossibleSceneEngine()
    coherence = engine.validate_coherence(None)
    assert coherence["lighting_coherent"] is True


def test_photographic_realism():
    engine = PhotographicRealismEngine()
    img = np.random.rand(64, 64, 3).astype(np.float32)
    metrics = engine.assess(img)
    assert metrics.overall >= 0.0


def test_detail_recovery():
    engine = DetailRecoveryEngine()
    img = np.random.rand(1, 3, 32, 32).astype(np.float32)
    recovered = engine.recover(img, target_short_side=64)
    assert recovered.shape[2] == 64


def test_quality_gate():
    gate = QualityGate()
    metrics = QualityMetrics(
        realism=0.9, anatomy=0.9, identity_consistency=0.9, object_consistency=0.9,
        material_realism=0.8, lighting=0.8, shadows=0.8, reflections=0.8,
        depth=0.8, perspective=0.8, composition=0.8, text_rendering=0.8,
        detail=0.8, artifacts=0.1, world_consistency=0.9, edit_fidelity=0.9
    )
    result = gate.evaluate(metrics)
    assert result["passed"] is True


def test_provenance_system():
    system = ProvenanceSystem()
    record = ProvenanceRecord(model_version="test", seed=42, prompt="test prompt")
    system.record(record)
    latest = system.latest()
    assert latest is not None
    assert latest.seed == 42
    json_out = system.to_json()
    assert "test" in json_out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
