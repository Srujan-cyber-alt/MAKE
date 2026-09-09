"""
Material interaction acoustics.

Describes the combined acoustic behavior when two materials interact
(e.g. footstep on wood, hand on glass, metal scraping against metal).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class MaterialInteraction:
    """Acoustic behavior for a pair of interacting materials."""

    material_a: str
    material_b: str
    impact_absorption: float = 0.3
    friction_coefficient: float = 0.5
    resonance_transfer: float = 0.4
    roughness_combined: float = 0.4
    damping: float = 0.3
    spectral_shift: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_a": self.material_a,
            "material_b": self.material_b,
            "impact_absorption": self.impact_absorption,
            "friction_coefficient": self.friction_coefficient,
            "resonance_transfer": self.resonance_transfer,
            "roughness_combined": self.roughness_combined,
            "damping": self.damping,
            "spectral_shift": self.spectral_shift,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MaterialInteraction":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    @classmethod
    def from_materials(cls, a: str, b: str) -> "MaterialInteraction":
        """Build an interaction from a material library."""
        from app.make_model.audio.material import get_material

        ma = get_material(a)
        mb = get_material(b)
        return cls(
            material_a=a,
            material_b=b,
            impact_absorption=(ma.absorption + mb.absorption) / 2.0,
            friction_coefficient=(ma.roughness + mb.roughness) / 2.0,
            resonance_transfer=(ma.resonance + mb.resonance) / 2.0,
            roughness_combined=(ma.roughness + mb.roughness) / 2.0,
            damping=(ma.density + mb.density) / 2.0 / 10000.0,
            spectral_shift=(mb.resonance - ma.resonance) * 0.5,
        )