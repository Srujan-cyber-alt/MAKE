"""
VoiceGenome dataclass for the flat MAKE Audio V2 module structure.

A voice genome captures the full acoustic fingerprint of a speaker so that
the same ``voice_id`` always produces a recognisably consistent voice.
"""

from __future__ import annotations

import copy as _copy
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VoiceGenome:
    """Acoustic fingerprint of a single speaker voice."""

    voice_id: str
    pitch: float = 220.0
    timbre: Dict[str, float] = field(default_factory=dict)
    resonance: float = 0.5
    formants: Dict[str, float] = field(default_factory=dict)
    breathiness: float = 0.2
    roughness: float = 0.1
    nasality: float = 0.1
    articulation: float = 0.6
    rhythm: float = 1.0
    cadence: float = 1.0
    energy: float = 0.5
    emotional_tendencies: Dict[str, float] = field(default_factory=dict)
    age_representation: float = 0.5

    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "pitch": self.pitch,
            "timbre": dict(self.timbre),
            "resonance": self.resonance,
            "formants": dict(self.formants),
            "breathiness": self.breathiness,
            "roughness": self.roughness,
            "nasality": self.nasality,
            "articulation": self.articulation,
            "rhythm": self.rhythm,
            "cadence": self.cadence,
            "energy": self.energy,
            "emotional_tendencies": dict(self.emotional_tendencies),
            "age_representation": self.age_representation,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceGenome":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    # ------------------------------------------------------------------
    # Identity / hashing
    # ------------------------------------------------------------------
    def canonical_hash(self) -> str:
        """Return a stable SHA-256 hex digest for this genome."""
        payload = self.to_dict()
        # Exclude metadata timestamps; identity is defined by the acoustic fields.
        for key in ("created_at", "updated_at"):
            payload.pop(key, None)
        # Sort keys so dict ordering never changes the hash.
        canonical = repr({k: payload[k] for k in sorted(payload)})
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def copy(self) -> "VoiceGenome":
        return _copy.deepcopy(self)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def similarity(self, other: "VoiceGenome") -> float:
        """Cosine-like similarity over the numeric scalar fields."""
        import numpy as np

        keys = [
            "pitch",
            "resonance",
            "breathiness",
            "roughness",
            "nasality",
            "articulation",
            "rhythm",
            "cadence",
            "energy",
            "age_representation",
        ]
        a = np.array([getattr(self, k, 0.0) for k in keys], dtype=np.float64)
        b = np.array([getattr(other, k, 0.0) for k in keys], dtype=np.float64)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0.0:
            return 0.0
        return float(np.clip(np.dot(a, b) / denom, -1.0, 1.0))

    def update(self, updates: Dict[str, Any]) -> None:
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.updated_at = time.time()