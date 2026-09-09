"""
Material acoustic properties.

Defines absorption, reflection, roughness, density, and resonance for common
building and environmental materials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Material:
    """Acoustic properties for a single material."""

    material_id: str
    name: str = ""
    absorption: float = 0.3
    reflection: float = 0.5
    roughness: float = 0.3
    density: float = 500.0
    resonance: float = 0.2
    transmission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "absorption": self.absorption,
            "reflection": self.reflection,
            "roughness": self.roughness,
            "density": self.density,
            "resonance": self.resonance,
            "transmission": self.transmission,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Material":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


# Library of common materials.
MATERIAL_LIBRARY: Dict[str, Material] = {
    "wood": Material(material_id="wood", name="Wood", absorption=0.25, reflection=0.6, roughness=0.4, density=650, resonance=0.4),
    "metal": Material(material_id="metal", name="Metal", absorption=0.1, reflection=0.8, roughness=0.2, density=7800, resonance=0.7),
    "glass": Material(material_id="glass", name="Glass", absorption=0.05, reflection=0.9, roughness=0.05, density=2500, resonance=0.3, transmission=0.8),
    "plastic": Material(material_id="plastic", name="Plastic", absorption=0.15, reflection=0.7, roughness=0.3, density=1200, resonance=0.2),
    "stone": Material(material_id="stone", name="Stone", absorption=0.1, reflection=0.7, roughness=0.5, density=2500, resonance=0.3),
    "fabric": Material(material_id="fabric", name="Fabric", absorption=0.7, reflection=0.2, roughness=0.6, density=300, resonance=0.1),
    "water": Material(material_id="water", name="Water", absorption=0.05, reflection=0.5, roughness=0.1, density=1000, resonance=0.6, transmission=0.9),
    "paper": Material(material_id="paper", name="Paper", absorption=0.5, reflection=0.3, roughness=0.5, density=800, resonance=0.1),
    "rubber": Material(material_id="rubber", name="Rubber", absorption=0.8, reflection=0.1, roughness=0.7, density=1100, resonance=0.05),
    "concrete": Material(material_id="concrete", name="Concrete", absorption=0.1, reflection=0.7, roughness=0.6, density=2300, resonance=0.3),
    "leather": Material(material_id="leather", name="Leather", absorption=0.2, reflection=0.6, roughness=0.4, density=900, resonance=0.3),
}


def get_material(material_id: str) -> Material:
    return MATERIAL_LIBRARY.get(material_id, MATERIAL_LIBRARY["fabric"])