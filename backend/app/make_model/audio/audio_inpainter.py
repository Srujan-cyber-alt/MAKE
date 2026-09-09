"""
Audio inpainting using numpy interpolation.

Replaces missing sections of an audio signal using linear, cosine, or
spline interpolation across the gap.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class InpaintMethod(str, Enum):
    LINEAR = "linear"
    COSINE = "cosine"
    SPLINE = "spline"
    SINE = "sine"


@dataclass
class InpaintMask:
    """Describes a region to be inpainted."""

    start_sample: int
    end_sample: int
    method: InpaintMethod = InpaintMethod.LINEAR

    @property
    def length(self) -> int:
        return max(0, self.end_sample - self.start_sample)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "method": self.method.value,
        }


class AudioInpainter:
    """Interpolate missing audio sections with numpy."""

    def inpaint(self, audio: np.ndarray, mask: InpaintMask) -> np.ndarray:
        if audio.size == 0:
            return audio
        start = max(0, min(mask.start_sample, audio.size - 1))
        end = max(start + 1, min(mask.end_sample, audio.size))
        if end <= start:
            return audio
        result = audio.copy()
        before = result[max(0, start - 1)]
        after = result[min(audio.size - 1, end)]
        n = end - start
        if n <= 0:
            return result
        t = np.linspace(0.0, 1.0, n, dtype=np.float32)
        if mask.method == InpaintMethod.LINEAR:
            curve = before + (after - before) * t
        elif mask.method == InpaintMethod.COSINE:
            curve = before + (after - before) * (1.0 - np.cos(t * np.pi)) / 2.0
        elif mask.method == InpaintMethod.SPLINE:
            # Simple parabolic interpolation.
            curve = before + (after - before) * t * (2.0 - t)
        else:  # SINE
            curve = before + (after - before) * np.sin(t * np.pi / 2.0)
        if audio.ndim > 1:
            curve = np.broadcast_to(curve[:, None], (n, audio.shape[1])).copy()
        result[start:end] = curve
        return result

    def inpaint_regions(self, audio: np.ndarray, masks: List[InpaintMask]) -> np.ndarray:
        result = audio.copy()
        for mask in masks:
            result = self.inpaint(result, mask)
        return result

    def detect_silence(self, audio: np.ndarray, threshold: float = 0.01, min_length: int = 100) -> List[InpaintMask]:
        """Find silent regions that could be inpainted."""
        mono = audio
        if audio.ndim > 1:
            mono = audio.mean(axis=1)
        env = np.abs(mono)
        silent = env < threshold
        masks: List[InpaintMask] = []
        i = 0
        n = silent.size
        while i < n:
            if silent[i]:
                j = i
                while j < n and silent[j]:
                    j += 1
                if j - i >= min_length:
                    masks.append(InpaintMask(start_sample=i, end_sample=j))
                i = j
            else:
                i += 1
        return masks