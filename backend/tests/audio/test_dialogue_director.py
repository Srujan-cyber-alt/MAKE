"""Tests for Dialogue Director."""
import numpy as np
import pytest
from app.make_model.audio.dialogue_director import (
    DialogueDirector, SpeakerState, SceneContext,
    DialogueTurn, SpeakingReason, RelationshipType, ReactionType,
)


class TestDialogueDirector:
    def test_director_creation(self):
        director = DialogueDirector()
        assert len(director.speakers) == 0

    def test_add_speaker(self):
        director = DialogueDirector()
        director.add_speaker("alice", {"bob": RelationshipType.FRIENDLY})
        assert "alice" in director.speakers
        assert director.speakers["alice"].speaker_id == "alice"

    def test_set_scene(self):
        director = DialogueDirector()
        scene = SceneContext(setting="office", topic="budget", tension=0.3, formality=0.5, time_of_day="afternoon", location="conference_room")
        director.set_scene(scene)
        assert director.scene_context == scene
        assert director.scene_context.topic == "budget"

    def test_determine_first_speaker(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.add_speaker("bob")
        speaker = director.determine_speaker(None)
        assert speaker is not None

    def test_turn_taking(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.add_speaker("bob")
        turn1 = director.generate_turn("Hello.", speaker_override="alice")
        assert turn1.speaker == "alice"
        turn2 = director.generate_turn("Hi there.", speaker_override="bob")
        assert turn2.speaker == "bob"
        assert turn2.reaction_to == "alice"

    def test_reason_determination(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        speaker = director.determine_speaker(None)
        assert speaker == "alice"
        reason = director.determine_reason(speaker, None)
        assert reason == SpeakingReason.BREAK_SILENCE

    def test_reaction_determination(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.add_speaker("bob", {"alice": RelationshipType.ANTAGONISTIC})
        director.speakers["bob"].tension_with["alice"] = 0.8
        reaction = director.determine_reaction("bob", "alice")
        assert reaction == ReactionType.CHALLENGE

    def test_timing(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        pause_before, pause_after, rate = director.determine_timing("alice", None)
        assert pause_before > 0
        assert pause_after > 0
        assert rate > 0

    def test_interruption_detection(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.speakers["alice"].current_emotion["urgency"] = 0.9
        director.set_scene(SceneContext("office", "topic", 0.8, 0.5, "day", "room"))
        assert director.determine_interruption("alice") is True

        director.speakers["alice"].current_emotion["urgency"] = 0.3
        assert director.determine_interruption("alice") is False

    def test_speaker_memory(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.generate_turn("Statement 1.", speaker_override="alice")
        director.generate_turn("Statement 2.", speaker_override="alice")
        assert director.speakers["alice"].statement_count >= 2
        assert len(director.speakers["alice"].dialogue_history) >= 2

    def test_emotional_drift(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        state = director.speakers["alice"]
        for i in range(5):
            state.emotional_memory.append({"happiness": 0.1 * i, "sadness": 0.1, "anger": 0.1, "fear": 0.1,
                                            "surprise": 0.1, "disgust": 0.05, "calm": 0.6, "excitement": 0.3,
                                            "confidence": 0.5, "tension": 0.3, "intimacy": 0.2, "urgency": 0.2})
        drift = state.emotional_drift()
        assert drift > 0

    def test_emotional_conflict(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        state = director.speakers["alice"]
        state.emotional_memory = [
            {"happiness": 0.9, "sadness": 0.1, "anger": 0.1, "fear": 0.1,
             "surprise": 0.1, "disgust": 0.05, "calm": 0.6, "excitement": 0.3,
             "confidence": 0.5, "tension": 0.3, "intimacy": 0.2, "urgency": 0.2},
            {"happiness": 0.1, "sadness": 0.9, "anger": 0.1, "fear": 0.1,
             "surprise": 0.1, "disgust": 0.05, "calm": 0.6, "excitement": 0.3,
             "confidence": 0.5, "tension": 0.3, "intimacy": 0.2, "urgency": 0.2},
            {"happiness": 0.9, "sadness": 0.1, "anger": 0.8, "fear": 0.1,
             "surprise": 0.1, "disgust": 0.05, "calm": 0.6, "excitement": 0.3,
             "confidence": 0.5, "tension": 0.3, "intimacy": 0.2, "urgency": 0.2},
        ]
        assert state.detect_emotional_conflict() is True

    def test_conversational_tension(self):
        director = DialogueDirector()
        director.add_speaker("alice", {"bob": RelationshipType.ANTAGONISTIC})
        director.add_speaker("bob", {"alice": RelationshipType.ANTAGONISTIC})
        director.speakers["alice"].tension_with["bob"] = 0.8
        tension = director.get_conversational_tension()
        assert tension > 0

    def test_scene_continuity(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.add_speaker("bob")
        director.generate_turn("Hello", speaker_override="alice")
        director.generate_turn("Hi", speaker_override="bob")
        continuity = director.get_scene_continuity()
        assert continuity["total_turns"] == 2
        assert "alice" in continuity["speakers_active"]
        assert "bob" in continuity["speakers_active"]

    def test_export_dialogue(self):
        director = DialogueDirector()
        director.add_speaker("alice")
        director.add_speaker("bob")
        director.generate_turn("Hello", speaker_override="alice")
        director.generate_turn("Hi", speaker_override="bob")
        exported = director.export_dialogue()
        assert "turns" in exported
        assert len(exported["turns"]) == 2
        assert exported["turns"][0]["speaker"] == "alice"
        assert exported["turns"][1]["speaker"] == "bob"
        assert "continuity" in exported

    def test_multi_speaker_scene(self):
        director = DialogueDirector()
        for name in ["alice", "bob", "charlie"]:
            director.add_speaker(name)
        director.generate_turn("First.", speaker_override="alice")
        director.generate_turn("Second.", speaker_override="bob")
        director.generate_turn("Third.", speaker_override="charlie")
        assert len(director.turn_history) == 3
        assert {t.speaker for t in director.turn_history} == {"alice", "bob", "charlie"}
