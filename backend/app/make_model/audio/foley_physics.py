"""
Foley physics synthesis.

Models impact, friction, scraping, collision, movement, deformation,
breakage, compression, stretching, and liquid displacement using numpy.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class FoleyEventType(str, Enum):
    IMPACT = "impact"
    FRICTION = "friction"
    SCRAPING = "scraping"
    COLLISION = "collision"
    MOVEMENT = "movement"
    DEFORMATION = "deformation"
    BREAKAGE = "breakage"
    COMPRESSION = "compression"
    STRETCHING = "stretching"
    LIQUID_DISPLACEMENT = "liquid_displacement"


@dataclass
class FoleyEvent:
    event_type: FoleyEventType
    timing: float = 0.0
    duration: float = 0.5
    intensity: float = 0.7
    material_a: str = "wood"
    material_b: Optional[str] = None
    mass: float = 1.0
    velocity: float = 1.0
    seed: Optional[int] = None
    sample_rate: int = 16000
    metadata: Dict[str, Any] = field(default_factory=dict)


class FoleyPhysics:
    """Deterministic foley synthesis using numpy."""

    DEFAULT_SAMPLE_RATE = 16000

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate

    def synthesize(self, event: FoleyEvent) -> np.ndarray:
        sr = event.sample_rate or self.sample_rate
        n_samples = max(1, int(event.duration * sr))
        rng = self._rng(event)
        audio = self._build(event, n_samples, sr, rng)
        return np.clip(audio * event.intensity, -0.99, 0.99).astype(np.float32)

    def generate(self, event_type: FoleyEventType, **kwargs: Any) -> np.ndarray:
        event = FoleyEvent(event_type=event_type, **kwargs)
        return self.synthesize(event)

    def _rng(self, event: FoleyEvent) -> np.random.RandomState:
        if event.seed is not None:
            return np.random.RandomState(event.seed)
        payload = f"{event.event_type.value}:{event.timing}:{event.material_a}:{event.material_b}"
        return np.random.RandomState(int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16))

    def _build(self, event: FoleyEvent, n_samples: int, sr: int, rng: np.random.RandomState) -> np.ndarray:
        t = np.arange(n_samples, dtype=np.float32) / sr
        et = event.event_type
        if et == FoleyEventType.IMPACT:
            env = np.exp(-t * 8.0)
            freq = 200.0 * event.mass + 50.0
            audio = env * np.sin(2 * np.pi * freq * t)
        elif et == FoleyEventType.FRICTION:
            env = np.exp(-t * 2.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = env * noise * 0.5
        elif et == FoleyEventType.SCRAPING:
            env = np.exp(-t * 3.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = env * noise * 0.6
        elif et == FoleyEventType.COLLISION:
            env = np.exp(-t * 10.0)
            freq = 150.0 / max(event.mass, 0.1)
            audio = env * np.sin(2 * np.pi * freq * t)
        elif et == FoleyEventType.MOVEMENT:
            env = np.exp(-t * 4.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = env * noise * 0.4
        elif et == FoleyEventType.DEFORMATION:
            env = np.exp(-t * 5.0)
            freq = 120.0 * event.mass
            audio = env * np.sin(2 * np.pi * freq * t)
        elif et == FoleyEventType.BREAKAGE:
            env = np.exp(-t * 6.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = env * noise * 0.7
        elif et == FoleyEventType.COMPRESSION:
            env = np.exp(-t * 4.0)
            freq = 80.0 * event.mass
            audio = env * np.sin(2 * np.pi * freq * t)
        elif et == FoleyEventType.STRETCHING:
            env = np.exp(-t * 3.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = env * noise * 0.4
        else:  # LIQUID_DISPLACEMENT
            env = np.exp(-t * 3.0)
            freq = 60.0 + 40.0 * np.sin(2 * np.pi * 0.5 * t)
            audio = env * np.sin(2 * np.pi * freq * t)
        return audio

    def available_types(self) -> List[str]:
        return [t.value for t in FoleyEventType]