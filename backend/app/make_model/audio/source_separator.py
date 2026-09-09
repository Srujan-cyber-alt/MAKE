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
import scipy.signal as signal


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
        """
        DSP-based source separation using frequency-band splitting.

        This is NOT neural separation. It splits the input into frequency bands:
        - Source 0: low frequencies (vocals/bass range)
        - Source 1: mid frequencies (speech range)
        - Source 2+: high frequencies (sibilants/ambience)
        """
        if audio.ndim == 1:
            audio = audio.reshape(-1, 1)
        n = audio.shape[0]
        sr = self.plan.expected_snr_db if self.plan and self.plan.num_sources else 16000
        n_fft = min(2048, max(256, n))
        hop = n_fft // 4
        f, t, S = signal.stft(audio[:, 0], nperseg=n_fft, noverlap=n_fft - hop)
        nyquist = f[-1] if len(f) > 0 else n_fft / 2
        boundaries = np.linspace(0, nyquist, num_sources + 1)
        sources: List[np.ndarray] = []
        for i in range(num_sources):
            mask = np.zeros_like(S, dtype=bool)
            for j in range(len(f)):
                if boundaries[i] <= f[j] <= boundaries[i + 1]:
                    mask[j, :] = True
            S_band = S * mask
            _, band = signal.istft(S_band, nperseg=n_fft, noverlap=n_fft - hop)
            band = band[:n] if len(band) > n else np.pad(band, (0, n - len(band)))
            sources.append(band)
        return sources if sources else [audio.squeeze()]

    def separate_to_files(
        self, audio_path: str, output_dir: str, num_sources: int = 2
    ) -> Dict[str, str]:
        """Separate a WAV file into individual source files."""
        import os
        from pathlib import Path
        import scipy.io.wavfile as wavfile
        sr, data = wavfile.read(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        else:
            audio = data.astype(np.float32)
        sources = self.separate(audio, num_sources)
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        result: Dict[str, str] = {}
        base = Path(audio_path).stem
        for i, src in enumerate(sources):
            src_int = (np.clip(src, -0.99, 0.99) * 32767).astype(np.int16)
            out_path = os.path.join(output_dir, f"{base}_source_{i}.wav")
            wavfile.write(out_path, sr, src_int)
            result[f"source_{i}"] = out_path
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "supported_methods": list(self.SUPPORTED_METHODS),
            "plan": self.plan.to_dict() if self.plan else None,
        }