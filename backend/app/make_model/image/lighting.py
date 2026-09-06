"""MAKE Image Engine — Lighting Director.

Semantic lighting control without destroying geometry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np


@dataclass
class LightSetup:
    light_type: str = "natural"
    key_direction: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    key_intensity: float = 1.0
    key_color: Tuple[float, float, float] = (1.0, 0.95, 0.9)
    fill_intensity: float = 0.3
    fill_color: Tuple[float, float, float] = (0.9, 0.95, 1.0)
    rim_intensity: float = 0.0
    rim_color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    ambient: float = 0.2
    volumetric: bool = False
    cast_shadows: bool = True
    exposure: float = 0.0
    contrast: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_type": self.light_type,
            "key_direction": list(self.key_direction),
            "key_intensity": self.key_intensity,
            "key_color": list(self.key_color),
            "fill_intensity": self.fill_intensity,
            "fill_color": list(self.fill_color),
            "rim_intensity": self.rim_intensity,
            "rim_color": list(self.rim_color),
            "ambient": self.ambient,
            "volumetric": self.volumetric,
            "cast_shadows": self.cast_shadows,
            "exposure": self.exposure,
            "contrast": self.contrast,
        }


class LightingDirector:
    def __init__(self):
        self.presets: Dict[str, LightSetup] = {
            "sunlight": LightSetup(light_type="sunlight", key_direction=(0.0, 1.0, 0.0), key_intensity=1.0, key_color=(1.0, 0.95, 0.9), fill_intensity=0.3, fill_color=(0.9, 0.95, 1.0), ambient=0.2),
            "moonlight": LightSetup(light_type="moonlight", key_direction=(-1.0, 0.2, -0.5), key_intensity=0.2, key_color=(0.6, 0.7, 1.0), fill_intensity=0.1, fill_color=(0.5, 0.6, 0.8), ambient=0.1),
            "studio": LightSetup(light_type="studio", key_direction=(0.0, 1.0, 0.5), key_intensity=0.8, key_color=(1.0, 1.0, 1.0), fill_intensity=0.4, fill_color=(0.95, 0.95, 1.0), rim_intensity=0.3, rim_color=(1.0, 1.0, 1.0), ambient=0.15),
            "dramatic": LightSetup(light_type="dramatic", key_direction=(0.0, 1.0, 0.0), key_intensity=1.2, key_color=(1.0, 0.9, 0.8), fill_intensity=0.1, fill_color=(0.8, 0.85, 0.9), rim_intensity=0.5, rim_color=(1.0, 0.95, 0.9), ambient=0.05),
            "soft": LightSetup(light_type="soft", key_direction=(0.0, 1.0, 0.2), key_intensity=0.7, key_color=(1.0, 0.98, 0.95), fill_intensity=0.5, fill_color=(0.95, 0.98, 1.0), ambient=0.3),
            "hard": LightSetup(light_type="hard", key_direction=(0.0, 1.0, 0.0), key_intensity=1.5, key_color=(1.0, 1.0, 1.0), fill_intensity=0.05, fill_color=(0.9, 0.9, 0.9), rim_intensity=0.0, ambient=0.1),
            "overcast": LightSetup(light_type="overcast", key_direction=(0.0, 1.0, 0.0), key_intensity=0.6, key_color=(0.85, 0.88, 0.92), fill_intensity=0.4, fill_color=(0.8, 0.85, 0.9), ambient=0.4),
            "natural": LightSetup(light_type="natural", key_direction=(0.0, 1.0, 0.0), key_intensity=1.0, key_color=(1.0, 0.95, 0.9), fill_intensity=0.3, fill_color=(0.9, 0.95, 1.0), ambient=0.2),
            "volumetric": LightSetup(light_type="volumetric", key_direction=(0.0, 1.0, 0.0), key_intensity=0.8, key_color=(1.0, 0.95, 0.85), fill_intensity=0.2, fill_color=(0.9, 0.9, 0.85), volumetric=True, ambient=0.25),
            "sunset": LightSetup(light_type="sunlight", key_direction=(-1.0, 0.1, 0.5), key_intensity=0.9, key_color=(1.0, 0.4, 0.2), fill_intensity=0.2, fill_color=(0.9, 0.8, 0.7), ambient=0.25),
        }

    def get_preset(self, name: str) -> Optional[LightSetup]:
        return self.presets.get(name)

    def apply(self, current: LightSetup, preset: str) -> LightSetup:
        target = self.get_preset(preset)
        if target is None:
            return current
        return LightSetup(
            light_type=target.light_type,
            key_direction=target.key_direction,
            key_intensity=target.key_intensity,
            key_color=target.key_color,
            fill_intensity=target.fill_intensity,
            fill_color=target.fill_color,
            rim_intensity=target.rim_intensity,
            rim_color=target.rim_color,
            ambient=target.ambient,
            volumetric=target.volumetric,
            cast_shadows=target.cast_shadows,
            exposure=target.exposure,
            contrast=target.contrast,
        )

    def blend(self, a: LightSetup, b: LightSetup, weight: float = 0.5) -> LightSetup:
        return LightSetup(
            light_type=a.light_type,
            key_direction=tuple((1 - weight) * np.array(a.key_direction) + weight * np.array(b.key_direction)),
            key_intensity=float((1 - weight) * a.key_intensity + weight * b.key_intensity),
            key_color=tuple((1 - weight) * np.array(a.key_color) + weight * np.array(b.key_color)),
            fill_intensity=float((1 - weight) * a.fill_intensity + weight * b.fill_intensity),
            fill_color=tuple((1 - weight) * np.array(a.fill_color) + weight * np.array(b.fill_color)),
            rim_intensity=float((1 - weight) * a.rim_intensity + weight * b.rim_intensity),
            rim_color=tuple((1 - weight) * np.array(a.rim_color) + weight * np.array(b.rim_color)),
            ambient=float((1 - weight) * a.ambient + weight * b.ambient),
            volumetric=a.volumetric or b.volumetric,
            cast_shadows=a.cast_shadows and b.cast_shadows,
            exposure=float((1 - weight) * a.exposure + weight * b.exposure),
            contrast=float((1 - weight) * a.contrast + weight * b.contrast),
        )


__all__ = [
    "LightSetup",
    "LightingDirector",
]
