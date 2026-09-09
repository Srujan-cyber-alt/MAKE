"""
3D audio spatial engine.

Handles azimuth, elevation, distance, and occlusion for positioning sources
around a listener.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SpatialModel(str, Enum):
    STEREO = "stereo"
    BINAURAL = "binaural"
    SURROUND = "surround"
    AMBISONIC = "ambisonic"


@dataclass
class SpatialSource:
    source_id: str
    azimuth: float = 0.0  # degrees, 0 = front
    elevation: float = 0.0  # degrees, 0 = horizon
    distance: float = 1.0  # metres
    occlusion: float = 0.0  # 0 = no obstruction, 1 = fully blocked
    gain: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "azimuth": self.azimuth,
            "elevation": self.elevation,
            "distance": self.distance,
            "occlusion": self.occlusion,
            "gain": self.gain,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpatialSource":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class ListenerPosition:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    yaw: float = 0.0  # degrees, facing direction
    pitch: float = 0.0
    roll: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "z": self.z, "yaw": self.yaw, "pitch": self.pitch, "roll": self.roll}


class SpatialEngine:
    """3D audio with azimuth, elevation, distance, occlusion."""

    def __init__(self, model: SpatialModel = SpatialModel.BINAURAL, sample_rate: int = 16000) -> None:
        self.model = model
        self.sample_rate = sample_rate

    def spatialize(self, audio: np.ndarray, source: SpatialSource) -> np.ndarray:
        """Apply HRTF-like panning to a mono source."""
        if audio.size == 0:
            return audio
        mono = audio
        if audio.ndim > 1:
            mono = audio.mean(axis=1)
        mono = mono.astype(np.float32)
        left, right = self._pan(mono, source)
        stereo = np.stack([left, right], axis=-1)
        return np.clip(stereo, -0.99, 0.99).astype(np.float32)

    def _pan(self, audio: np.ndarray, source: SpatialSource) -> Tuple[np.ndarray, np.ndarray]:
        az = math.radians(source.azimuth)
        el = math.radians(source.elevation)
        # Distance attenuation.
        dist_gain = 1.0 / max(0.1, source.distance)
        # Occlusion low-pass.
        occlusion = max(0.0, min(1.0, source.occlusion))
        # Simple pan law.
        left_gain = math.cos(az) * dist_gain * (1.0 - occlusion * 0.5) * source.gain
        right_gain = math.sin(az) * dist_gain * (1.0 - occlusion * 0.5) * source.gain
        # Elevation attenuates slightly.
        el_factor = math.cos(el)
        left_gain *= el_factor
        right_gain *= el_factor
        left = audio * left_gain
        right = audio * right_gain
        return left, right

    def create_scene(self, sources: List[SpatialSource], listener: ListenerPosition, audio_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """Mix multiple spatial sources into a stereo render."""
        max_len = max((a.size for a in audio_dict.values()), default=0)
        if max_len == 0:
            return np.zeros((0, 2), dtype=np.float32)
        scene = np.zeros((max_len, 2), dtype=np.float32)
        for source in sources:
            audio = audio_dict.get(source.source_id)
            if audio is None:
                continue
            spatial = self.spatialize(audio, source)
            if spatial.ndim == 1:
                spatial = np.stack([spatial, spatial], axis=-1)
            if spatial.shape[0] < scene.shape[0]:
                padded = np.zeros((scene.shape[0], spatial.shape[1]), dtype=np.float32)
                padded[: spatial.shape[0]] = spatial
                spatial = padded
            scene += spatial[: scene.shape[0]]
        return np.clip(scene, -0.99, 0.99).astype(np.float32)

    def available_models(self) -> List[str]:
        return [m.value for m in SpatialModel]