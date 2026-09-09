"""
Non-verbal reaction synthesis.

Generates short audio events (breath, hesitation, laugh, sigh, gasp, surprise,
throat clearing, quiet acknowledgment) using deterministic numpy synthesis.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ReactionType(str, Enum):
    BREATH = "breath"
    HESITATION = "hesitation"
    LAUGH = "laugh"
    SIGH = "sigh"
    GASP = "gasp"
    SURPRISE = "surprise"
    THROAT_CLEARING = "throat_clearing"
    QUIET_ACKNOWLEDGMENT = "quiet_acknowledgment"


@dataclass
class ReactionSpec:
    reaction_type: ReactionType
    duration: float = 0.5
    intensity: float = 0.7
    seed: Optional[int] = None
    sample_rate: int = 16000
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReactionEngine:
    """Generate non-verbal reactions with numpy audio synthesis."""

    DEFAULT_SAMPLE_RATE = 16000

    def __init__(self, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._templates: Dict[ReactionType, Dict[str, Any]] = {
            ReactionType.BREATH: {"base_freq": 0.5, "amp": 0.3},
            ReactionType.HESITATION: {"base_freq": 0.4, "amp": 0.2},
            ReactionType.LAUGH: {"base_freq": 0.6, "amp": 0.4},
            ReactionType.SIGH: {"base_freq": 0.3, "amp": 0.35},
            ReactionType.GASP: {"base_freq": 0.7, "amp": 0.45},
            ReactionType.SURPRISE: {"base_freq": 0.65, "amp": 0.4},
            ReactionType.THROAT_CLEARING: {"base_freq": 0.35, "amp": 0.3},
            ReactionType.QUIET_ACKNOWLEDGMENT: {"base_freq": 0.25, "amp": 0.15},
        }

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------
    def synthesize(self, spec: ReactionSpec) -> np.ndarray:
        if spec.reaction_type not in self._templates:
            raise ValueError(f"Unknown reaction type: {spec.reaction_type}")
        template = self._templates[spec.reaction_type]
        sr = spec.sample_rate or self.sample_rate
        n_samples = max(1, int(spec.duration * sr))
        rng = self._rng(spec.reaction_type, spec.seed)
        audio = self._build_audio(spec.reaction_type, template, n_samples, sr, spec.intensity, rng)
        return np.clip(audio, -0.99, 0.99).astype(np.float32)

    def generate(self, reaction_type: ReactionType, duration: float = 0.5, intensity: float = 0.7, seed: Optional[int] = None) -> np.ndarray:
        spec = ReactionSpec(reaction_type=reaction_type, duration=duration, intensity=intensity, seed=seed)
        return self.synthesize(spec)

    def _rng(self, reaction_type: ReactionType, seed: Optional[int]) -> np.random.RandomState:
        if seed is not None:
            return np.random.RandomState(seed)
        payload = reaction_type.value
        return np.random.RandomState(int(hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8], 16))

    def _build_audio(
        self,
        reaction_type: ReactionType,
        template: Dict[str, Any],
        n_samples: int,
        sr: int,
        intensity: float,
        rng: np.random.RandomState,
    ) -> np.ndarray:
        t = np.arange(n_samples, dtype=np.float32) / sr
        amp = template["amp"] * max(0.0, min(1.5, intensity))
        if reaction_type == ReactionType.BREATH:
            env = np.exp(-t * 3.0)
            audio = amp * env * (0.5 + 0.5 * np.sin(2 * np.pi * template["base_freq"] * t))
        elif reaction_type == ReactionType.HESITATION:
            env = np.exp(-t * 2.0)
            audio = amp * env * (0.3 + 0.7 * np.sin(2 * np.pi * template["base_freq"] * t))
        elif reaction_type == ReactionType.LAUGH:
            # Bursty amplitude modulation.
            bursts = np.zeros(n_samples, dtype=np.float32)
            burst_len = max(1, n_samples // 6)
            for i in range(6):
                start = i * burst_len
                end = min(n_samples, start + burst_len)
                if start >= n_samples:
                    break
                env = np.exp(-np.arange(end - start, dtype=np.float32) * 6.0)
                bursts[start:end] = env
            audio = amp * bursts * (0.5 + 0.5 * np.sin(2 * np.pi * 6.0 * t))
        elif reaction_type == ReactionType.SIGH:
            env = np.exp(-t * 1.5)
            audio = amp * env * (0.4 + 0.6 * np.sin(2 * np.pi * template["base_freq"] * t))
        elif reaction_type in (ReactionType.GASP, ReactionType.SURPRISE):
            env = np.exp(-t * 4.0)
            audio = amp * env * (0.6 + 0.4 * np.sin(2 * np.pi * template["base_freq"] * t))
        elif reaction_type == ReactionType.THROAT_CLEARING:
            env = np.exp(-t * 3.0)
            noise = rng.normal(0, 1, n_samples).astype(np.float32)
            audio = amp * env * noise * 0.5
        else:  # QUIET_ACKNOWLEDGMENT
            env = np.exp(-t * 5.0)
            audio = amp * env * (0.3 + 0.7 * np.sin(2 * np.pi * template["base_freq"] * t))
        return audio

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------
    def generate_batch(self, reactions: List[ReactionSpec]) -> List[np.ndarray]:
        return [self.synthesize(r) for r in reactions]

    def available_types(self) -> List[str]:
        return [t.value for t in self._templates]