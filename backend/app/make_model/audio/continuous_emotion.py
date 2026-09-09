"""
Continuous emotion representation with 12 dimensions.

Each dimension lives in [0, 1].  The dataclass supports blending, distance
computation, dominant-dimension extraction, intensity scaling, and conversion
to audio parameters (pitch shift, energy, speaking rate, breathiness).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


EMOTION_DIMENSIONS: Tuple[str, ...] = (
    "valence",
    "arousal",
    "dominance",
    "tension",
    "warmth",
    "confidence",
    "urgency",
    "sadness",
    "anger",
    "fear",
    "joy",
    "calmness",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass
class ContinuousEmotion:
    """12-dimensional continuous emotion vector."""

    valence: float = 0.5
    arousal: float = 0.5
    dominance: float = 0.5
    tension: float = 0.5
    warmth: float = 0.5
    confidence: float = 0.5
    urgency: float = 0.5
    sadness: float = 0.5
    anger: float = 0.5
    fear: float = 0.5
    joy: float = 0.5
    calmness: float = 0.5

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def neutral(cls) -> "ContinuousEmotion":
        return cls()

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "ContinuousEmotion":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: _clamp(float(v)) for k, v in data.items() if k in known})

    @classmethod
    def from_named(cls, name: str, intensity: float = 1.0) -> "ContinuousEmotion":
        presets = {
            "neutral": {},
            "happy": {"joy": 0.9, "valence": 0.8, "arousal": 0.6},
            "sad": {"sadness": 0.9, "valence": 0.2, "calmness": 0.4},
            "angry": {"anger": 0.9, "tension": 0.8, "arousal": 0.8},
            "fearful": {"fear": 0.9, "tension": 0.7, "arousal": 0.8},
            "calm": {"calmness": 0.9, "arousal": 0.2, "valence": 0.6},
            "excited": {"arousal": 0.9, "joy": 0.7, "urgency": 0.6},
            "tense": {"tension": 0.9, "fear": 0.4, "arousal": 0.6},
            "confident": {"confidence": 0.9, "dominance": 0.7},
            "surprised": {"arousal": 0.8, "tension": 0.4, "valence": 0.5},
        }
        base = presets.get(name.lower(), {})
        obj = cls.neutral()
        for k, v in base.items():
            setattr(obj, k, _clamp(v * intensity))
        return obj

    # ------------------------------------------------------------------
    # Vector operations
    # ------------------------------------------------------------------
    def to_list(self) -> List[float]:
        return [getattr(self, d) for d in EMOTION_DIMENSIONS]

    def to_dict(self) -> Dict[str, float]:
        return {d: getattr(self, d) for d in EMOTION_DIMENSIONS}

    def as_array(self):
        import numpy as np

        return np.array(self.to_list(), dtype=np.float32)

    def blend(self, other: "ContinuousEmotion", weight: float = 0.5) -> "ContinuousEmotion":
        w = _clamp(weight)
        result = ContinuousEmotion()
        for d in EMOTION_DIMENSIONS:
            a = getattr(self, d)
            b = getattr(other, d)
            setattr(result, d, _clamp(a * (1.0 - w) + b * w))
        return result

    def scale(self, intensity: float) -> "ContinuousEmotion":
        """Scale towards the neutral point (0.5) by ``intensity``."""
        result = ContinuousEmotion()
        for d in EMOTION_DIMENSIONS:
            val = getattr(self, d)
            setattr(result, d, _clamp(val + (0.5 - val) * (1.0 - _clamp(intensity))))
        return result

    def distance(self, other: "ContinuousEmotion") -> float:
        import numpy as np

        a = self.as_array()
        b = other.as_array()
        return float(np.linalg.norm(a - b))

    def cosine_similarity(self, other: "ContinuousEmotion") -> float:
        import numpy as np

        a = self.as_array()
        b = other.as_array()
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0.0:
            return 0.0
        return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def dominant_dimension(self) -> str:
        best_dim = EMOTION_DIMENSIONS[0]
        best_val = -1.0
        for d in EMOTION_DIMENSIONS:
            val = getattr(self, d)
            # Distance from neutral (0.5) is what makes a dimension "dominant".
            dev = abs(val - 0.5)
            if dev > best_val:
                best_val = dev
                best_dim = d
        return best_dim

    def intensity(self) -> float:
        """Maximum absolute deviation from neutral, scaled to [0, 1]."""
        import numpy as np

        arr = self.as_array()
        return float(np.max(np.abs(arr - 0.5)) * 2.0)

    # ------------------------------------------------------------------
    # Audio parameter conversion
    # ------------------------------------------------------------------
    def to_audio_parameters(self) -> Dict[str, float]:
        """Map emotional dimensions to audio synthesis parameters."""
        valence = self.valence
        arousal = self.arousal
        return {
            "pitch_shift_semitones": (valence - 0.5) * 4.0 + (arousal - 0.5) * 2.0,
            "energy": _clamp(0.3 + arousal * 0.7),
            "speaking_rate": _clamp(0.7 + arousal * 0.6),
            "breathiness": _clamp(self.breathiness_proxy()),
            "tension": self.tension,
            "warmth": self.warmth,
            "confidence": self.confidence,
            "urgency": self.urgency,
        }

    def breathiness_proxy(self) -> float:
        """Higher arousal + lower dominance => more breathiness."""
        return _clamp(0.5 * self.arousal + 0.3 * (1.0 - self.dominance) + 0.1)

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        dom = self.dominant_dimension()
        return f"ContinuousEmotion(dominant={dom}, intensity={self.intensity():.2f})"