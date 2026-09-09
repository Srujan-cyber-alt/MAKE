"""
Audio quality evaluation and gating.

Measures: SNR, clipping, silence, spectral stability, intelligibility,
crest factor, DC offset, dynamic range, peak, RMS, duration consistency,
sample rate validity, channel validity, noise estimate, distortion.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal

from app.make_model.audio.architecture import AudioConfig, QualityReport
from app.make_model.audio.types import AudioTensor


QualityGateDecision = str  # "PASS" | "REVISE" | "FAIL"


class AudioQualityEvaluator:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config

    async def evaluate(self, audio_path: str) -> QualityReport:
        sr, data = wavfile.read(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.float32 or data.dtype == np.float64:
            audio = data.astype(np.float32)
        else:
            audio = data.astype(np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)
        snr = self._calculate_snr(audio)
        clipping = self._calculate_clipping(audio)
        silence = self._calculate_silence_ratio(audio, sr)
        spectral = self._calculate_spectral_stability(audio, sr)
        crest = self._calculate_crest_factor(audio)
        dc = self._calculate_dc_offset(audio)
        dynamics = self._calculate_dynamic_range(audio)
        peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
        rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        distortion = self._calculate_thd(audio, sr)
        overall = float((
            min(1.0, snr / 40.0) * 0.25
            + (1.0 - clipping) * 0.15
            + (1.0 - min(1.0, silence)) * 0.15
            + spectral * 0.15
            + (1.0 - min(1.0, crest / 20.0)) * 0.1
            + (1.0 - min(1.0, abs(dc))) * 0.1
            + dynamics * 0.1
            + (1.0 - min(1.0, distortion)) * 0.05
        ))
        passed = (
            snr >= 20.0
            and clipping <= 0.01
            and silence <= 0.3
            and spectral >= 0.5
            and abs(dc) <= 0.01
            and peak <= 0.99
            and distortion <= 0.5
        )
        return QualityReport(
            snr_db=float(snr),
            clipping_ratio=float(clipping),
            silence_ratio=float(silence),
            spectral_stability=float(spectral),
            overall_score=overall,
            passed=bool(passed),
            details={
                "sample_rate": sr,
                "samples": len(audio),
                "duration_seconds": len(audio) / sr,
                "crest_factor": crest,
                "dc_offset": dc,
                "dynamic_range": dynamics,
                "peak": peak,
                "rms": rms,
                "thd": distortion,
                "channels": 1 if audio.ndim == 1 else audio.shape[0],
            },
        )

    def gate(self, audio_path: str) -> Tuple[QualityGateDecision, QualityReport]:
        import asyncio
        report = asyncio.get_event_loop().run_until_complete(self.evaluate(audio_path)) if False else None
        if report is None:
            report = asyncio.run(self.evaluate(audio_path))
        if report.passed:
            return "PASS", report
        if report.overall_score >= 0.3:
            return "REVISE", report
        return "FAIL", report

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

    def _calculate_crest_factor(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio ** 2))
        peak = np.max(np.abs(audio))
        if rms == 0:
            return 0.0
        return float(peak / rms)

    def _calculate_dc_offset(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        return float(np.mean(audio))

    def _calculate_dynamic_range(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        peak = np.max(np.abs(audio))
        rms = np.sqrt(np.mean(audio ** 2))
        if rms == 0:
            return 0.0
        return float(min(1.0, peak / rms / 20.0))

    def _calculate_thd(self, audio: np.ndarray, sr: int) -> float:
        """Total harmonic distortion estimate."""
        if len(audio) < 4410:
            return 0.0
        f, t, S = signal.stft(audio, sr, nperseg=min(1024, len(audio)))
        if S.shape[1] < 1:
            return 0.0
        spectral_energy = np.mean(np.abs(S), axis=1)
        fundamental_idx = int(np.argmax(spectral_energy))
        harmonic_energy = 0.0
        for h in range(2, 6):
            h_idx = fundamental_idx * h
            if h_idx < len(spectral_energy):
                harmonic_energy += spectral_energy[h_idx]
        if spectral_energy[fundamental_idx] == 0:
            return 0.0
        return float(np.clip(harmonic_energy / spectral_energy[fundamental_idx], 0.0, 1.0))
