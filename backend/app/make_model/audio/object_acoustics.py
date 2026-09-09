"""
Object acoustics: impact, resonance, decay.

Describes how a physical object radiates sound when excited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class ObjectAcoustics:
    """Acoustic fingerprint of a physical object."""

    object_id: str
    material_id: str = "wood"
    impact_strength: float = 0.5
    resonance: float = 0.4
    decay: float = 0.6
    mass: float = 1.0
    stiffness: float = 0.5
    damping: float = 0.3
    spectral_profile: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def dominant_frequency(self) -> float:
        # Heuristic mapping from stiffness/mass.
        return 200.0 * (self.stiffness + 0.1) / (self.mass + 0.1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "material_id": self.material_id,
            "impact_strength": self.impact_strength,
            "resonance": self.resonance,
            "decay": self.decay,
            "mass": self.mass,
            "stiffness": self.stiffness,
            "damping": self.damping,
            "spectral_profile": dict(self.spectral_profile),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ObjectAcoustics":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def impact_response(self, force: float = 1.0) -> Dict[str, float]:
        """Return parameters describing an impact on this object."""
        amp = self.impact_strength * max(0.0, force)
        return {
            "amplitude": amp,
            "frequency": self.dominant_frequency,
            "decay_time": self.decay,
            "resonance": self.resonance,
        }