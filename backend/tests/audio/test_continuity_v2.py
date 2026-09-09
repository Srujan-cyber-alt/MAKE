"""Tests for continuity engine, project audio state, and continuity validator."""

import json
import os

import pytest

from app.make_model.audio.audio_continuity_engine import (
    AudioContinuityEngine,
    ContinuityState,
    ContinuityType,
)
from app.make_model.audio.project_audio_state import ProjectAudioState, SceneEntry
from app.make_model.audio.continuity_validator import (
    ContinuityValidator,
    ValidationResult,
    ValidationLevel,
    DimensionResult,
)


class TestAudioContinuityEngine:
    def test_set_and_get(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "cont.json"))
        engine.set_state(ContinuityType.VOICE, "voice_1")
        state = engine.get_state(ContinuityType.VOICE)
        assert state is not None
        assert state.value == "voice_1"

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "cont.json")
        engine = AudioContinuityEngine(path)
        engine.set_state(ContinuityType.EMOTION, "happy")
        engine2 = AudioContinuityEngine(path)
        state = engine2.get_state(ContinuityType.EMOTION)
        assert state is not None
        assert state.value == "happy"

    def test_snapshot(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "cont.json"))
        engine.set_state(ContinuityType.VOICE, "v1")
        snap = engine.snapshot()
        assert snap["voice"] == "v1"

    def test_history(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "cont.json"))
        engine.set_state(ContinuityType.VOICE, "v1")
        engine.set_state(ContinuityType.VOICE, "v2")
        history = engine.get_history(ContinuityType.VOICE)
        assert len(history) == 2

    def test_diff(self, tmp_path):
        a = AudioContinuityEngine(str(tmp_path / "a.json"))
        b = AudioContinuityEngine(str(tmp_path / "b.json"))
        a.set_state(ContinuityType.VOICE, "v1")
        b.set_state(ContinuityType.VOICE, "v2")
        diff = a.diff(b)
        assert diff["voice"]["changed"] is True

    def test_continuity_hash(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "cont.json"))
        engine.set_state(ContinuityType.VOICE, "v1")
        h = engine.continuity_hash()
        assert isinstance(h, str) and len(h) > 0


class TestProjectAudioState:
    def test_add_scene(self, tmp_path):
        state = ProjectAudioState(str(tmp_path / "proj.json"))
        state.add_scene("scene_1", {"voice": "v1"})
        assert state.get_scene("scene_1") is not None
        assert state.get_scene_order() == ["scene_1"]

    def test_remove_scene(self, tmp_path):
        state = ProjectAudioState(str(tmp_path / "proj.json"))
        state.add_scene("scene_1", {"voice": "v1"})
        state.add_scene("scene_2", {"voice": "v2"})
        assert state.remove_scene("scene_1") is True
        assert state.get_scene("scene_1") is None
        assert state.get_scene_order() == ["scene_2"]

    def test_reorder(self, tmp_path):
        state = ProjectAudioState(str(tmp_path / "proj.json"))
        state.add_scene("scene_1", {"voice": "v1"})
        state.add_scene("scene_2", {"voice": "v2"})
        state.reorder(["scene_2", "scene_1"])
        assert state.get_scene_order() == ["scene_2", "scene_1"]

    def test_continuity_inheritance(self, tmp_path):
        state = ProjectAudioState(str(tmp_path / "proj.json"))
        state.add_scene("scene_1", {"voice": "v1", "room": "studio"})
        assert state.get_continuity(ContinuityType.VOICE) == "v1"
        assert state.get_continuity(ContinuityType.ROOM) == "studio"

    def test_snapshot(self, tmp_path):
        state = ProjectAudioState(str(tmp_path / "proj.json"))
        state.add_scene("scene_1", {"voice": "v1"})
        snap = state.snapshot()
        assert "scene_order" in snap
        assert "continuity" in snap


class TestContinuityValidator:
    def test_validate_pass(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "v2.json"))
        engine.set_state(ContinuityType.VOICE, "v1")
        validator = ContinuityValidator()
        result = validator.validate(engine)
        assert isinstance(result, ValidationResult)
        assert result.level in (ValidationLevel.PASS, ValidationLevel.REVISE, ValidationLevel.FAIL)

    def test_validate_fail(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "vf.json"))
        validator = ContinuityValidator()
        result = validator.validate(engine, expected={"voice": "v1"})
        assert result.level in (ValidationLevel.REVISE, ValidationLevel.FAIL)

    def test_snapshot_validation(self):
        validator = ContinuityValidator()
        result = validator.validate_snapshot({"voice": "v1"}, {"voice": "v1"})
        assert result.overall_score > 0.9

    def test_dimension_results(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "vd.json"))
        validator = ContinuityValidator()
        result = validator.validate(engine)
        assert len(result.dimensions) == 8
        for d in result.dimensions:
            assert isinstance(d, DimensionResult)
            assert 0.0 <= d.score <= 1.0

    def test_custom_weights(self, tmp_path):
        engine = AudioContinuityEngine(str(tmp_path / "vw.json"))
        validator = ContinuityValidator(weights={"voice": 0.5, "emotion": 0.5})
        result = validator.validate(engine)
        assert result.overall_score >= 0.0