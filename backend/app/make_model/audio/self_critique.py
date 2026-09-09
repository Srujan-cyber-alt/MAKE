"""
Self-critique: evaluate audio quality with PASS / REVISE / FAIL.

Inspects an audio signal and a quality report to decide whether the output
is acceptable, needs revision, or fails entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class CritiqueLevel(str, Enum):
    PASS = "PASS"
    REVISE = "REVISE"
    FAIL = "FAIL"


@dataclass
class CritiqueIssue:
    severity: str  # info | warning | error
    dimension: str
    message: str
    current_value: Optional[float] = None
    threshold: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "message": self.message,
            "current_value": self.current_value,
            "threshold": self.threshold,
        }


@dataclass
class CritiqueResult:
    level: CritiqueLevel
    score: float
    issues: List[CritiqueIssue] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
            "recommendations": list(self.recommendations),
            "details": dict(self.details),
        }


class SelfCritique:
    """Evaluate audio quality with PASS / REVISE / FAIL."""

    DEFAULT_THRESHOLDS = {
        "snr_db": 20.0,
        "clipping_ratio": 0.05,
        "silence_ratio": 0.5,
        "spectral_stability": 0.5,
    }

    def __init__(self, thresholds: Optional[Dict[str, float]] = None) -> None:
        self.thresholds = dict(thresholds) if thresholds else dict(self.DEFAULT_THRESHOLDS)

    def critique(self, audio: np.ndarray, sample_rate: int = 16000, quality_report: Optional[Any] = None) -> CritiqueResult:
        issues: List[CritiqueIssue] = []
        recommendations: List[str] = []
        details: Dict[str, Any] = {}

        snr = self._snr_db(audio)
        clipping = self._clipping_ratio(audio)
        silence = self._silence_ratio(audio, sample_rate)
        stability = self._spectral_stability(audio)

        details["snr_db"] = snr
        details["clipping_ratio"] = clipping
        details["silence_ratio"] = silence
        details["spectral_stability"] = stability

        if snr < self.thresholds["snr_db"]:
            issues.append(CritiqueIssue("error", "snr", f"SNR too low: {snr:.1f} dB", snr, self.thresholds["snr_db"]))
            recommendations.append("Reduce background noise")
        if clipping > self.thresholds["clipping_ratio"]:
            issues.append(CritiqueIssue("error", "clipping", f"Clipping ratio too high: {clipping:.3f}", clipping, self.thresholds["clipping_ratio"]))
            recommendations.append("Apply limiting / reduce gain")
        if silence > self.thresholds["silence_ratio"]:
            issues.append(CritiqueIssue("warning", "silence", f"Too much silence: {silence:.2%}", silence, self.thresholds["silence_ratio"]))
            recommendations.append("Trim silent regions")
        if stability < self.thresholds["spectral_stability"]:
            issues.append(CritiqueIssue("warning", "stability", f"Spectral instability: {stability:.2f}", stability, self.thresholds["spectral_stability"]))
            recommendations.append("Smooth spectral evolution")

        # Overall score.
        score = self._score(snr, clipping, silence, stability)
        details["score"] = score

        if score >= 0.8:
            level = CritiqueLevel.PASS
        elif score >= 0.5:
            level = CritiqueLevel.REVISE
        else:
            level = CritiqueLevel.FAIL

        return CritiqueResult(level=level, score=score, issues=issues, recommendations=recommendations, details=details)

    def _score(self, snr: float, clipping: float, silence: float, stability: float) -> float:
        snr_score = min(1.0, max(0.0, snr / 40.0))
        clip_score = max(0.0, 1.0 - clipping * 10.0)
        silence_score = max(0.0, 1.0 - silence)
        stability_score = stability
        return float(0.3 * snr_score + 0.3 * clip_score + 0.2 * silence_score + 0.2 * stability_score)

    def _snr_db(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        mono = audio.mean(axis=1) if audio.ndim > 1 else audio
        signal_power = float(np.mean(mono ** 2))
        if signal_power <= 1e-12:
            return -120.0
        noise_power = float(np.var(mono)) * 0.1 + 1e-12
        return float(10.0 * np.log10(signal_power / noise_power))

    def _clipping_ratio(self, audio: np.ndarray) -> float:
        if audio.size == 0:
            return 0.0
        return float(np.mean(np.abs(audio) >= 0.99))

    def _silence_ratio(self, audio: np.ndarray, sample_rate: int) -> float:
        if audio.size == 0:
            return 1.0
        mono = audio.mean(axis=1) if audio.ndim > 1 else audio
        return float(np.mean(np.abs(mono) < 0.01))

    def _spectral_stability(self, audio: np.ndarray) -> float:
        if audio.size < 256:
            return 0.5
        mono = audio.mean(axis=1) if audio.ndim > 1 else audio
        frame = 256
        frames = [mono[i : i + frame] for i in range(0, mono.size - frame, frame)]
        if len(frames) < 2:
            return 0.5
        spectra = [np.abs(np.fft.rfft(f)) for f in frames]
        # Normalise each spectrum.
        norms = [np.linalg.norm(s) for s in spectra]
        sims = []
        for i in range(len(spectra) - 1):
            a = spectra[i] / max(1e-6, norms[i])
            b = spectra[i + 1] / max(1e-6, norms[i + 1])
            sims.append(float(np.dot(a, b)))
        return float(np.mean(sims)) if sims else 0.5