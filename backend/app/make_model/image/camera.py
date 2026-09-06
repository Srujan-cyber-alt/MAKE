"""MAKE Image Engine — Cinema Camera Engine.

Explicit cinematic camera controls with teleportation support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class CameraParameters:
    position: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    focal_length: float = 50.0
    aperture: float = 2.8
    focus_distance: float = 1.0
    sensor_width: float = 36.0
    sensor_height: float = 24.0
    is_anamorphic: bool = False
    shutter_angle: float = 180.0
    frame_rate: float = 24.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "rotation": list(self.rotation),
            "focal_length": self.focal_length,
            "aperture": self.aperture,
            "focus_distance": self.focus_distance,
            "sensor_width": self.sensor_width,
            "sensor_height": self.sensor_height,
            "is_anamorphic": self.is_anamorphic,
            "shutter_angle": self.shutter_angle,
            "frame_rate": self.frame_rate,
        }


@dataclass
class CameraPath:
    keyframes: List[Dict[str, Any]] = field(default_factory=list)

    def add_keyframe(self, time: float, params: CameraParameters) -> None:
        self.keyframes.append({"time": time, **params.to_dict()})

    def interpolate(self, time: float) -> Optional[CameraParameters]:
        if not self.keyframes:
            return None
        kf = self.keyframes[0]
        return CameraParameters(
            position=tuple(kf["position"]),
            rotation=tuple(kf["rotation"]),
            focal_length=kf["focal_length"],
            aperture=kf["aperture"],
            focus_distance=kf["focus_distance"],
            sensor_width=kf["sensor_width"],
            sensor_height=kf["sensor_height"],
            is_anamorphic=kf["is_anamorphic"],
            shutter_angle=kf["shutter_angle"],
            frame_rate=kf["frame_rate"],
        )


class CinemaCameraEngine:
    def __init__(self):
        self.presets: Dict[str, CameraParameters] = {
            "front": CameraParameters(position=(0.0, 0.0, 1.0), rotation=(0.0, 0.0, 0.0), focal_length=50.0),
            "rear": CameraParameters(position=(0.0, 0.0, -1.0), rotation=(0.0, 180.0, 0.0), focal_length=50.0),
            "left": CameraParameters(position=(-1.0, 0.0, 0.0), rotation=(0.0, 90.0, 0.0), focal_length=50.0),
            "right": CameraParameters(position=(1.0, 0.0, 0.0), rotation=(0.0, -90.0, 0.0), focal_length=50.0),
            "overhead": CameraParameters(position=(0.0, 1.5, 0.0), rotation=(-90.0, 0.0, 0.0), focal_length=35.0),
            "low_angle": CameraParameters(position=(0.0, -0.8, 0.5), rotation=(45.0, 0.0, 0.0), focal_length=35.0),
            "close_up": CameraParameters(position=(0.0, 0.0, 0.3), rotation=(0.0, 0.0, 0.0), focal_length=85.0),
            "wide": CameraParameters(position=(0.0, 0.0, 2.5), rotation=(0.0, 0.0, 0.0), focal_length=24.0),
            "macro": CameraParameters(position=(0.0, 0.0, 0.1), rotation=(0.0, 0.0, 0.0), focal_length=100.0),
            "portrait": CameraParameters(position=(0.0, 0.0, 1.2), rotation=(0.0, 0.0, 0.0), focal_length=85.0),
            "tracking": CameraParameters(position=(0.5, 0.0, 0.5), rotation=(0.0, -30.0, 0.0), focal_length=35.0),
            "cinematic": CameraParameters(position=(0.3, -0.2, 1.0), rotation=(5.0, -15.0, 0.0), focal_length=50.0, aperture=2.0),
        }

    def get_preset(self, name: str) -> Optional[CameraParameters]:
        return self.presets.get(name)

    def apply(self, current: CameraParameters, preset: str) -> CameraParameters:
        target = self.get_preset(preset)
        if target is None:
            return current
        return CameraParameters(
            position=target.position,
            rotation=target.rotation,
            focal_length=target.focal_length,
            aperture=target.aperture,
            focus_distance=target.focus_distance,
            sensor_width=target.sensor_width,
            sensor_height=target.sensor_height,
            is_anamorphic=target.is_anamorphic,
            shutter_angle=target.shutter_angle,
            frame_rate=target.frame_rate,
        )

    def create_path(self, keyframes: List[Dict[str, Any]]) -> CameraPath:
        path = CameraPath()
        for kf in keyframes:
            params = CameraParameters(
                position=tuple(kf.get("position", (0.0, 0.0, 1.0))),
                rotation=tuple(kf.get("rotation", (0.0, 0.0, 0.0))),
                focal_length=kf.get("focal_length", 50.0),
                aperture=kf.get("aperture", 2.8),
                focus_distance=kf.get("focus_distance", 1.0),
                sensor_width=kf.get("sensor_width", 36.0),
                sensor_height=kf.get("sensor_height", 24.0),
                is_anamorphic=kf.get("is_anamorphic", False),
                shutter_angle=kf.get("shutter_angle", 180.0),
                frame_rate=kf.get("frame_rate", 24.0),
            )
            path.add_keyframe(kf.get("time", 0.0), params)
        return path


__all__ = [
    "CameraParameters",
    "CameraPath",
    "CinemaCameraEngine",
]
