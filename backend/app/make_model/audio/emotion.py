"""MAKE Audio — Emotion Engine.

Maps structured emotional states to voice-parameter adjustments so that
emotion genuinely affects the synthesized signal, not just metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class EmotionType(str, Enum):
    HAPPINESS = "happiness"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    CALM = "calm"
    EXCITEMENT = "excitement"
    TENSION = "tension"
    CONFIDENCE = "confidence"
    INTIMACY = "intimacy"
    EXHAUSTION = "exhaustion"
    SURPRISE = "surprise"
    NEUTRAL = "neutral"


_DEFAULT_EMOTIONS = {
    e.value: 0.0 for e in EmotionType
}


@dataclass
class EmotionEngine:
    """Tracks and blends emotional states.

    Intensity values are floats in [0, 1] for each emotion.
    """

    emotions: Dict[str, float] = field(default_factory=lambda: dict(_DEFAULT_EMOTIONS))
    max_active: int = 3

    def set(self, emotion: str, intensity: float) -> None:
        emotion = emotion.lower()
        if emotion not in self.emotions:
            self.emotions[emotion] = 0.0
        self.emotions[emotion] = max(0.0, min(1.0, intensity))

    def blend(self, emotions: Dict[str, float]) -> None:
        for name, intensity in emotions.items():
            self.set(name, intensity)

    def get(self, emotion: str) -> float:
        return self.emotions.get(emotion.lower(), 0.0)

    def get_state(self) -> Dict[str, float]:
        return dict(self.emotions)

    def to_voice_adjustments(self) -> Dict[str, Any]:
        """Convert emotional state to voice-parameter deltas."""
        h = self.emotions.get("happiness", 0)
        s = self.emotions.get("sadness", 0)
        a = self.emotions.get("anger", 0)
        f = self.emotions.get("fear", 0)
        c = self.emotions.get("calm", 0)
        ex = self.emotions.get("excitement", 0)
        t = self.emotions.get("tension", 0)
        con = self.emotions.get("confidence", 0)
        inti = self.emotions.get("intimacy", 0)
        e = self.emotions.get("exhaustion", 0)
        surp = self.emotions.get("surprise", 0)

        return {
            "pitch_shift": (h + ex + f + surp) * 15 - s * 25 - e * 15,
            "brightness": (h + ex - s - e) * 0.3,
            "breathiness": (f + inti) * 0.4 + (h + ex) * 0.2,
            "roughness": a * 0.5 + t * 0.3,
            "warmth": (s + c) * 0.3 - a * 0.2,
            "speaking_rate": 1.0 + (ex + h) * 0.3 - (s + c) * 0.15 - e * 0.2,
            "volume_scale": 1.0 + (a + ex) * 0.2 - (f + inti) * 0.3,
            "formant_shift": (h * 0.05) - (s + e) * 0.08,
            "tenseness": (a + t + f) * 0.4,
            "monotone": (s + e + c) * 0.3,
            "tremor_depth": (e + f) * 0.15,
            "tremor_rate": 4.0 + (f * 3.0),
        }

    def validate(self) -> bool:
        """Check that emotion intensities sum to <= 1.0 (no over-saturation)."""
        active = sum(v for v in self.emotions.values() if v > 0)
        return active <= 1.0 + 1e-6

    def reset(self) -> None:
        for k in self.emotions:
            self.emotions[k] = 0.0
        self.emotions["neutral"] = 1.0

    def describe(self) -> str:
        active = {k: round(v, 3) for k, v in self.emotions.items() if v > 0.01}
        return f"EmotionEngine({active})"
