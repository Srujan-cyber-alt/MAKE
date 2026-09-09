"""
Smooth state-to-state interpolation for emotional transitions.

Supports ``linear``, ``sigmoid``, ``cosine`` and ``cubic`` easing curves.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from app.make_model.audio.continuous_emotion import ContinuousEmotion


LINEAR = "linear"
SIGMOID = "sigmoid"
COSINE = "cosine"
CUBIC = "cubic"

CURVES: Tuple[str, ...] = (LINEAR, SIGMOID, COSINE, CUBIC)


def _ease(t: float, curve: str) -> float:
    t = max(0.0, min(1.0, t))
    if curve == LINEAR:
        return t
    if curve == SIGMOID:
        return 1.0 / (1.0 + math.exp(-12.0 * (t - 0.5)))
    if curve == COSINE:
        return (1.0 - math.cos(t * math.pi)) / 2.0
    if curve == CUBIC:
        return t * t * (3.0 - 2.0 * t)
    return t


@dataclass
class EmotionTransition:
    """Smooth interpolation between two emotional states."""

    from_emotion: ContinuousEmotion
    to_emotion: ContinuousEmotion
    curve: str = LINEAR
    duration: float = 1.0

    def __post_init__(self) -> None:
        if self.curve not in CURVES:
            raise ValueError(f"Unknown curve: {self.curve}. Choose from {CURVES}")
        if self.duration < 0:
            raise ValueError("duration must be non-negative")

    def sample(self, t: float) -> ContinuousEmotion:
        """Sample emotion at time ``t`` within [0, duration]."""
        if self.duration <= 0:
            return self.to_emotion
        ratio = max(0.0, min(1.0, t / self.duration))
        eased = _ease(ratio, self.curve)
        return self.from_emotion.blend(self.to_emotion, weight=eased)

    def sample_curve(self, steps: int = 20) -> list:
        """Return evenly spaced samples across the transition."""
        if steps <= 0:
            return []
        if self.duration <= 0:
            return [self.to_emotion]
        return [self.sample(self.duration * i / (steps - 1)) for i in range(steps)]

    def derivative(self, t: float) -> ContinuousEmotion:
        """Approximate rate of change at time ``t``."""
        eps = 1e-4
        a = self.sample(max(0.0, t - eps))
        b = self.sample(t + eps)
        return ContinuousEmotion(
            valence=b.valence - a.valence,
            arousal=b.arousal - a.arousal,
            dominance=b.dominance - a.dominance,
            tension=b.tension - a.tension,
            warmth=b.warmth - a.warmth,
            confidence=b.confidence - a.confidence,
            urgency=b.urgency - a.urgency,
            sadness=b.sadness - a.sadness,
            anger=b.anger - a.anger,
            fear=b.fear - a.fear,
            joy=b.joy - a.joy,
            calmness=b.calmness - a.calmness,
        )