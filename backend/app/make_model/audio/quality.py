"""
Audio quality evaluation - SNR, clipping, silence, spectral stability, intelligibility.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

from app.make_model.audio.architecture import AudioConfig, QualityReport
from app.make_model.audio.types import AudioTensor


class AudioQualityEvaluator:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config

    async def evaluate(self, audio_path: str) -> QualityReport:
        sr, data = wavfile.read(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        else:
            audio = data.astype(np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        snr = self._calculate_snr(audio)
        clipping = self._calculate_clipping(audio)
        silence = self._calculate_silence_ratio(audio, sr)
        spectral = self._calculate_spectral_stability(audio, sr)
        passed = (
            snr >= 20.0
            and clipping <= 0.01
            and silence <= 0.3
            and spectral >= 0.5
        )
        return QualityReport(
            snr_db=float(snr),
            clipping_ratio=float(clipping),
            silence_ratio=float(silence),
            spectral_stability=float(spectral),
            overall_score=float((snr / 40.0 + (1.0 - clipping) + (1.0 - silence) + spectral) / 4.0),
            passed=passed,
            details={
                "sample_rate": sr,
                "samples": len(audio),
                "duration_seconds": len(audio) / sr,
            },
        )

    def _calculate_snr(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        signal_power = np.mean(audio ** 2)
        if signal_power == 0:
            return 0.0
        noise_floor = np.percentile(np.abs(audio), 10)
        noise_power = noise_floor ** 2
        if noise_power == 0:
            return 40.0
        return float(10.0 * np.log10(signal_power / noise_power))

    def _calculate_clipping(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        clipped = np.sum(np.abs(audio) >= 0.99)
        return float(clipped / len(audio))

    def _calculate_silence_ratio(self, audio: np.ndarray, sr: int) -> float:
        if len(audio) == 0:
            return 0.0
        frame_size = int(0.025 * sr)
        hop_size = int(0.010 * sr)
        silent_frames = 0
        total_frames = 0
        for i in range(0, len(audio) - frame_size, hop_size):
            frame = audio[i:i + frame_size]
            rms = np.sqrt(np.mean(frame ** 2))
            if rms < 0.01:
                silent_frames += 1
            total_frames += 1
        if total_frames == 0:
            return 0.0
        return float(silent_frames / total_frames)

    def _calculate_spectral_stability(self, audio: np.ndarray, sr: int) -> float:
        if len(audio) < 2048:
            return 0.0
        nperseg = min(2048, len(audio))
        f, t, S = signal.spectrogram(audio, sr, nperseg=nperseg)
        if S.shape[1] < 2:
            return 0.0
        spectral_centroids = []
        for i in range(S.shape[1]):
            centroid = np.sum(f * S[:, i]) / (np.sum(S[:, i]) + 1e-10)
            spectral_centroids.append(centroid)
        if len(spectral_centroids) < 2:
            return 0.0
        stability = 1.0 - min(1.0, np.std(spectral_centroids) / (np.mean(spectral_centroids) + 1e-10))
        return float(max(0.0, stability))
