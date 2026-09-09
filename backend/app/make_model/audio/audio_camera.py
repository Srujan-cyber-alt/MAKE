"""
Audio camera abstraction.

Represents the listener / microphone position and orientation in 3D space,
used by the spatial engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.spatial_engine import ListenerPosition


@dataclass
class AudioCamera:
    """Listener/microphone position and orientation."""

    camera_id: str = "default"
    position: ListenerPosition = field(default_factory=ListenerPosition)
    look_at: Optional[Tuple[float, float, float]] = None
    up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    fov: float = 90.0  # degrees, horizontal field of view
    near_clip: float = 0.1
    far_clip: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "position": self.position.to_dict(),
            "look_at": list(self.look_at) if self.look_at else None,
            "up": list(self.up),
            "fov": self.fov,
            "near_clip": self.near_clip,
            "far_clip": self.far_clip,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioCamera":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "position" in filtered and isinstance(filtered["position"], dict):
            filtered["position"] = ListenerPosition(**filtered["position"])
        if "look_at" in filtered and filtered["look_at"] is not None:
            filtered["look_at"] = tuple(filtered["look_at"])
        if "up" in filtered and filtered["up"] is not None:
            filtered["up"] = tuple(filtered["up"])
        return cls(**filtered)

    def forward_vector(self) -> Tuple[float, float, float]:
        if self.look_at is not None:
            dx = self.look_at[0] - self.position.x
            dy = self.look_at[1] - self.position.y
            dz = self.look_at[2] - self.position.z
            norm = (dx * dx + dy * dy + dz * dz) ** 0.5
            if norm > 0:
                return (dx / norm, dy / norm, dz / norm)
        yaw = math.radians(self.position.yaw)
        return (math.cos(yaw), math.sin(yaw), 0.0)

    def visible_sources(self, sources: List[Any], max_distance: float = 50.0) -> List[Any]:
        forward = self.forward_vector()
        visible: List[Any] = []
        for source in sources:
            if getattr(source, "distance", 1.0) > max_distance:
                continue
            az = math.radians(getattr(source, "azimuth", 0.0))
            direction = (math.cos(az), math.sin(az), 0.0)
            dot = sum(a * b for a, b in zip(forward, direction))
            half_fov = math.radians(self.fov) / 2.0
            if dot >= math.cos(half_fov):
                visible.append(source)
        return visible