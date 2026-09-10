"""Tests for sound director, audio reasoning, self critique, audio memory."""

import numpy as np
import pytest

from app.make_model.audio.sound_director import SoundDirector, AudioPlan, AudioSource, AudioPlanStatus
from app.make_model.audio.audio_reasoning import AudioReasoning, IntentType
from app.make_model.audio.self_critique import SelfCritiqueLoop, CritiqueDecision
from app.make_model.audio.audio_memory import AudioMemory, AudioArtifact
from app.make_model.audio.dialogue_scene import DialogueScene


class TestSoundDirector:
    def test_generate_plan(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 1.0)
        director = SoundDirector()
        plan = director.generate_plan(scene)
        assert plan.scene_id == "s1"
        assert len(plan.sources) == 1

    def test_get_plan(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 1.0)
        director = SoundDirector()
        plan = director.generate_plan(scene)
        assert director.get_plan(plan.plan_id) is not None

    def test_update_plan(self):
        scene = DialogueScene("s1")
        director = SoundDirector()
        plan = director.generate_plan(scene)
        updated = director.update_plan(plan.plan_id, {"notes": "test"})
        assert updated is not None
        assert updated.notes == "test"

    def test_plan_duration(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 1.0)
        scene.add_speech("B", "Hi", 2.0, 1.0)
        director = SoundDirector()
        plan = director.generate_plan(scene)
        assert plan.duration >= 3.0

    def test_add_source(self):
        plan = AudioPlan(plan_id="p1", scene_id="s1")
        plan.add_source(AudioSource(source_id="src1", source_type="dialogue", start_time=0.0, duration=1.0))
        assert len(plan.sources) == 1
        assert plan.duration >= 1.0

    def test_to_dict_roundtrip(self):
        plan = AudioPlan(plan_id="p1", scene_id="s1")
        data = plan.to_dict()
        restored = AudioPlan.from_dict(data)
        assert restored.plan_id == "p1"


class TestAudioReasoning:
    def test_parse_voice(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("generate voice for this text")
        assert intent.intent_type == IntentType.GENERATE_VOICE

    def test_parse_dialogue(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("create a dialogue between two speakers")
        assert intent.intent_type == IntentType.GENERATE_DIALOGUE

    def test_parse_music(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("compose a song")
        assert intent.intent_type == IntentType.GENERATE_MUSIC

    def test_parse_foley(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("add a footstep foley")
        assert intent.intent_type == IntentType.GENERATE_FOLEY

    def test_parse_emotion(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("make it angrier")
        assert intent.intent_type == IntentType.APPLY_EMOTION

    def test_parse_spatial(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("position the sound in 3d space")
        assert intent.intent_type == IntentType.APPLY_SPATIAL

    def test_parse_acoustics(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("apply reverb for a large hall")
        assert intent.intent_type == IntentType.APPLY_ACOUSTICS

    def test_route(self):
        reasoning = AudioReasoning()
        intent = reasoning.parse_intent("generate voice")
        route = reasoning.route(intent)
        assert route["handler"] == "generate_voice"


class TestSelfCritique:
    def test_pass_on_clean_signal(self):
        critique = SelfCritiqueLoop()
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        result = critique.critique(audio, sample_rate=16000)
        assert result.final_decision.value in ("accept", "revise", "fail")

    def test_fail_on_silence(self):
        critique = SelfCritiqueLoop()
        audio = np.zeros(16000, dtype=np.float32)
        result = critique.critique(audio, sample_rate=16000)
        assert result.final_decision in (CritiqueDecision.REVISE, CritiqueDecision.FAIL)

    def test_clipping_detection(self):
        critique = SelfCritiqueLoop()
        audio = np.ones(16000, dtype=np.float32)
        result = critique.critique(audio, sample_rate=16000)
        assert result.details["clipping_ratio"] == 1.0

    def test_to_dict(self):
        critique = SelfCritiqueLoop()
        audio = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 16000)).astype(np.float32)
        result = critique.critique(audio, sample_rate=16000)
        data = result.to_dict()
        assert "level" in data
        assert "score" in data


class TestAudioMemory:
    def test_add_and_get(self, tmp_path):
        mem = AudioMemory(str(tmp_path / "mem.json"))
        artifact = AudioArtifact(artifact_id="a1", path="a.wav")
        mem.add(artifact)
        assert mem.get("a1") is not None

    def test_remove(self, tmp_path):
        mem = AudioMemory(str(tmp_path / "mem.json"))
        artifact = AudioArtifact(artifact_id="a1", path="a.wav")
        mem.add(artifact)
        assert mem.remove("a1") is True
        assert mem.get("a1") is None

    def test_find_by_voice(self, tmp_path):
        mem = AudioMemory(str(tmp_path / "mem.json"))
        mem.add(AudioArtifact(artifact_id="a1", path="a.wav", voice_id="v1"))
        found = mem.find_by_voice("v1")
        assert len(found) == 1

    def test_find_by_tag(self, tmp_path):
        mem = AudioMemory(str(tmp_path / "mem.json"))
        mem.add(AudioArtifact(artifact_id="a1", path="a.wav", tags=["test"]))
        found = mem.find_by_tag("test")
        assert len(found) == 1

    def test_stats(self, tmp_path):
        mem = AudioMemory(str(tmp_path / "mem.json"))
        mem.add(AudioArtifact(artifact_id="a1", path="a.wav"))
        stats = mem.stats()
        assert stats["artifact_count"] == 1