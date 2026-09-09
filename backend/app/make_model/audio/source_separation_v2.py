"""
Source Separation V2 - deterministic DSP frequency-band separation.

HONESTLY LABELED AS DSP. Not neural.
Separates: vocal, speech, music, percussion, bass, HF content, ambience, noise.
"""
from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np
from scipy import signal as scipy_signal
from enum import Enum
from dataclasses import dataclass



class SeparationBand(Enum):
    VOCAL = "vocal"
    SPEECH = "speech"
    MUSIC = "music"
    PERCUSSION = "percussion"
    BASS = "bass"
    HF_CONTENT = "high_frequency"
    AMBIENCE = "ambience"
    NOISE = "noise"


SEPARATION_BAND_DEFS: Dict[SeparationBand, Dict] = {
    SeparationBand.BASS: {"low": 20, "high": 250, "type": "lowpass"},
    SeparationBand.VOCAL: {"low": 85, "high": 1000, "type": "bandpass"},
    SeparationBand.SPEECH: {"low": 300, "high": 3400, "type": "bandpass"},
    SeparationBand.MUSIC: {"low": 250, "high": 4000, "type": "bandpass"},
    SeparationBand.PERCUSSION: {"low": 2000, "high": 8000, "type": "bandpass", "emphasis": "transient"},
    SeparationBand.HF_CONTENT: {"low": 8000, "high": 16000, "type": "highpass"},
    SeparationBand.NOISE: {"low": 16000, "high": 24000, "type": "highpass"},
    SeparationBand.AMBIENCE: {"low": 20, "high": 500, "type": "lowpass", "emphasis": "sustained"},
}


@dataclass
class SeparationResult:
    bands: Dict[str, np.ndarray]
    input_audio: np.ndarray
    input_sha256: str
    method: str
    leakage_metrics: Dict[str, float]
    artifact_score: float
    reconstruction_error: float


@dataclass
class SeparationQuality:
    sdr: float
    sir: float
    sar: float
    leakage_db: float
    artifact_level: float
    reconstruction_snr: float


class DSPSeparator:
    def __init__(self, sample_rate: int = 16000, nperseg: Optional[int] = None):
        self.sample_rate = sample_rate
        self.nperseg = nperseg or min(1024, max(64, 2 ** int(np.log2(len([1] * sample_rate)) - 1)))

    def _design_filter(self, low: float, high: float, btype: str) -> Tuple[np.ndarray, np.ndarray]:
        nyq = self.sample_rate / 2
        low_norm = min(low / nyq, 0.99)
        high_norm = min(high / nyq, 0.99)
        if btype == "lowpass":
            return scipy_signal.butter(4, low_norm, btype='low')
        elif btype == "highpass":
            return scipy_signal.butter(4, high_norm, btype='high')
        else:
            return scipy_signal.butter(4, [max(low_norm, 1e-4), min(high_norm, 0.99)], btype='band')

    def _detect_transients(self, audio: np.ndarray) -> np.ndarray:
        diff = np.abs(np.diff(audio))
        diff_padded = np.pad(diff, (1, 0), mode='constant')
        return diff_padded

    def _detect_sustained(self, audio: np.ndarray) -> np.ndarray:
        win = min(1023, len(audio) - 1)
        if win < 3:
            return np.ones_like(audio)
        env = np.abs(audio)
        kernel = np.hanning(win)
        kernel /= np.sum(kernel)
        smoothed = np.convolve(env, kernel, mode='same')
        return smoothed

    def separate(self, audio: np.ndarray) -> SeparationResult:
        import hashlib
        input_sha = hashlib.sha256(audio.tobytes()).hexdigest()[:32]
        bands: Dict[str, np.ndarray] = {}
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        for band, defn in SEPARATION_BAND_DEFS.items():
            b, a = self._design_filter(defn["low"], defn["high"], defn["type"])
            filtered = scipy_signal.filtfilt(b, a, audio)
            if defn.get("emphasis") == "transient":
                filtered = filtered * self._detect_transients(audio)
            elif defn.get("emphasis") == "sustained":
                sustain = self._detect_sustained(audio)
                sustain = np.clip(sustain / (np.max(sustain) + 1e-10), 0, 1)
                filtered = filtered * sustain
            bands[band.value] = filtered
        leakage = self._measure_leakage(bands, audio)
        artifact_score = self._measure_artifacts(bands)
        reconst = sum(bands.values()) / len(bands) if bands else np.zeros_like(audio)
        recon_err = float(np.sqrt(np.mean((audio[:min(len(audio), len(reconst))] - reconst[:min(len(audio), len(reconst))]) ** 2))) if len(audio) > 0 else 0.0
        return SeparationResult(
            bands=bands,
            input_audio=audio,
            input_sha256=input_sha,
            method="dsp_fft_filterbank_v2",
            leakage_metrics=leakage,
            artifact_score=artifact_score,
            reconstruction_error=recon_err,
        )

    def _measure_leakage(self, bands: Dict[str, np.ndarray], original: np.ndarray) -> Dict[str, float]:
        metrics = {}
        band_names = list(bands.keys())
        for i, name in enumerate(band_names):
            if i + 1 < len(band_names):
                other = bands[band_names[i + 1]]
                min_len = min(len(bands[name]), len(other))
                if min_len > 1:
                    corr = np.corrcoef(bands[name][:min_len], other[:min_len])
                    overlap = float(corr[0, 1]) if isinstance(corr, np.ndarray) and corr.ndim == 2 else 0.0
                else:
                    overlap = 0.0
                metrics[f"{name}_leakage"] = overlap if not np.isnan(overlap) else 0.0
        return metrics

    def _measure_artifacts(self, bands: Dict[str, np.ndarray]) -> float:
        scores = []
        for name, band in bands.items():
            if len(band) < 4:
                scores.append(0.0)
                continue
            diff = np.abs(np.diff(band))
            spike_rate = float(np.mean(diff > np.std(diff) * 3))
            scores.append(spike_rate)
        return float(np.mean(scores)) if scores else 0.0

    def get_quality_metrics(self, result: SeparationResult) -> SeparationQuality:
        sdr = 10 * np.log10(np.mean(result.input_audio ** 2) / (np.var(sum(result.bands.values())) + 1e-10))
        sir = 10 * np.log10(float(np.mean(result.input_audio ** 2)) / (float(np.mean((result.input_audio - np.zeros_like(result.input_audio)) ** 2)) + 1e-10))
        sar = float(np.mean([np.max(np.abs(b)) / (np.mean(np.abs(b)) + 1e-10) for b in result.bands.values()]))
        leakage_db = float(np.mean(list(result.leakage_metrics.values())))
        total_recon = sum(result.bands.values())
        min_len = min(len(total_recon), len(result.input_audio))
        recon_snr = 10 * np.log10(np.mean(result.input_audio[:min_len] ** 2) / (np.mean((result.input_audio[:min_len] - total_recon[:min_len]) ** 2) + 1e-10))
        return SeparationQuality(
            sdr=float(sdr),
            sir=float(sir),
            sar=sar,
            leakage_db=leakage_db,
            artifact_level=result.artifact_score,
            reconstruction_snr=float(recon_snr),
        )

    def get_separated_audio(self, result: SeparationResult, band_names: List[str]) -> np.ndarray:
        selected = [result.bands[name] for name in band_names if name in result.bands]
        if not selected:
            return np.zeros(len(result.input_audio))
        min_len = min(len(b) for b in selected)
        combined = np.sum([b[:min_len] for b in selected], axis=0)
        return np.clip(combined, -0.99, 0.99)



