"""
Audio Reconstruction - gap repair, clipped segment repair, dropout repair.

Maintains continuity with neighboring audio. Never silently fabricates;
always records reconstruction provenance.
"""
from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass, field
import numpy as np
import hashlib


@dataclass
class ReconstructionRecord:
    method: str
    start_sample: int
    end_sample: int
    duration: float
    parameters: Dict[str, Any]
    input_sha256: str
    output_sha256: str
    quality_before: float
    quality_after: float


@dataclass
class ReconstructionResult:
    audio: np.ndarray
    records: List[ReconstructionRecord]
    confidence: float
    steps: List[ReconstructionRecord] = field(default_factory=list)


class AudioReconstructor:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.history: List[ReconstructionRecord] = []

    def _sha256(self, audio: np.ndarray) -> str:
        return hashlib.sha256(audio.tobytes()).hexdigest()[:32]

    def repair_clipping(self, audio: np.ndarray, threshold: float = 0.98) -> Tuple[np.ndarray, ReconstructionRecord]:
        result = audio.copy()
        clipped_mask = np.abs(result) >= threshold
        quality_before = float(np.mean(np.abs(result)))
        if np.any(clipped_mask):
            for i in range(len(result)):
                if clipped_mask[i]:
                    left = result[i - 1] if i > 0 else result[i]
                    right = result[i + 1] if i < len(result) - 1 else result[i]
                    result[i] = (left + right) / 2
        quality_after = float(np.mean(np.abs(result)))
        record = ReconstructionRecord(
            method="clipping_repair",
            start_sample=0,
            end_sample=len(audio),
            duration=len(audio) / self.sample_rate,
            parameters={"threshold": threshold},
            input_sha256=self._sha256(audio),
            output_sha256=self._sha256(result),
            quality_before=quality_before,
            quality_after=quality_after,
        )
        self.history.append(record)
        return result, record

    def repair_dropout(self, audio: np.ndarray, dropout_threshold: float = 0.001, gap_size_ms: int = 20) -> Tuple[np.ndarray, List[ReconstructionRecord]]:
        result = audio.copy()
        records: List[ReconstructionRecord] = []
        gap_samples = int(self.sample_rate * gap_size_ms / 1000)
        silence_mask = np.abs(result) < dropout_threshold
        i = 0
        quality_before = float(np.std(result))
        while i < len(result):
            if silence_mask[i]:
                start = i
                while i < len(result) and silence_mask[i]:
                    i += 1
                end = i
                gap_len = end - start
                if gap_len >= gap_samples:
                    left = result[start - 1] if start > 0 else 0.0
                    right = result[end] if end < len(result) else 0.0
                    for j in range(start, end):
                        if end < len(result):
                            alpha = (j - start + 1) / (gap_len + 1)
                            result[j] = left * (1 - alpha) + right * alpha
                    record = ReconstructionRecord(
                        method="dropout_repair",
                        start_sample=start,
                        end_sample=end,
                        duration=gap_len / self.sample_rate,
                        parameters={"threshold": dropout_threshold, "interpolation": "linear"},
                        input_sha256=self._sha256(audio),
                        output_sha256=self._sha256(result),
                        quality_before=quality_before,
                        quality_after=float(np.std(result)),
                    )
                    records.append(record)
                    self.history.append(record)
            else:
                i += 1
        return result, records

    def repair_discontinuity(self, audio: np.ndarray, threshold: float = 0.5) -> Tuple[np.ndarray, List[ReconstructionRecord]]:
        result = audio.copy()
        records: List[ReconstructionRecord] = []
        diff = np.abs(np.diff(result))
        jumps = np.where(diff > threshold)[0]
        quality_before = float(np.std(result))
        for idx in jumps:
            if idx > 0 and idx < len(result) - 1:
                left = result[idx]
                right = result[idx + 1]
                window = 5
                left_smooth = np.mean(result[max(0, idx - window):idx])
                right_smooth = np.mean(result[idx + 1:min(len(result), idx + window + 1)])
                result[idx] = (left + right) / 2
                result[idx + 1] = (left + right) / 2
                record = ReconstructionRecord(
                    method="discontinuity_repair",
                    start_sample=idx,
                    end_sample=idx + 2,
                    duration=2 / self.sample_rate,
                    parameters={"threshold": threshold, "window": window},
                    input_sha256=self._sha256(audio),
                    output_sha256=self._sha256(result),
                    quality_before=quality_before,
                    quality_after=float(np.std(result)),
                )
                records.append(record)
                self.history.append(record)
        return result, records

    def reconstruct_gap(self, audio: np.ndarray, start_sample: int, end_sample: int, method: str = "interpolation") -> Tuple[np.ndarray, ReconstructionRecord]:
        result = audio.copy()
        quality_before = float(np.std(audio[start_sample:end_sample + 1]) if start_sample < len(audio) else 0)
        if start_sample < 0 or end_sample >= len(audio) or start_sample >= end_sample:
            return result, ReconstructionRecord(
                method=method, start_sample=start_sample, end_sample=end_sample,
                duration=0, parameters={}, input_sha256=self._sha256(audio),
                output_sha256=self._sha256(result), quality_before=0, quality_after=0,
            )
        gap_len = end_sample - start_sample
        left = audio[start_sample - 1] if start_sample > 0 else audio[start_sample]
        right = audio[end_sample + 1] if end_sample < len(audio) - 1 else audio[end_sample]
        if method == "interpolation":
            for j in range(start_sample, end_sample + 1):
                alpha = (j - start_sample + 1) / (gap_len + 1)
                result[j] = left * (1 - alpha) + right * alpha
        elif method == "repeat":
            segment = audio[start_sample:end_sample + 1]
            if len(segment) > 0:
                result[start_sample:end_sample + 1] = np.resize(segment, gap_len + 1)
        elif method == "noise":
            rng = np.random.RandomState(42)
            result[start_sample:end_sample + 1] = rng.uniform(-0.01, 0.01, gap_len + 1)
        record = ReconstructionRecord(
            method=method,
            start_sample=start_sample,
            end_sample=end_sample,
            duration=gap_len / self.sample_rate,
            parameters={"method": method, "gap_samples": gap_len + 1},
            input_sha256=self._sha256(audio),
            output_sha256=self._sha256(result),
            quality_before=quality_before,
            quality_after=float(np.std(result[start_sample:end_sample + 1])),
        )
        self.history.append(record)
        return result, record

    def reconstruct_ambience(self, audio: np.ndarray, ambient_region: Tuple[int, int], target_region: Tuple[int, int]) -> Tuple[np.ndarray, ReconstructionRecord]:
        result = audio.copy()
        amb_start, amb_end = ambient_region
        tgt_start, tgt_end = target_region
        if amb_start >= amb_end or tgt_start >= tgt_end:
            return result, ReconstructionRecord(method="ambience_copy", start_sample=tgt_start, end_sample=tgt_end, duration=0, parameters={}, input_sha256=self._sha256(audio), output_sha256=self._sha256(result), quality_before=0, quality_after=0)
        ambient_segment = audio[amb_start:amb_end]
        seg_len = tgt_end - tgt_start
        if len(ambient_segment) >= seg_len:
            replacement = ambient_segment[:seg_len]
        else:
            replacement = np.resize(ambient_segment, seg_len)
        result[tgt_start:tgt_end] = replacement * 0.7
        record = ReconstructionRecord(
            method="ambience_continuity",
            start_sample=tgt_start,
            end_sample=tgt_end,
            duration=seg_len / self.sample_rate,
            parameters={"source_region": list(ambient_region), "target_region": list(target_region), "attenuation": 0.7},
            input_sha256=self._sha256(audio),
            output_sha256=self._sha256(result),
            quality_before=float(np.std(audio[tgt_start:tgt_end])),
            quality_after=float(np.std(result[tgt_start:tgt_end])),
        )
        self.history.append(record)
        return result, record

    def full_reconstruction(self, audio: np.ndarray) -> ReconstructionResult:
        result = audio.copy()
        records: List[ReconstructionRecord] = []
        result, clip_rec = self.repair_clipping(result)
        records.append(clip_rec)
        result, dropout_recs = self.repair_dropout(result)
        records.extend(dropout_recs)
        result, disc_recs = self.repair_discontinuity(result)
        records.extend(disc_recs)
        confidence = 1.0 if len(records) <= 1 else min(1.0, len([r for r in records if r.quality_after >= r.quality_before]) / max(1, len(records)))
        return ReconstructionResult(audio=result, records=records, confidence=confidence, steps=records)
