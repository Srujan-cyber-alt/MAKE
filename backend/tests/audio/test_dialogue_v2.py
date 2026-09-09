"""Tests for dialogue scene, speaker state, conversation memory, reaction engine."""

import time

import numpy as np
import pytest

from app.make_model.audio.dialogue_scene import (
    DialogueScene,
    DialogueTurn,
    InterruptionMarker,
    TurnType,
)
from app.make_model.audio.continuous_emotion import ContinuousEmotion
from app.make_model.audio.speaker_state import (
    SpeakerState,
    PersonalityProfile,
    SpeakingStyle,
)
from app.make_model.audio.conversation_memory import ConversationMemory, ConversationTurn
from app.make_model.audio.reaction_engine import (
    ReactionEngine,
    ReactionSpec,
    ReactionType,
)


class TestDialogueScene:
    def test_add_speech(self):
        scene = DialogueScene("s1")
        turn = scene.add_speech("Alice", "Hello", start_time=0.0, duration=1.0)
        assert scene.turn_count == 1
        assert turn.speaker_id == "Alice"
        assert "Alice" in scene.speakers

    def test_interruption_marker(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 1.0)
        scene.add_interruption(0.5, "B", "A")
        assert len(scene.interruptions) == 1
        assert scene.interruptions[0].interrupter == "B"

    def test_overlaps_at(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 2.0)
        scene.add_speech("B", "Hi", 1.0, 1.0)
        overlaps = scene.overlaps_at(1.5)
        assert len(overlaps) == 2

    def test_remove_turn(self):
        scene = DialogueScene("s1")
        turn = scene.add_speech("A", "Hello", 0.0, 1.0)
        assert scene.remove_turn(turn.turn_id) is True
        assert scene.turn_count == 0

    def test_to_dict_roundtrip(self):
        scene = DialogueScene("s1")
        scene.add_speech("A", "Hello", 0.0, 1.0, emotion=ContinuousEmotion(valence=0.8))
        data = scene.to_dict()
        restored = DialogueScene.from_dict(data)
        assert restored.scene_id == "s1"
        assert restored.turn_count == 1


class TestSpeakerState:
    def test_register_and_emotion(self):
        speaker = SpeakerState("spk_1")
        speaker.set_emotion(ContinuousEmotion(valence=0.9))
        assert speaker.emotional_state.valence == 0.9

    def test_remember_and_recall(self):
        speaker = SpeakerState("spk_1")
        speaker.remember({"text": "hello"})
        recalled = speaker.recall(limit=1)
        assert len(recalled) == 1
        assert recalled[0]["text"] == "hello"

    def test_to_dict_roundtrip(self):
        speaker = SpeakerState("spk_1")
        speaker.set_emotion(ContinuousEmotion(valence=0.7))
        data = speaker.to_dict()
        restored = SpeakerState.from_dict(data)
        assert restored.speaker_id == "spk_1"
        assert restored.emotional_state.valence == 0.7

    def test_conditioning(self):
        speaker = SpeakerState("spk_1")
        cond = speaker.get_conditioning()
        assert cond["speaker_id"] == "spk_1"
        assert "audio_parameters" in cond


class TestConversationMemory:
    def test_add_speech(self):
        mem = ConversationMemory("c1")
        mem.add_speech("A", "Hello")
        mem.add_speech("B", "Hi there")
        assert mem.turn_count == 2
        assert set(mem.speakers) == {"A", "B"}

    def test_relationships(self):
        mem = ConversationMemory("c1")
        mem.add_speech("A", "Hello")
        mem.add_speech("B", "Hi")
        rels = mem.get_relationships()
        assert "A" in rels and "B" in rels["A"]

    def test_reference_resolution(self):
        mem = ConversationMemory("c1")
        t1 = mem.add_speech("A", "Hello")
        t2 = mem.add_speech("B", "Hi", referenced_turn_ids=[t1.turn_id])
        refs = mem.resolve_reference(t2.turn_id, depth=1)
        assert any(t.turn_id == t1.turn_id for t in refs)

    def test_to_dict_roundtrip(self):
        mem = ConversationMemory("c1")
        mem.add_speech("A", "Hello")
        data = mem.to_dict()
        restored = ConversationMemory.from_dict(data)
        assert restored.turn_count == 1


class TestReactionEngine:
    def test_synthesize_breath(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.BREATH, duration=0.2)
        assert audio.size > 0
        assert np.max(np.abs(audio)) <= 1.0

    def test_synthesize_laugh(self):
        engine = ReactionEngine(sample_rate=16000)
        audio = engine.generate(ReactionType.LAUGH, duration=0.5)
        assert audio.size > 0

    def test_all_types(self):
        engine = ReactionEngine()
        types = engine.available_types()
        for t in types:
            audio = engine.generate(ReactionType(t), duration=0.1)
            assert audio.size > 0

    def test_deterministic_with_seed(self):
        engine = ReactionEngine(sample_rate=16000)
        a1 = engine.generate(ReactionType.SIGH, duration=0.3, seed=42)
        a2 = engine.generate(ReactionType.SIGH, duration=0.3, seed=42)
        assert np.allclose(a1, a2)

    def test_spec_object(self):
        engine = ReactionEngine(sample_rate=16000)
        spec = ReactionSpec(reaction_type=ReactionType.GASP, duration=0.2, intensity=0.8, seed=1)
        audio = engine.synthesize(spec)
        assert audio.size > 0