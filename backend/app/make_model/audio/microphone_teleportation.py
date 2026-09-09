"""
Microphone teleportation: simulate different microphone characteristics.

Models mic distance, polar pattern, frequency response, and proximity effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class PolarPattern(str, Enum):
    OMNI = "omni"
    CARDIOID = "cardioid"
    HYPERCARDIOID = "hypercardioid"
    FIGURE8 = "figure8"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class MicrophoneDNA:
    """Microphone acoustic characteristics."""

    mic_id: str = "default"
    polar_pattern: PolarPattern = PolarPattern.CARDIOID
    distance: float = 1.0  # metres
    frequency_response: Dict[str, float] = field(default_factory=dict)
    proximity_effect: float = 0.5
    self_noise: float = 0.01
    max_spl: float = 130.0
    sensitivity: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mic_id": self.mic_id,
            "polar_pattern": self.polar_pattern.value,
            "distance": self.distance,
            "frequency_response": dict(self.frequency_response),
            "proximity_effect": self.proximity_effect,
            "self_noise": self.self_noise,
            "max_spl": self.max_spl,
            "sensitivity": self.sensitivity,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MicrophoneDNA":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "polar_pattern" in filtered and not isinstance(filtered["polar_pattern"], PolarPattern):
            filtered["polar_pattern"] = PolarPattern(filtered["polar_pattern"])
        return cls(**filtered)


MIC_LIBRARY: Dict[str, MicrophoneDNA] = {
    "studio_condenser": MicrophoneDNA(mic_id="studio_condenser", polar_pattern=PolarPattern.OMNI, distance=0.3, proximity_effect=0.2, sensitivity=0.9),
    "dynamic_vocal": MicrophoneDNA(mic_id="dynamic_vocal", polar_pattern=PolarPattern.CARDIOID, distance=0.1, proximity_effect=0.8, sensitivity=0.7),
    "ribbon": MicrophoneDNA(mic_id="ribbon", polar_pattern=PolarPattern.FIGURE8, distance=0.4, proximity_effect=0.3, sensitivity=0.6),
    "shotgun": MicrophoneDNA(mic_id="shotgun", polar_pattern=PolarPattern.HYPERCARDIOID, distance=1.0, proximity_effect=0.1, sensitivity=0.8),
    "lavalier": MicrophoneDNA(mic_id="lavalier", polar_pattern=PolarPattern.CARDIOID, distance=0.05, proximity_effect=0.0, sensitivity=0.5),
}


class MicrophoneTeleportation:
    """Simulate different microphone characteristics."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def apply(self, audio: np.ndarray, mic: MicrophoneDNA, source_angle: float = 0.0) -> np.ndarray:
        result = audio.copy().astype(np.float32)
        # Polar pattern attenuation based on angle.
        gain = self._polar_gain(mic.polar_pattern, source_angle)
        result = result * gain
        # Distance attenuation.
        dist_gain = 1.0 / max(0.1, mic.distance)
        result = result * dist_gain
        # Proximity effect boosts low frequencies.
        if mic.proximity_effect > 0:
            result = self._apply_proximity(result, mic.proximity_effect)
        # Add self noise.
        if mic.self_noise > 0:
            rng = np.random.RandomState(int(hashlib_hash(mic.mic_id)))
            noise = rng.normal(0, mic.self_noise, result.shape[0]).astype(np.float32)
            if result.ndim > 1:
                noise = np.broadcast_to(noise[:, None], result.shape).copy()
            result = result + noise
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def _polar_gain(self, pattern: PolarPattern, angle_deg: float) -> float:
        angle = np.deg2rad(angle_deg)
        if pattern == PolarPattern.OMNI:
            return 1.0
        if pattern == PolarPattern.CARDIOID:
            return float(0.5 + 0.5 * np.cos(angle))
        if pattern == PolarPattern.HYPERCARDIOID:
            return float(0.25 + 0.75 * np.cos(angle))
        if pattern == PolarPattern.FIGURE8:
            return float(np.abs(np.cos(angle)))
        return 1.0

    def _apply_proximity(self, audio: np.ndarray, amount: float) -> np.ndarray:
        # Simple low-shelf boost.
        coeff = 0.1 * amount
        result = np.zeros_like(audio)
        prev = 0.0
        for i in range(audio.size):
            result[i] = audio[i] + coeff * (audio[i] - prev) * 0.0 + coeff * prev
            prev = audio[i]
        return result

    def get_mic(self, mic_id: str) -> MicrophoneDNA:
        return MIC_LIBRARY.get(mic_id, MIC_LIBRARY["studio_condenser"])

    def available_mics(self) -> List[str]:
        return list(MIC_LIBRARY.keys())


def hashlib_hash(value: str) -> int:
    import hashlib

    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)