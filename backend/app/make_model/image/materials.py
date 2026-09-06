"""MAKE Image Engine — Material Lab.

Semantic material editing with physically plausible lighting interaction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class MaterialProperties:
    base_color: Tuple[float, float, float] = (0.8, 0.8, 0.8)
    metallic: float = 0.0
    roughness: float = 0.5
    specular: float = 0.5
    clearcoat: float = 0.0
    clearcoat_roughness: float = 0.0
    transmission: float = 0.0
    ior: float = 1.5
    subsurface: float = 0.0
    subsurface_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    sheen: float = 0.0
    anisotropic: float = 0.0
    tags: List[str] = field(default_factory=lambda: ["default"])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_color": list(self.base_color),
            "metallic": self.metallic,
            "roughness": self.roughness,
            "specular": self.specular,
            "clearcoat": self.clearcoat,
            "clearcoat_roughness": self.clearcoat_roughness,
            "transmission": self.transmission,
            "ior": self.ior,
            "subsurface": self.subsurface,
            "subsurface_color": list(self.subsurface_color),
            "sheen": self.sheen,
            "anisotropic": self.anisotropic,
            "tags": list(self.tags),
        }


class MaterialLab:
    def __init__(self):
        self.presets: Dict[str, MaterialProperties] = {
            "plastic": MaterialProperties(base_color=(0.8, 0.8, 0.8), metallic=0.0, roughness=0.4, specular=0.5, tags=["plastic"]),
            "glass": MaterialProperties(base_color=(0.95, 0.95, 0.95), metallic=0.0, roughness=0.0, transmission=0.9, ior=1.5, tags=["glass"]),
            "metal": MaterialProperties(base_color=(0.8, 0.8, 0.8), metallic=1.0, roughness=0.3, specular=0.8, tags=["metal"]),
            "gold": MaterialProperties(base_color=(1.0, 0.84, 0.0), metallic=1.0, roughness=0.2, specular=0.9, tags=["metal", "gold"]),
            "concrete": MaterialProperties(base_color=(0.6, 0.6, 0.58), metallic=0.0, roughness=0.9, specular=0.1, tags=["concrete"]),
            "marble": MaterialProperties(base_color=(0.95, 0.95, 0.93), metallic=0.0, roughness=0.3, specular=0.4, subsurface=0.2, tags=["stone", "marble"]),
            "dry": MaterialProperties(base_color=(0.7, 0.6, 0.5), metallic=0.0, roughness=0.8, specular=0.1, tags=["dry"]),
            "wet": MaterialProperties(base_color=(0.5, 0.5, 0.55), metallic=0.0, roughness=0.2, specular=0.9, tags=["wet"]),
            "matte": MaterialProperties(base_color=(0.8, 0.8, 0.8), metallic=0.0, roughness=1.0, specular=0.0, tags=["matte"]),
            "glossy": MaterialProperties(base_color=(0.9, 0.9, 0.9), metallic=0.0, roughness=0.1, specular=1.0, tags=["glossy"]),
            "clean": MaterialProperties(base_color=(0.9, 0.9, 0.9), metallic=0.0, roughness=0.3, specular=0.5, tags=["clean"]),
            "weathered": MaterialProperties(base_color=(0.6, 0.55, 0.5), metallic=0.0, roughness=0.8, specular=0.2, tags=["weathered"]),
            "new": MaterialProperties(base_color=(0.95, 0.95, 0.95), metallic=0.0, roughness=0.2, specular=0.6, tags=["new"]),
            "aged": MaterialProperties(base_color=(0.7, 0.65, 0.6), metallic=0.0, roughness=0.7, specular=0.3, tags=["aged"]),
        }

    def get_preset(self, name: str) -> Optional[MaterialProperties]:
        return self.presets.get(name)

    def apply(self, current: MaterialProperties, preset: str) -> MaterialProperties:
        target = self.get_preset(preset)
        if target is None:
            return current
        return MaterialProperties(
            base_color=target.base_color,
            metallic=target.metallic,
            roughness=target.roughness,
            specular=target.specular,
            clearcoat=target.clearcoat,
            clearcoat_roughness=target.clearcoat_roughness,
            transmission=target.transmission,
            ior=target.ior,
            subsurface=target.subsurface,
            subsurface_color=target.subsurface_color,
            sheen=target.sheen,
            anisotropic=target.anisotropic,
            tags=list(target.tags),
        )

    def interpolate(self, a: MaterialProperties, b: MaterialProperties, weight: float = 0.5) -> MaterialProperties:
        return MaterialProperties(
            base_color=tuple((1 - weight) * np.array(a.base_color) + weight * np.array(b.base_color)),
            metallic=(1 - weight) * a.metallic + weight * b.metallic,
            roughness=(1 - weight) * a.roughness + weight * b.roughness,
            specular=(1 - weight) * a.specular + weight * b.specular,
            clearcoat=(1 - weight) * a.clearcoat + weight * b.clearcoat,
            clearcoat_roughness=(1 - weight) * a.clearcoat_roughness + weight * b.clearcoat_roughness,
            transmission=(1 - weight) * a.transmission + weight * b.transmission,
            ior=(1 - weight) * a.ior + weight * b.ior,
            subsurface=(1 - weight) * a.subsurface + weight * b.subsurface,
            subsurface_color=tuple((1 - weight) * np.array(a.subsurface_color) + weight * np.array(b.subsurface_color)),
            sheen=(1 - weight) * a.sheen + weight * b.sheen,
            anisotropic=(1 - weight) * a.anisotropic + weight * b.anisotropic,
            tags=list(set(a.tags + b.tags)),
        )


__all__ = [
    "MaterialProperties",
    "MaterialLab",
]
