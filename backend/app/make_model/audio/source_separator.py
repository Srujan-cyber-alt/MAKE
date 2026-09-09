"""
Source separation approach documentation.

This module documents the separation strategy used by the audio pipeline.
It is intentionally lightweight (no heavy ML dependencies) and exposes a
small numpy-based fallback estimator so callers can introspect the design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SeparationMethod(str, Enum):
    SPECTRAL_SUBTRACTION = "spectral_subtraction"
    NMFD = "nmfd"
    BEAMFORMING = "beamforming"
    DEEP_LEARNING = "deep_learning"


@dataclass
class SeparationPlan:
    """Describes how a separation task should be executed."""

    method: SeparationMethod = SeparationMethod.SPECTRAL_SUBTRACTION
    num_sources: int = 2
    source_names: List[str] = field(default_factory=list)
    expected_snr_db: float = 10.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "num_sources": self.num_sources,
            "source_names": list(self.source_names),
            "expected_snr_db": self.expected_snr_db,
            "notes": self.notes,
        }


class SourceSeparator:
    """Stub documenting the separation approach with a numpy fallback."""

    SUPPORTED_METHODS = [m.value for m in SeparationMethod]

    def __init__(self, method: SeparationMethod = SeparationMethod.SPECTRAL_SUBTRACTION) -> None:
        self.method = method
        self.plan: Optional[SeparationPlan] = None

    def plan_separation(self, num_sources: int, source_names: Optional[List[str]] = None) -> SeparationPlan:
        self.plan = SeparationPlan(
            method=self.method,
            num_sources=num_sources,
            source_names=source_names or [f"source_{i}" for i in range(num_sources)],
            notes=self._method_notes(),
        )
        return self.plan

    def _method_notes(self) -> str:
        if self.method == SeparationMethod.SPECTRAL_SUBTRACTION:
            return "Estimate noise profile and subtract in STFT domain."
        if self.method == SeparationMethod.NMFD:
            return "Non-negative matrix factorisation with sparsity priors."
        if self.method == SeparationMethod.BEAMFORMING:
            return "Multi-channel beamforming with null-steering."
        return "Deep learning based mask estimation."

    def separate(self, audio: np.ndarray, num_sources: int = 2) -> List[np.ndarray]:
        """Fallback separation: split energy across ``num_sources`` channels."""
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        n = audio.shape[0]
        # Simple spectral split by frequency bands.
        sources: List[np.ndarray] = []
        for i in range(num_sources):
            band = np.zeros_like(audio)
            low = int(i * n / num_sources)
            high = int((i + 1) * n / num_sources)
            band[low:high] = audio[low:high]
            sources.append(band.squeeze())
        return sources

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "supported_methods": list(self.SUPPORTED_METHODS),
            "plan": self.plan.to_dict() if self.plan else None,
        }