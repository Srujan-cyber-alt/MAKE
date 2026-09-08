"""MAKE Audio — WAV file I/O and AudioBuffer container.

Uses Python's standard-library ``wave`` module for I/O so no external
codec dependencies are required. ``AudioBuffer`` wraps a numpy array with
sample-rate metadata.
"""

from __future__ import annotations

import os
import wave
import struct
import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass
class AudioBuffer:
    samples: np.ndarray
    sample_rate: int
    channels: int = 1

    def __post_init__(self):
        if self.samples.ndim == 1:
            self.channels = 1
        elif self.samples.ndim == 2:
            self.channels = self.samples.shape[1]

    @property
    def duration(self) -> float:
        if len(self.samples) == 0:
            return 0.0
        if self.samples.ndim > 1:
            return len(self.samples) / self.sample_rate
        return len(self.samples) / self.sample_rate

    @property
    def rms(self) -> float:
        if len(self.samples) == 0:
            return 0.0
        mono = self.samples.mean(axis=-1) if self.samples.ndim > 1 else self.samples
        return float(np.sqrt(np.mean(mono ** 2)))

    @property
    def peak(self) -> float:
        return float(np.max(np.abs(self.samples))) if len(self.samples) > 0 else 0.0

    def to_mono(self) -> "AudioBuffer":
        if self.channels == 1:
            return self
        mono = self.samples.mean(axis=1)
        return AudioBuffer(samples=mono, sample_rate=self.sample_rate, channels=1)

    def to_stereo(self) -> "AudioBuffer":
        if self.channels >= 2:
            return self
        left = self.samples
        right = self.samples
        stereo = np.column_stack([left, right])
        return AudioBuffer(samples=stereo, sample_rate=self.sample_rate, channels=2)

    def resample(self, new_rate: int) -> "AudioBuffer":
        if new_rate == self.sample_rate:
            return self
        if self.samples.ndim > 1:
            ch = self.samples.shape[1]
            resampled = np.column_stack([
                _resample_1d(self.samples[:, c], self.sample_rate, new_rate)
                for c in range(ch)
            ])
        else:
            resampled = _resample_1d(self.samples, self.sample_rate, new_rate)
        return AudioBuffer(samples=resampled, sample_rate=new_rate, channels=self.channels)

    def normalized(self, target_rms: float = 0.1) -> "AudioBuffer":
        mono = self.samples
        if self.samples.ndim > 1:
            mono = self.samples.mean(axis=-1)
        rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) > 0 else 0.0
        if rms > 1e-10:
            factor = target_rms / rms
            return AudioBuffer(
                samples=self.samples * factor,
                sample_rate=self.sample_rate,
                channels=self.channels,
            )
        return self


def _resample_1d(signal: np.ndarray, old_rate: int, new_rate: int) -> np.ndarray:
    n = len(signal)
    if n == 0:
        return signal
    step = old_rate / new_rate
    indices = np.arange(0, n, step)
    indices = indices[indices < n]
    return np.interp(indices, np.arange(n), signal)


def read_wav(path: str) -> AudioBuffer:
    with wave.open(path, "rb") as w:
        n_channels = w.getnchannels()
        sample_width = w.getsampwidth()
        sample_rate = w.getframerate()
        n_frames = w.getnframes()
        raw = w.readframes(n_frames)

    dtype_map = {1: np.int8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width, np.int16)
    arr = np.frombuffer(raw, dtype=dtype)
    if sample_width == 1:
        arr = arr.astype(np.float32) / 128.0
    elif sample_width == 2:
        arr = arr.astype(np.float32) / 32768.0
    elif sample_width == 4:
        arr = arr.astype(np.float32) / 2147483648.0

    if n_channels > 1:
        arr = arr.reshape(-1, n_channels)
    return AudioBuffer(samples=arr, sample_rate=sample_rate, channels=n_channels)


def write_wav(path: str, buffer: AudioBuffer) -> str:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    samples = buffer.samples
    if samples.dtype != np.float32 and samples.dtype != np.float64:
        samples = samples.astype(np.float32)
    samples = np.clip(samples, -1.0, 1.0)

    bit_depth = 16
    max_val = 32767

    if buffer.channels == 1:
        int_samples = (samples * max_val).astype(np.int16)
    else:
        int_samples = (samples * max_val).astype(np.int16)
        int_samples = int_samples.reshape(-1)

    with wave.open(path, "wb") as w:
        w.setnchannels(buffer.channels)
        w.setsampwidth(bit_depth // 8)
        w.setframerate(buffer.sample_rate)
        if buffer.channels == 1:
            w.writeframes(int_samples.tobytes())
        else:
            w.writeframes(int_samples.tobytes())

    return path
