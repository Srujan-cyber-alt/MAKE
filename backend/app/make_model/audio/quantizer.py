"""
Quantizer for FP32 / FP16 / INT8 with size and error measurement.

Provides deterministic quantisation of numpy arrays and reports size
reduction and reconstruction error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class QuantizeDtype(str, Enum):
    FP32 = "fp32"
    FP16 = "fp16"
    INT8 = "int8"
    INT4 = "int4"
    UINT8 = "uint8"


@dataclass
class QuantizeResult:
    data: np.ndarray
    original_dtype: str
    target_dtype: str
    original_size_bytes: int
    quantized_size_bytes: int
    compression_ratio: float
    error: float
    max_abs_error: float
    snr_db: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_dtype": self.target_dtype,
            "original_size_bytes": self.original_size_bytes,
            "quantized_size_bytes": self.quantized_size_bytes,
            "compression_ratio": self.compression_ratio,
            "error": self.error,
            "max_abs_error": self.max_abs_error,
            "snr_db": self.snr_db,
        }

    @property
    def size_bytes(self) -> int:
        return self.quantized_size_bytes


class Quantizer:
    """Quantize numpy arrays to FP32 / FP16 / INT8 with error measurement."""

    SUPPORTED_DTYPES = [d.value for d in QuantizeDtype]

    def quantize(self, data: np.ndarray, dtype: QuantizeDtype = QuantizeDtype.INT8) -> QuantizeResult:
        original = data.astype(np.float32)
        original_size = original.nbytes
        original_dtype = str(original.dtype)

        if dtype == QuantizeDtype.FP32:
            quantized = original.astype(np.float32)
        elif dtype == QuantizeDtype.FP16:
            quantized = original.astype(np.float16)
        elif dtype == QuantizeDtype.UINT8:
            quantized = self._linear_quantize(original, np.uint8, 0, 255)
        elif dtype == QuantizeDtype.INT8:
            quantized = self._linear_quantize(original, np.int8, -128, 127)
        elif dtype == QuantizeDtype.INT4:
            quantized = self._linear_quantize(original, np.int8, -8, 7, bits=4)
        else:
            raise ValueError(f"Unsupported dtype: {dtype}")

        quantized_size = quantized.nbytes
        quantized_float = quantized.astype(np.float32)
        compression = original_size / max(1, quantized_size)
        error = float(np.mean((original - quantized_float) ** 2))
        max_abs_error = float(np.max(np.abs(original - quantized_float)))
        signal_power = float(np.mean(original ** 2))
        noise_power = max(error, 1e-12)
        snr = float(10.0 * math.log10(signal_power / noise_power))

        return QuantizeResult(
            data=quantized,
            original_dtype=original_dtype,
            target_dtype=dtype.value,
            original_size_bytes=original_size,
            quantized_size_bytes=quantized_size,
            compression_ratio=compression,
            error=error,
            max_abs_error=max_abs_error,
            snr_db=snr,
        )

    def _linear_quantize(self, data: np.ndarray, dtype: Any, low: int, high: int, bits: int = 8) -> np.ndarray:
        """Linearly map data to integer range."""
        dmin = float(data.min())
        dmax = float(data.max())
        if dmax == dmin:
            # Preserve constant values at the midpoint.
            mid = (low + high) / 2.0
            return np.full(data.shape, mid, dtype=dtype)
        scale = (high - low) / (dmax - dmin)
        shifted = (data - dmin) * scale + low
        if bits < 8:
            # Mask to the lower bits.
            mask = (1 << bits) - 1
            shifted = shifted.astype(np.int32) & mask
            if low < 0:
                shifted = shifted - (1 << (bits - 1))
        return shifted.astype(dtype)

    def compare(self, data: np.ndarray, dtypes: Optional[List[QuantizeDtype]] = None) -> List[QuantizeResult]:
        dtypes = dtypes or [QuantizeDtype.FP32, QuantizeDtype.FP16, QuantizeDtype.INT8, QuantizeDtype.UINT8]
        return [self.quantize(data, dt) for dt in dtypes]

    def best_dtype(self, data: np.ndarray, max_error: float = 0.01) -> Optional[QuantizeDtype]:
        """Return the most compressed dtype that stays within ``max_error``."""
        candidates = [QuantizeDtype.INT8, QuantizeDtype.UINT8, QuantizeDtype.FP16, QuantizeDtype.FP32]
        best: Optional[QuantizeResult] = None
        best_dtype: Optional[QuantizeDtype] = None
        for dt in candidates:
            result = self.quantize(data, dt)
            if result.error <= max_error:
                if best is None or result.quantized_size_bytes < best.quantized_size_bytes:
                    best = result
                    best_dtype = dt
        return best_dtype or QuantizeDtype.FP32