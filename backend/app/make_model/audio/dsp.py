"""MAKE Audio — Digital Signal Processing primitives (CPU-only, numpy).

Implements real waveform generation, filtering, panning, and analysis
functions. All operations are deterministic when a seed is provided.
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Optional, List


RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------

def sine(frequency: float, duration: float, sample_rate: int,
         amplitude: float = 0.5) -> np.ndarray:
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    return amplitude * np.sin(2 * np.pi * frequency * t)


def square(frequency: float, duration: float, sample_rate: int,
           amplitude: float = 0.5, duty: float = 0.5) -> np.ndarray:
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    return amplitude * np.sign(np.sin(2 * np.pi * frequency * t) - (duty - 0.5))


def sawtooth(frequency: float, duration: float, sample_rate: int,
             amplitude: float = 0.5) -> np.ndarray:
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    return amplitude * (2 * (frequency * t - np.floor(frequency * t + 0.5)))


def triangle(frequency: float, duration: float, sample_rate: int,
             amplitude: float = 0.5) -> np.ndarray:
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    return amplitude * (2 * np.abs(2 * (frequency * t - np.floor(frequency * t + 0.5))) - 1)


def white_noise(duration: float, sample_rate: int, amplitude: float = 0.5,
                seed: Optional[int] = None) -> np.ndarray:
    rng = np.random.default_rng(seed) if seed is not None else RNG
    n = int(sample_rate * duration)
    return amplitude * rng.uniform(-1, 1, n)


def pink_noise(duration: float, sample_rate: int, amplitude: float = 0.5,
               seed: Optional[int] = None) -> np.ndarray:
    """Pink noise via filtered white noise (approximately 3 dB/octave)."""
    rng = np.random.default_rng(seed) if seed is not None else RNG
    n = int(sample_rate * duration)
    white = rng.uniform(-1, 1, n)
    # Simple first-order filter cascade to approximate pink spectrum
    pink = np.zeros(n)
    pink[0] = white[0]
    coeff = 0.997
    for i in range(1, n):
        pink[i] = coeff * pink[i - 1] + (1 - coeff) * white[i]
    peak = np.max(np.abs(pink))
    if peak > 1e-10:
        pink /= peak
    return amplitude * pink


def pulse_train(frequency: float, duration: float, sample_rate: int,
                amplitude: float = 0.5, width: float = 0.005) -> np.ndarray:
    """Generate a pulse train (glottal pulse for speech synthesis)."""
    n = int(sample_rate * duration)
    t = np.arange(n) / sample_rate
    period = 1.0 / frequency
    pulse = np.zeros(n)
    for i in range(n):
        phase = t[i] % period
        if phase < width:
            pulse[i] = amplitude
    return pulse


# ---------------------------------------------------------------------------
# Envelope generation
# ---------------------------------------------------------------------------

def adsr(duration: float, sample_rate: int,
         attack: float = 0.01, decay: float = 0.1,
         sustain_level: float = 0.8, release: float = 0.1,
         gate_duration: Optional[float] = None) -> np.ndarray:
    """ADSR envelope. Values in [0, 1]."""
    n = int(sample_rate * duration)
    if n == 0:
        return np.array([])

    if gate_duration is None:
        gate_duration = max(duration - release, 0.01)

    a_samp = max(int(attack * sample_rate), 1)
    d_samp = max(int(decay * sample_rate), 1)
    s_end = int(gate_duration * sample_rate)
    r_samp = max(int(release * sample_rate), 1)

    env = np.zeros(n)

    # Attack
    end = min(a_samp, n)
    env[:end] = np.linspace(0, 1, end)

    # Decay
    d_start = a_samp
    d_end = min(a_samp + d_samp, n, s_end)
    if d_start < d_end:
        env[d_start:d_end] = np.linspace(1, sustain_level, d_end - d_start)

    # Sustain
    s_start = min(a_samp + d_samp, n, s_end)
    s_end_clamped = min(s_end, n)
    if s_start < s_end_clamped:
        env[s_start:s_end_clamped] = sustain_level

    # Release
    r_start = s_end_clamped
    r_end = min(r_start + r_samp, n)
    if r_start < n:
        env[r_start:r_end] = np.linspace(sustain_level, 0, r_end - r_start)

    return env


def linear_ramp(length: int, start: float = 1.0, end: float = 0.0) -> np.ndarray:
    return np.linspace(start, end, length)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def butter_lowpass(signal: np.ndarray, cutoff: float, sample_rate: int,
                   order: int = 4) -> np.ndarray:
    """Butterworth lowpass via FFT (zero-phase)."""
    n = len(signal)
    if n < 2:
        return signal.copy()
    freqs = np.fft.fftfreq(n, d=1.0 / sample_rate)
    spectrum = np.fft.fft(signal)
    response = 1.0 / np.sqrt(1 + (np.abs(freqs) / cutoff) ** (2 * order))
    filtered = np.fft.ifft(spectrum * response).real
    return filtered


def butter_highpass(signal: np.ndarray, cutoff: float, sample_rate: int,
                    order: int = 4) -> np.ndarray:
    """Butterworth highpass via FFT (zero-phase)."""
    n = len(signal)
    if n < 2:
        return signal.copy()
    freqs = np.fft.fftfreq(n, d=1.0 / sample_rate)
    spectrum = np.fft.fft(signal)
    response = np.sqrt(1 - 1.0 / np.sqrt(1 + (np.abs(freqs) / cutoff) ** (2 * order)))
    filtered = np.fft.ifft(spectrum * response).real
    return filtered


def formant_filter(signal: np.ndarray, sample_rate: int,
                   formants: List[Tuple[float, float]],
                   bandwidth: float = 80.0) -> np.ndarray:
    """Apply resonant formant bandpass filters.

    formants: list of (frequency_hz, gain_db) tuples.
    """
    result = signal.copy()
    for freq, gain_db in formants:
        gain_lin = 10 ** (gain_db / 20)
        response = _bandpass_response(len(result), sample_rate, freq, bandwidth)
        spectrum = np.fft.fft(result)
        result = np.fft.ifft(spectrum * response * gain_lin).real
    return result


def _bandpass_response(n: int, sample_rate: int, center: float,
                       bandwidth: float) -> np.ndarray:
    freqs = np.fft.fftfreq(n, d=1.0 / sample_rate)
    response = np.exp(-((freqs - center) ** 2) / (2 * (bandwidth / 2.355) ** 2))
    response += np.exp(-((freqs + center) ** 2) / (2 * (bandwidth / 2.355) ** 2))
    return response


# ---------------------------------------------------------------------------
# Stereo / spatial
# ---------------------------------------------------------------------------

def pan_stereo(mono: np.ndarray, position: float) -> np.ndarray:
    """Constant-power stereo panning. Position: -1 (left) … +1 (right)."""
    position = np.clip(position, -1.0, 1.0)
    left_gain = np.cos(position * np.pi / 2)
    right_gain = np.sin(np.abs(position) * np.pi / 2)
    left = mono * left_gain
    right = mono * right_gain
    return np.column_stack([left, right])


def stereo_widen(signal: np.ndarray, width: float = 0.3) -> np.ndarray:
    """Enhance stereo width via mid-side processing."""
    if signal.ndim == 1:
        signal = np.column_stack([signal, signal])
    mid = (signal[:, 0] + signal[:, 1]) / 2
    side = (signal[:, 0] - signal[:, 1]) / 2
    new_side = side * (1 + width)
    left = mid + new_side
    right = mid - new_side
    return np.column_stack([left, right])


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def compute_rms(signal: np.ndarray) -> float:
    if signal.ndim > 1:
        signal = signal.mean(axis=1)
    if len(signal) == 0:
        return 0.0
    return float(np.sqrt(np.mean(signal ** 2)))


def compute_peak(signal: np.ndarray) -> float:
    return float(np.max(np.abs(signal)))


def remove_dc(signal: np.ndarray) -> np.ndarray:
    if signal.ndim > 1:
        return signal - signal.mean(axis=0, keepdims=True)
    return signal - signal.mean()


def normalize(signal: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
    rms = compute_rms(signal)
    if rms > 1e-10:
        return signal * (target_rms / rms)
    return signal


def spectral_centroid(signal: np.ndarray, sample_rate: int) -> float:
    n = len(signal)
    if n < 2:
        return 0.0
    spectrum = np.abs(np.fft.rfft(signal))
    freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)
    total = np.sum(spectrum)
    if total == 0:
        return 0.0
    return float(np.sum(freqs * spectrum) / total)


def zero_crossing_rate(signal: np.ndarray) -> float:
    if len(signal) < 2:
        return 0.0
    signs = np.sign(signal)
    return float(np.sum(np.abs(np.diff(signs))) / (2 * len(signal)))


# ---------------------------------------------------------------------------
# Mixing / editing utilities
# ---------------------------------------------------------------------------

def mix_buffers(signals: List[np.ndarray],
                weights: Optional[List[float]] = None) -> np.ndarray:
    if not signals:
        return np.array([])
    if weights is None:
        weights = [1.0 / len(signals)] * len(signals)
    max_len = max(len(s) for s in signals)
    result = np.zeros(max_len)
    for s, w in zip(signals, weights):
        result[:len(s)] += s * w
    return result


def crossfade(a: np.ndarray, b: np.ndarray,
              fade_duration: float, sample_rate: int) -> np.ndarray:
    fade_n = int(fade_duration * sample_rate)
    fade_n = min(fade_n, len(a), len(b))
    if fade_n <= 0:
        return np.concatenate([a, b])
    env = np.linspace(1, 0, fade_n)
    fade_out = a[-fade_n:] * env
    fade_in = b[:fade_n] * (1 - env)
    return np.concatenate([a[:-fade_n], fade_out + fade_in, b[fade_n:]])


def trim_silence(signal: np.ndarray, threshold: float = 0.001) -> np.ndarray:
    above = np.abs(signal) > threshold
    if not np.any(above):
        return np.array([])
    idx = np.where(above)[0]
    return signal[idx[0]:idx[-1] + 1]


def time_stretch(signal: np.ndarray, rate: float) -> np.ndarray:
    """Simple WSOLA-style time stretch (phase vocoder approximation)."""
    if rate <= 0:
        raise ValueError("rate must be positive")
    if abs(rate - 1.0) < 1e-6:
        return signal.copy()
    n = len(signal)
    indices = np.arange(n) * (1.0 / rate)
    indices = indices[indices < n]
    return np.interp(indices, np.arange(n), signal)


def change_speed(signal: np.ndarray, rate: float) -> np.ndarray:
    return time_stretch(signal, rate)
