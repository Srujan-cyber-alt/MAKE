"""
Acoustic teleportation: move audio between environments.

Simulates how the same source would sound in different spaces (studio,
bathroom, church, warehouse, car, street, forest, underwater, mountain, bedroom)
by applying room-specific reverberation and noise profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class AcousticEnvironment(str, Enum):
    STUDIO = "studio"
    BATHROOM = "bathroom"
    CHURCH = "church"
    WAREHOUSE = "warehouse"
    CAR = "car"
    STREET = "street"
    FOREST = "forest"
    UNDERWATER = "underwater"
    MOUNTAIN = "mountain"
    BEDROOM = "bedroom"


@dataclass
class EnvironmentProfile:
    name: AcousticEnvironment
    rt60: float = 0.3
    absorption: float = 0.5
    reflection: float = 0.4
    background_noise: float = 0.05
    delay_spread: float = 0.02
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "rt60": self.rt60,
            "absorption": self.absorption,
            "reflection": self.reflection,
            "background_noise": self.background_noise,
            "delay_spread": self.delay_spread,
            "description": self.description,
        }


ENVIRONMENT_PROFILES: Dict[AcousticEnvironment, EnvironmentProfile] = {
    AcousticEnvironment.STUDIO: EnvironmentProfile(AcousticEnvironment.STUDIO, rt60=0.1, absorption=0.8, reflection=0.1, background_noise=0.01, description="Treated studio"),
    AcousticEnvironment.BATHROOM: EnvironmentProfile(AcousticEnvironment.BATHROOM, rt60=0.8, absorption=0.3, reflection=0.8, background_noise=0.02, description="Tiled bathroom"),
    AcousticEnvironment.CHURCH: EnvironmentProfile(AcousticEnvironment.CHURCH, rt60=2.5, absorption=0.1, reflection=0.9, background_noise=0.01, description="Large church"),
    AcousticEnvironment.WAREHOUSE: EnvironmentProfile(AcousticEnvironment.WAREHOUSE, rt60=1.5, absorption=0.2, reflection=0.7, background_noise=0.03, description="Empty warehouse"),
    AcousticEnvironment.CAR: EnvironmentProfile(AcousticEnvironment.CAR, rt60=0.15, absorption=0.6, reflection=0.3, background_noise=0.05, description="Car interior"),
    AcousticEnvironment.STREET: EnvironmentProfile(AcousticEnvironment.STREET, rt60=0.2, absorption=0.7, reflection=0.2, background_noise=0.1, description="Outdoor street"),
    AcousticEnvironment.FOREST: EnvironmentProfile(AcousticEnvironment.FOREST, rt60=0.05, absorption=0.9, reflection=0.05, background_noise=0.05, description="Forest"),
    AcousticEnvironment.UNDERWATER: EnvironmentProfile(AcousticEnvironment.UNDERWATER, rt60=0.5, absorption=0.5, reflection=0.3, background_noise=0.1, description="Underwater"),
    AcousticEnvironment.MOUNTAIN: EnvironmentProfile(AcousticEnvironment.MOUNTAIN, rt60=0.1, absorption=0.8, reflection=0.1, background_noise=0.03, description="Mountain"),
    AcousticEnvironment.BEDROOM: EnvironmentProfile(AcousticEnvironment.BEDROOM, rt60=0.4, absorption=0.5, reflection=0.5, background_noise=0.02, description="Bedroom"),
}


class AcousticTeleportation:
    """Move audio between acoustic environments."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def teleport(self, audio: np.ndarray, environment: AcousticEnvironment, intensity: float = 1.0) -> np.ndarray:
        profile = ENVIRONMENT_PROFILES.get(environment, ENVIRONMENT_PROFILES[AcousticEnvironment.STUDIO])
        result = audio.copy().astype(np.float32)
        # Apply reverb.
        result = self._apply_reverb(result, profile.rt60 * intensity)
        # Add background noise.
        if profile.background_noise > 0:
            rng = np.random.RandomState(int(hashlib_hash(environment.value)))
            noise = rng.normal(0, profile.background_noise * intensity, result.shape[0]).astype(np.float32)
            if result.ndim > 1:
                noise = np.broadcast_to(noise[:, None], result.shape).copy()
            result = result + noise
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def _apply_reverb(self, audio: np.ndarray, rt60: float) -> np.ndarray:
        if rt60 <= 0:
            return audio
        sr = self.sample_rate
        delay = max(1, int(sr * 0.02))
        decay = np.exp(-delay / max(rt60, 0.01) / sr)
        reverb = np.zeros_like(audio)
        for d in range(1, 8):
            shifted = np.roll(audio, d * delay)
            reverb += shifted * (decay ** d) * 0.3
        return audio + reverb

    def available_environments(self) -> List[str]:
        return [e.value for e in AcousticEnvironment]

    def get_profile(self, environment: AcousticEnvironment) -> EnvironmentProfile:
        return ENVIRONMENT_PROFILES.get(environment, ENVIRONMENT_PROFILES[AcousticEnvironment.STUDIO])


def hashlib_hash(value: str) -> int:
    import hashlib

    return int(hashlib.sha256(value.encode("utf-8")).hexdigest()[:8], 16)