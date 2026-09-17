"""
Semantic label mappings for neural audio conditioning.

Provides bidirectional mappings between human-readable labels and numeric IDs
used by the neural model encoders (SpeakerEncoder, EmotionEncoder, StyleEncoder).
"""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass


# Emotion labels (32 slots available in model)
EMOTION_LABELS: Dict[str, int] = {
    "neutral": 0,
    "happy": 1,
    "sad": 2,
    "angry": 3,
    "fearful": 4,
    "disgusted": 5,
    "surprised": 6,
    "calm": 7,
    "excited": 8,
    "confident": 9,
    "hesitant": 10,
    "sarcastic": 11,
    "urgent": 12,
    "exhausted": 13,
    "intimate": 14,
    "dramatic": 15,
    "whisper": 16,
    "shout": 17,
    "bored": 18,
    "curious": 19,
    "amused": 20,
    "concerned": 21,
    "hopeful": 22,
    "nostalgic": 23,
    "determined": 24,
    "gentle": 25,
    "stern": 26,
    "playful": 27,
    "serious": 28,
    "tender": 29,
    "melancholic": 30,
    "euphoric": 31,
}

EMOTION_ID_TO_LABEL: Dict[int, str] = {v: k for k, v in EMOTION_LABELS.items()}


# Style/Acting labels (16 slots available in model)
STYLE_LABELS: Dict[str, int] = {
    "neutral": 0,
    "whisper": 1,
    "shout": 2,
    "hesitant": 3,
    "sarcastic": 4,
    "urgent": 5,
    "confident": 6,
    "fearful": 7,
    "exhausted": 8,
    "excited": 9,
    "calm": 10,
    "intimate": 11,
    "dramatic": 12,
    "storytelling": 13,
    "news_anchor": 14,
    "conversational": 15,
}

STYLE_ID_TO_LABEL: Dict[int, str] = {v: k for k, v in STYLE_LABELS.items()}


# Speaker labels (1000 slots available - predefine common ones)
SPEAKER_LABELS: Dict[str, int] = {
    "default": 0,
    "narrator": 1,
    "female_1": 2,
    "male_1": 3,
    "child": 4,
    "elderly": 5,
    "professional": 6,
    "casual": 7,
    "authoritative": 8,
    "warm": 9,
    "cool": 10,
    "energetic": 11,
    "soothing": 12,
    "deep": 13,
    "bright": 14,
    "radio_host": 15,
    "podcast_host": 16,
    "audiobook_narrator": 17,
    "character_1": 18,
    "character_2": 19,
    "character_3": 20,
    "character_4": 21,
    "character_5": 22,
    "character_6": 23,
    "character_7": 24,
    "character_8": 25,
    "character_9": 26,
    "character_10": 27,
}

SPEAKER_ID_TO_LABEL: Dict[int, str] = {v: k for k, v in SPEAKER_LABELS.items()}


@dataclass
class SemanticConditioning:
    """Semantic conditioning parameters for neural generation."""
    speaker: Optional[str] = None
    emotion: Optional[str] = None
    style: Optional[str] = None
    pitch_hz: Optional[float] = None
    energy_db: Optional[float] = None
    
    def to_ids(
        self,
        default_speaker: int = 0,
        default_emotion: int = 0,
        default_style: int = 0,
        default_pitch: float = 120.0,
        default_energy: float = -20.0,
    ) -> Dict[str, any]:
        """Convert semantic labels to numeric IDs."""
        return {
            "speaker_id": SPEAKER_LABELS.get(self.speaker, default_speaker) if self.speaker else default_speaker,
            "emotion_id": EMOTION_LABELS.get(self.emotion, default_emotion) if self.emotion else default_emotion,
            "style_id": STYLE_LABELS.get(self.style, default_style) if self.style else default_style,
            "pitch_hz": self.pitch_hz if self.pitch_hz is not None else default_pitch,
            "energy_db": self.energy_db if self.energy_db is not None else default_energy,
        }


def get_emotion_label(emotion_id: int) -> str:
    """Get emotion label from ID."""
    return EMOTION_ID_TO_LABEL.get(emotion_id, f"unknown_{emotion_id}")


def get_style_label(style_id: int) -> str:
    """Get style label from ID."""
    return STYLE_ID_TO_LABEL.get(style_id, f"unknown_{style_id}")


def get_speaker_label(speaker_id: int) -> str:
    """Get speaker label from ID."""
    return SPEAKER_ID_TO_LABEL.get(speaker_id, f"speaker_{speaker_id}")


def get_emotion_id(emotion_label: str) -> Optional[int]:
    """Get emotion ID from label."""
    return EMOTION_LABELS.get(emotion_label.lower())


def get_style_id(style_label: str) -> Optional[int]:
    """Get style ID from label."""
    return STYLE_LABELS.get(style_label.lower())


def get_speaker_id(speaker_label: str) -> Optional[int]:
    """Get speaker ID from label."""
    return SPEAKER_LABELS.get(speaker_label.lower())


def list_emotions() -> List[str]:
    """List all available emotion labels."""
    return list(EMOTION_LABELS.keys())


def list_styles() -> List[str]:
    """List all available style labels."""
    return list(STYLE_LABELS.keys())


def list_speakers() -> List[str]:
    """List all available speaker labels."""
    return list(SPEAKER_LABELS.keys())


def validate_emotion(emotion: str) -> bool:
    """Validate emotion label."""
    return emotion.lower() in EMOTION_LABELS


def validate_style(style: str) -> bool:
    """Validate style label."""
    return style.lower() in STYLE_LABELS


def validate_speaker(speaker: str) -> bool:
    """Validate speaker label."""
    return speaker.lower() in SPEAKER_LABELS