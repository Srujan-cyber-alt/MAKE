"""
Room acoustic model.

Captures size, materials, RT60, absorption, and reflection for a space.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Room:
    """Acoustic description of a room."""

    room_id: str
    size: str = "medium"  # small | medium | large | huge
    materials: Dict[str, float] = field(default_factory=dict)
    absorption: float = 0.3
    reflection: float = 0.5
    rt60: float = 0.4
    width: float = 5.0
    length: float = 6.0
    height: float = 3.0
    occupancy: float = 0.5
    volume: float = 0.0
    surface_area: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.volume:
            self.volume = self.width * self.length * self.height
        if not self.surface_area:
            self.surface_area = 2.0 * (self.width * self.length + self.width * self.height + self.length * self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "size": self.size,
            "materials": dict(self.materials),
            "absorption": self.absorption,
            "reflection": self.reflection,
            "rt60": self.rt60,
            "width": self.width,
            "length": self.length,
            "height": self.height,
            "occupancy": self.occupancy,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Room":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def estimate_rt60(self) -> float:
        """Sabine-style RT60 estimate based on volume and absorption."""
        if self.absorption <= 0:
            return 0.0
        return 0.161 * self.volume / (self.absorption * self.surface_area)