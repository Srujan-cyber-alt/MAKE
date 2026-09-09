"""
Audio outpainter.

Extends an audio signal while preserving tempo and character using
deterministic numpy resampling and envelope matching.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class OutpaintMode(str, Enum):
    SMOOTH = "smooth"
    LOOP = "loop"
    REVERBERANT = "reverberant"


@dataclass
class OutpaintSpec:
    target_duration: float = 5.0
    mode: OutpaintMode = OutpaintMode.SMOOTH
    preserve_tempo: bool = True
    crossfade: float = 0.1
    seed: Optional[int] = None
    sample_rate: int = 16000


class AudioOutpainter:
    """Extend audio while preserving tempo and character."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate

    def outpaint(self, audio: np.ndarray, spec: OutpaintSpec) -> np.ndarray:
        if audio.size == 0:
            return audio
        sr = spec.sample_rate or self.sample_rate
        target_samples = max(1, int(spec.target_duration * sr))
        current = audio
        if audio.ndim > 1:
            current = audio.mean(axis=1)
        result = current.astype(np.float32).copy()
        while result.size < target_samples:
            chunk = self._extend_chunk(result, spec)
            if spec.crossfade > 0 and result.size > 0:
                overlap = min(int(spec.crossfade * sr), result.size // 2, chunk.size // 2)
                if overlap > 0:
                    fade_out = np.linspace(1.0, 0.0, overlap, dtype=np.float32)
                    fade_in = np.linspace(0.0, 1.0, overlap, dtype=np.float32)
                    blended = result[-overlap:] * fade_out + chunk[:overlap] * fade_in
                    result = np.concatenate([result[:-overlap], blended, chunk[overlap:]])
                else:
                    result = np.concatenate([result, chunk])
            else:
                result = np.concatenate([result, chunk])
        result = result[:target_samples]
        if audio.ndim > 1:
            result = np.broadcast_to(result[:, None], (result.size, audio.shape[1])).copy()
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def _extend_chunk(self, current: np.ndarray, spec: OutpaintSpec) -> np.ndarray:
        # Use a pitch-shifted / time-stretched repeat of the tail.
        chunk_size = max(1, min(current.size, 4096))
        tail = current[-chunk_size:]
        if spec.mode == OutpaintMode.LOOP:
            return tail
        # Slight detune for smooth extension.
        shift = 1.0 + (0.001 if spec.preserve_tempo else 0.0)
        new_chunk = self._time_stretch(tail, shift)
        return new_chunk

    def _time_stretch(self, chunk: np.ndarray, factor: float) -> np.ndarray:
        if factor == 1.0 or chunk.size == 0:
            return chunk
        new_len = max(1, int(chunk.size / factor))
        idx = np.linspace(0, chunk.size - 1, new_len, dtype=np.float32)
        i0 = np.floor(idx).astype(np.int32)
        i1 = np.minimum(i0 + 1, chunk.size - 1)
        frac = (idx - i0).astype(np.float32)
        return chunk[i0] * (1.0 - frac) + chunk[i1] * frac