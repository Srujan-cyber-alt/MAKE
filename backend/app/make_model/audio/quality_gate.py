"""
MAKE Audio Quality Gate V2.

Weighted scoring with continuity-aware quality assessment.
Produces PASS / REVISE / FAIL with machine-readable reasons.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal as signal


QualityDecision = str  # "PASS" | "REVISE" | "FAIL"


@dataclass
class QualityDimension:
    name: str
    weight: float
    score: float = 0.0
    threshold_pass: float = 0.7
    threshold_revise: float = 0.4

    @property
    def decision(self) -> QualityDecision:
        if self.score >= self.threshold_pass:
            return "PASS"
        if self.score >= self.threshold_revise:
            return "REVISE"
        return "FAIL"


@dataclass
class QualityReportV2:
    overall_score: float
    decision: QualityDecision
    dimensions: List[QualityDimension]
    details: Dict[str, Any]
    reasons: List[str]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "decision": self.decision,
            "dimensions": [
                {"name": d.name, "weight": d.weight, "score": d.score, "decision": d.decision}
                for d in self.dimensions
            ],
            "details": self.details,
            "reasons": self.reasons,
            "provenance": self.provenance,
        }


class QualityGateV2:
    DEFAULT_WEIGHTS = {
        "technical": 0.40,
        "continuity": 0.20,
        "identity": 0.15,
        "acoustic": 0.10,
        "semantic": 0.15,
    }

    def __init__(self, sample_rate: int = 16000, weights: Optional[Dict[str, float]] = None):
        self.sample_rate = sample_rate
        self.weights = weights or dict(self.DEFAULT_WEIGHTS)

    def evaluate(
        self,
        audio_path: str,
        expected_duration: Optional[float] = None,
        expected_sample_rate: int = 16000,
        continuity_score: float = 1.0,
        identity_score: float = 1.0,
        semantic_match: bool = True,
        room_rt60: Optional[float] = None,
        provenance: Optional[Dict[str, Any]] = None,
    ) -> QualityReportV2:
        sr, data = wavfile.read(audio_path)
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        else:
            audio = data.astype(np.float32)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        technical = QualityDimension(
            "technical", self.weights["technical"],
            score=self._technical_score(audio, sr),
            threshold_pass=0.7, threshold_revise=0.4,
        )
        continuity = QualityDimension(
            "continuity", self.weights["continuity"],
            score=continuity_score,
            threshold_pass=0.7, threshold_revise=0.4,
        )
        identity = QualityDimension(
            "identity", self.weights["identity"],
            score=identity_score,
            threshold_pass=0.8, threshold_revise=0.5,
        )
        acoustic = QualityDimension(
            "acoustic", self.weights["acoustic"],
            score=self._acoustic_score(audio, sr, room_rt60),
            threshold_pass=0.6, threshold_revise=0.3,
        )
        semantic = QualityDimension(
            "semantic", self.weights["semantic"],
            score=1.0 if semantic_match else 0.0,
            threshold_pass=1.0, threshold_revise=0.5,
        )

        dimensions = [technical, continuity, identity, acoustic, semantic]
        weighted = sum(d.score * d.weight for d in dimensions) / sum(d.weight for d in dimensions)
        decision = self._overall_decision(dimensions, weighted)

        reasons = []
        if technical.decision == "FAIL":
            reasons.append(f"Technical quality below threshold: {technical.score:.2f}")
        if continuity.decision == "FAIL":
            reasons.append(f"Continuity score below threshold: {continuity.score:.2f}")
        if identity.decision == "FAIL":
            reasons.append(f"Identity consistency below threshold: {identity.score:.2f}")
        if acoustic.decision == "FAIL":
            reasons.append(f"Acoustic quality below threshold: {acoustic.score:.2f}")
        if semantic.decision == "FAIL":
            reasons.append("Semantic requirements not met")
        if not reasons:
            reasons.append("All dimensions within acceptable thresholds")

        details = {
            "sample_rate": sr,
            "duration_seconds": len(audio) / sr,
            "expected_sr": expected_sample_rate,
            "sr_valid": sr == expected_sample_rate,
            "expected_duration": expected_duration,
            "duration_valid": expected_duration is None or abs(len(audio) / sr - expected_duration) < 0.5,
            "channels": 1 if audio.ndim == 1 else audio.shape[0],
            "snr_db": self._snr(audio),
            "clipping_ratio": self._clipping(audio),
            "silence_ratio": self._silence(audio, sr),
            "crest_factor": self._crest(audio),
            "dc_offset": float(np.mean(audio)),
            "thd": self._thd(audio, sr),
            "dynamic_range_db": self._dynamic_range(audio),
        }

        return QualityReportV2(
            overall_score=weighted,
            decision=decision,
            dimensions=dimensions,
            details=details,
            reasons=reasons,
            provenance=provenance or {},
        )

    def _technical_score(self, audio: np.ndarray, sr: int) -> float:
        snr = self._snr(audio)
        clip = self._clipping(audio)
        silence = self._silence(audio, sr)
        thd = self._thd(audio, sr)
        dc = abs(float(np.mean(audio)))
        score = 1.0
        if snr < 20:
            score -= (20 - snr) / 40
        if clip > 0.01:
            score -= min(0.5, clip * 50)
        if silence > 0.2:
            score -= min(0.5, (silence - 0.2) * 2)
        if thd > 0.3:
            score -= min(0.3, thd * 0.5)
        if dc > 0.01:
            score -= min(0.2, dc)
        return max(0.0, score)

    def _acoustic_score(self, audio: np.ndarray, sr: int, room_rt60: Optional[float]) -> float:
        score = 1.0
        if len(audio) < sr * 0.1:
            score -= 0.3
        if room_rt60 is not None and room_rt60 > 2.0:
            score -= min(0.4, (room_rt60 - 2.0) / 2.0)
        return max(0.0, score)

    def _overall_decision(self, dims: List[QualityDimension], weighted: float) -> QualityDecision:
        min_score = min(d.score for d in dims)
        if min_score < 0.3:
            return "FAIL"
        if weighted < 0.5:
            return "FAIL"
        if weighted < 0.7 or any(d.decision == "FAIL" for d in dims if d.weight > 0.1):
            return "REVISE"
        return "PASS"

    def _dynamic_range(self, audio: np.ndarray) -> float:
        peak = float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0
        rms = float(np.sqrt(np.mean(audio ** 2))) if len(audio) > 0 else 0.0
        if rms < 1e-10:
            return 0.0
        return float(20 * np.log10(peak / rms))

    def _snr(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        signal_power = np.mean(audio ** 2)
        if signal_power == 0:
            return 0.0
        noise_floor = np.percentile(np.abs(audio), 10)
        return float(10 * np.log10(signal_power / max(noise_floor ** 2, 1e-10)))

    def _clipping(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        return float(np.sum(np.abs(audio) >= 0.99) / len(audio))

    def _silence(self, audio: np.ndarray, sr: int) -> float:
        if len(audio) == 0:
            return 0.0
        frame_size = int(0.025 * sr)
        hop = int(0.010 * sr)
        silent = sum(1 for i in range(0, len(audio) - frame_size, hop)
                      if np.sqrt(np.mean(audio[i:i+frame_size] ** 2)) < 0.01)
        total = max(1, (len(audio) - frame_size) // hop + 1)
        return float(silent / total)

    def _crest(self, audio: np.ndarray) -> float:
        if len(audio) == 0:
            return 0.0
        rms = np.sqrt(np.mean(audio ** 2))
        if rms == 0:
            return 0.0
        return float(np.max(np.abs(audio)) / rms)

    def _thd(self, audio: np.ndarray, sr: int) -> float:
        if len(audio) < 4410:
            return 0.0
        n_fft = min(1024, len(audio))
        f, t_arr, S = signal.stft(audio, sr, nperseg=n_fft)
        if S.shape[1] < 1:
            return 0.0
        energy = np.mean(np.abs(S), axis=1)
        fund = int(np.argmax(energy))
        harmonic = 0.0
        for h in range(2, 6):
            h_idx = fund * h
            if h_idx < len(energy):
                harmonic += energy[h_idx]
        if energy[fund] == 0:
            return 0.0
        return float(np.clip(harmonic / energy[fund], 0.0, 1.0))
