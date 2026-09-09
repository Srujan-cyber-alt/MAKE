"""Tests for speaker consistency, continuity, prosody, performance, and spatial."""

import pytest
import numpy as np
from app.make_model.audio.config_loader import load_audio_config
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder
from app.make_model.audio.continuity import AudioContinuityMemory
from app.make_model.audio.spatial import SpatialAudioDirector
from app.make_model.audio.performance import PerformanceDirector
from app.make_model.audio.prosody import ProsodyDirector


class TestSpeakerConsistency:
    def test_same_speaker_same_output(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        out1 = model.forward("consistent test", "speaker_A", "neutral")
        out2 = model.forward("consistent test", "speaker_A", "neutral")
        assert np.allclose(out1, out2)

    def test_different_speakers_different_outputs(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        out1 = model.forward("test", "speaker_A", "neutral")
        out2 = model.forward("test", "speaker_B", "neutral")
        assert not np.allclose(out1, out2)

    def test_speaker_persists_across_emotions(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        model = TinyAudioModel(config, seed=42)
        base = model.forward("hello", "speaker_X", "neutral")
        happy = model.forward("hello", "speaker_X", "happy")
        sad = model.forward("hello", "speaker_X", "sad")
        corr_happy = float(np.corrcoef(base, happy)[0, 1])
        corr_sad = float(np.corrcoef(base, sad)[0, 1])
        assert corr_happy > 0.5
        assert corr_sad > 0.5


class TestContinuity:
    def test_scene_memory(self):
        memory = AudioContinuityMemory("/tmp/test_audio_continuity.json")
        memory.record_scene("scene_1", {"ambience": "forest", "room": "outdoor"})
        scene = memory.get_scene("scene_1")
        assert scene is not None
        assert scene["audio_state"]["ambience"] == "forest"

    def test_environment_change(self):
        memory = AudioContinuityMemory("/tmp/test_audio_continuity2.json")
        memory.record_scene("scene_1", {"ambience": "forest"})
        memory.record_scene("scene_2", {"ambience": "city"})
        s1 = memory.get_scene("scene_1")
        s2 = memory.get_scene("scene_2")
        assert s1["audio_state"]["ambience"] == "forest"
        assert s2["audio_state"]["ambience"] == "city"


class TestProsody:
    def test_prosody_director_init(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = ProsodyDirector()
        assert director is not None

    def test_prosody_parameters(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = ProsodyDirector()
        params = director.generate_prosody("hello world", speaking_rate=1.2)
        assert params is not None


class TestPerformance:
    def test_performance_director_init(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = PerformanceDirector()
        assert director is not None

    def test_performance_provenance(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = PerformanceDirector()
        prov = director.get_provenance()
        assert prov["model_type"] == "performance"


class TestSpatial:
    def test_spatial_director_init(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = SpatialAudioDirector()
        assert director is not None

    def test_spatial_provenance(self):
        config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")
        director = SpatialAudioDirector()
        prov = director.get_provenance()
        assert prov["model_type"] == "spatial"
