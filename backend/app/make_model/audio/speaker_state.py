"""
Speaker state: identity, personality, emotional state, speaking style, memory.

Combines a voice genome with a persistent personality profile and the
speaker's current emotional and stylistic state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.make_model.audio.continuous_emotion import ContinuousEmotion
from app.make_model.audio.voice_genome import VoiceGenome


@dataclass
class PersonalityProfile:
    """Big-Five-ish personality traits in [0, 1]."""

    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def to_dict(self) -> Dict[str, float]:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "PersonalityProfile":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: float(v) for k, v in data.items() if k in known})


@dataclass
class SpeakingStyle:
    """Stylistic preferences for how a speaker talks."""

    base_rate: float = 1.0
    pitch_variance: float = 0.5
    volume: float = 0.7
    formality: float = 0.5
    humor: float = 0.3
    interruption_tendency: float = 0.2
    pause_frequency: float = 0.4

    def to_dict(self) -> Dict[str, float]:
        return {
            "base_rate": self.base_rate,
            "pitch_variance": self.pitch_variance,
            "volume": self.volume,
            "formality": self.formality,
            "humor": self.humor,
            "interruption_tendency": self.interruption_tendency,
            "pause_frequency": self.pause_frequency,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "SpeakingStyle":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: float(v) for k, v in data.items() if k in known})


class SpeakerState:
    """Identity, personality, emotional state, speaking style, conversation memory."""

    def __init__(
        self,
        speaker_id: str,
        voice_genome: Optional[VoiceGenome] = None,
        personality: Optional[PersonalityProfile] = None,
        speaking_style: Optional[SpeakingStyle] = None,
    ) -> None:
        self.speaker_id = speaker_id
        self.voice_genome = voice_genome or VoiceGenome(voice_id=speaker_id)
        self.personality = personality or PersonalityProfile()
        self.speaking_style = speaking_style or SpeakingStyle()
        self.emotional_state = ContinuousEmotion.neutral()
        self.memory: List[Dict[str, Any]] = []
        self.created_at = time.time()
        self.last_active = time.time()

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------
    def set_emotion(self, emotion: ContinuousEmotion) -> None:
        self.emotional_state = emotion
        self.last_active = time.time()

    def update_personality(self, updates: Dict[str, float]) -> None:
        for key, value in updates.items():
            if hasattr(self.personality, key):
                setattr(self.personality, key, float(value))

    def update_style(self, updates: Dict[str, float]) -> None:
        for key, value in updates.items():
            if hasattr(self.speaking_style, key):
                setattr(self.speaking_style, key, float(value))

    def remember(self, event: Dict[str, Any]) -> None:
        entry = dict(event)
        entry.setdefault("timestamp", time.time())
        self.memory.append(entry)
        self.last_active = time.time()

    def recall(self, limit: int = 10) -> List[Dict[str, Any]]:
        return list(self.memory[-limit:])

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "voice_genome": self.voice_genome.to_dict(),
            "personality": self.personality.to_dict(),
            "speaking_style": self.speaking_style.to_dict(),
            "emotional_state": self.emotional_state.to_dict(),
            "memory": list(self.memory),
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpeakerState":
        speaker = cls(
            speaker_id=data["speaker_id"],
            voice_genome=VoiceGenome.from_dict(data.get("voice_genome", {"voice_id": data["speaker_id"]})),
            personality=PersonalityProfile.from_dict(data.get("personality", {})),
            speaking_style=SpeakingStyle.from_dict(data.get("speaking_style", {})),
        )
        speaker.emotional_state = ContinuousEmotion.from_dict(data.get("emotional_state", {}))
        speaker.memory = list(data.get("memory", []))
        speaker.created_at = data.get("created_at", time.time())
        speaker.last_active = data.get("last_active", time.time())
        return speaker

    def get_conditioning(self) -> Dict[str, Any]:
        """Return conditioning parameters derived from current state."""
        audio_params = self.emotional_state.to_audio_parameters()
        return {
            "speaker_id": self.speaker_id,
            "voice_id": self.voice_genome.voice_id,
            "personality": self.personality.to_dict(),
            "speaking_style": self.speaking_style.to_dict(),
            "emotion": self.emotional_state.to_dict(),
            "audio_parameters": audio_params,
        }