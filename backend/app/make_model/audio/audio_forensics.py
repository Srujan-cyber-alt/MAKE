"""
Audio forensic analysis.

Given a WAV file, determine:
- format, codec/container, sample rate, channels, duration
- loudness (RMS, peak, crest factor)
- clipping, silence, DC offset
- spectral anomalies, discontinuities, repetition
- provenance metadata
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal
from pathlib import Path


@dataclass
class ForensicReport:
    file_path: str
    file_size_bytes: int
    format: str
    sample_rate: int
    num_channels: int
    duration_seconds: float
    bit_depth: int
    total_samples: int
    peak: float
    rms: float
    crest_factor: float
    dc_offset: float
    clipping_count: int
    clipping_ratio: float
    silence_ratio: float
    dynamic_range_db: float
    spectral_center_hz: float
    spectral_bandwidth: float
    discontinuities: int
    suspicious_repetition: bool
    sha256: str
    provenance: Dict[str, Any]
    anomalies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "format": self.format,
            "sample_rate": self.sample_rate,
            "num_channels": self.num_channels,
            "duration_seconds": self.duration_seconds,
            "bit_depth": self.bit_depth,
            "total_samples": self.total_samples,
            "peak": self.peak,
            "rms": self.rms,
            "crest_factor": self.crest_factor,
            "dc_offset": self.dc_offset,
            "clipping_count": self.clipping_count,
            "clipping_ratio": self.clipping_ratio,
            "silence_ratio": self.silence_ratio,
            "dynamic_range_db": self.dynamic_range_db,
            "spectral_center_hz": self.spectral_center_hz,
            "spectral_bandwidth": self.spectral_bandwidth,
            "discontinuities": self.discontinuities,
            "suspicious_repetition": self.suspicious_repetition,
            "sha256": self.sha256,
            "provenance": self.provenance,
            "anomalies": self.anomalies,
        }


class AudioForensics:
    @staticmethod
    def analyze(file_path: str) -> ForensicReport:
        path = Path(file_path)
        file_size = path.stat().st_size
        sha256 = AudioForensics._compute_sha256(file_path)
        sr, data = wavfile.read(file_path)
        fmt = AudioForensics._detect_format(file_path)
        bit_depth = AudioForensics._detect_bit_depth(data.dtype)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        else:
            audio = data.astype(np.float32)
        if audio.ndim > 1:
            mono = np.mean(audio, axis=1)
        else:
            mono = audio
        peak = float(np.max(np.abs(mono))) if len(mono) > 0 else 0.0
        rms = float(np.sqrt(np.mean(mono ** 2))) if len(mono) > 0 else 0.0
        crest = float(peak / rms) if rms > 0 else 0.0
        dc = float(np.mean(mono)) if len(mono) > 0 else 0.0
        clipped = int(np.sum(np.abs(mono) >= 0.989))
        clipping_ratio = float(clipped / len(mono)) if len(mono) > 0 else 0.0
        frame_size = int(0.025 * sr)
        hop_size = int(0.010 * sr)
        silent = 0
        total = 0
        for i in range(0, len(mono) - frame_size, hop_size):
            frame = mono[i:i + frame_size]
            if np.sqrt(np.mean(frame ** 2)) < 0.01:
                silent += 1
            total += 1
        silence_ratio = float(silent / total) if total > 0 else 0.0
        dyn_range = float(20 * np.log10(peak / (rms + 1e-10))) if rms > 0 and peak > 0 else 0.0
        f, _, Sxx = signal.spectrogram(mono, sr, nperseg=min(2048, len(mono)))
        spec_energy = np.sum(Sxx, axis=1)
        spec_energy_norm = spec_energy / (np.sum(spec_energy) + 1e-10)
        spec_center = float(np.sum(f * spec_energy_norm)) if len(f) > 0 else 0.0
        spec_bandwidth = float(np.sqrt(np.sum((f - spec_center) ** 2 * spec_energy_norm))) if len(f) > 0 else 0.0
        discontinuities = AudioForensics._count_discontinuities(mono, threshold=0.5)
        suspicious_rep = AudioForensics._detect_repetition(mono)
        anomalies = AudioForensics._find_anomalies(
            clipping_ratio, silence_ratio, dc, dyn_range, discontinuities
        )
        provenance = AudioForensics._extract_metadata(file_path)
        return ForensicReport(
            file_path=file_path,
            file_size_bytes=file_size,
            format=fmt,
            sample_rate=sr,
            num_channels=audio.shape[0] if audio.ndim > 1 else 1,
            duration_seconds=len(mono) / sr,
            bit_depth=bit_depth,
            total_samples=len(mono),
            peak=peak,
            rms=rms,
            crest_factor=crest,
            dc_offset=dc,
            clipping_count=clipped,
            clipping_ratio=clipping_ratio,
            silence_ratio=silence_ratio,
            dynamic_range_db=dyn_range,
            spectral_center_hz=spec_center,
            spectral_bandwidth=spec_bandwidth,
            discontinuities=discontinuities,
            suspicious_repetition=suspicious_rep,
            sha256=sha256,
            provenance=provenance,
            anomalies=anomalies,
        )

    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _detect_format(file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".wav":
            return "WAV (PCM)"
        return suffix.lstrip(".")

    @staticmethod
    def _detect_bit_depth(dtype: np.dtype) -> int:
        if dtype == np.int16:
            return 16
        elif dtype == np.int32:
            return 32
        elif dtype == np.float32:
            return 32
        elif dtype == np.float64:
            return 64
        elif dtype == np.uint8:
            return 8
        return 0

    @staticmethod
    def _count_discontinuities(audio: np.ndarray, threshold: float = 0.5) -> int:
        if len(audio) < 2:
            return 0
        diffs = np.abs(np.diff(audio))
        return int(np.sum(diffs > threshold))

    @staticmethod
    def _detect_repetition(audio: np.ndarray, frame_ms: float = 50.0, sr: int = 16000) -> bool:
        frame_size = int(frame_ms * sr / 1000.0)
        if len(audio) < frame_size * 4:
            return False
        frames = []
        for i in range(0, len(audio) - frame_size, frame_size):
            frames.append(audio[i:i + frame_size])
        if len(frames) < 4:
            return False
        energies = [float(np.mean(f ** 2)) for f in frames]
        if len(energies) < 4:
            return False
        recent = energies[-4:]
        return bool(max(recent) - min(recent) < 1e-4 and max(recent) > 1e-6)

    @staticmethod
    def _find_anomalies(
        clipping: float, silence: float, dc: float, dyn_range: float, discontinuities: int
    ) -> List[str]:
        anomalies = []
        if clipping > 0.01:
            anomalies.append("high_clipping")
        if silence > 0.3:
            anomalies.append("high_silence_ratio")
        if abs(dc) > 0.01:
            anomalies.append("significant_dc_offset")
        if discontinuities > 10:
            anomalies.append("many_discontinuities")
        if dyn_range < 6.0:
            anomalies.append("low_dynamic_range")
        return anomalies

    @staticmethod
    def _extract_metadata(file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        provenance_path = path.parent / f"{path.stem}.provenance.json"
        if provenance_path.exists():
            with open(provenance_path, "r") as f:
                return json.load(f)
        return {}
