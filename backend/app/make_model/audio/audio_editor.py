"""
Audio Editor - non-destructive editing with provenance chain.

Every operation creates a new artifact with parent ID, operation metadata,
SHA-256, and immutable provenance.
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
import numpy as np
import hashlib
from pathlib import Path
from enum import Enum


class EditOperation(Enum):
    CUT = "cut"
    TRIM = "trim"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    CROSSFADE = "crossfade"
    REPLACE = "replace"
    EXTEND = "extend"
    LOOP = "loop"
    REVERSE = "reverse"
    PITCH_SHIFT = "pitch_shift"
    TIME_STRETCH = "time_stretch"
    EQ = "eq"
    COMPRESS = "compress"
    REVERB = "reverb"
    DELAY = "delay"
    DENOISE = "denoise"
    NORMALIZE = "normalize"
    SPATIALIZE = "spatialize"


@dataclass
class EditSegment:
    start: float
    end: float
    data: np.ndarray


@dataclass
class EditOperationRecord:
    op: EditOperation
    timestamp: float
    parameters: Dict[str, Any]
    input_sha256: str
    output_sha256: str
    parent_id: str
    artifact_id: str
    duration: float


@dataclass
class AudioArtifact:
    artifact_id: str
    path: Optional[str]
    parent_id: Optional[str]
    sha256: str
    duration: float
    sample_rate: int
    channels: int
    operations: List[EditOperationRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioEditor:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.artifacts: Dict[str, AudioArtifact] = {}
        self.operation_history: List[EditOperationRecord] = []

    def _new_artifact_id(self) -> str:
        import time as _time
        content = f"{_time.time_ns()}{len(self.artifacts)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _sha256_from_audio(self, audio: np.ndarray) -> str:
        return hashlib.sha256(audio.tobytes()).hexdigest()[:32]

    def register_artifact(self, audio: np.ndarray, parent_id: Optional[str] = None, path: Optional[str] = None) -> AudioArtifact:
        artifact_id = self._new_artifact_id()
        sha = self._sha256_from_audio(audio)
        duration = len(audio) / self.sample_rate
        artifact = AudioArtifact(
            artifact_id=artifact_id,
            path=path,
            parent_id=parent_id,
            sha256=sha,
            duration=duration,
            sample_rate=self.sample_rate,
            channels=1 if audio.ndim == 1 else audio.shape[1],
        )
        self.artifacts[artifact_id] = artifact
        return artifact

    def cut(self, audio: np.ndarray, start: float, end: float) -> np.ndarray:
        start_s = int(start * self.sample_rate)
        end_s = int(end * self.sample_rate)
        start_s = max(0, min(start_s, len(audio)))
        end_s = max(0, min(end_s, len(audio)))
        return audio[start_s:end_s].copy()

    def trim(self, audio: np.ndarray, start: float, end: float) -> np.ndarray:
        return self.cut(audio, start, end)

    def fade_in(self, audio: np.ndarray, duration: float = 0.5) -> np.ndarray:
        n_samples = int(duration * self.sample_rate)
        n_samples = min(n_samples, len(audio))
        if n_samples == 0:
            return audio.copy()
        fade = np.linspace(0, 1, n_samples, dtype=np.float32)
        result = audio.copy()
        result[:n_samples] = result[:n_samples] * fade
        return result

    def fade_out(self, audio: np.ndarray, duration: float = 0.5) -> np.ndarray:
        n_samples = int(duration * self.sample_rate)
        n_samples = min(n_samples, len(audio))
        if n_samples == 0:
            return audio.copy()
        fade = np.linspace(1, 0, n_samples, dtype=np.float32)
        result = audio.copy()
        result[-n_samples:] = result[-n_samples:] * fade
        return result

    def crossfade(self, audio_a: np.ndarray, audio_b: np.ndarray, fade_duration: float = 0.3) -> np.ndarray:
        n = int(fade_duration * self.sample_rate)
        n = min(n, len(audio_a), len(audio_b))
        if n == 0:
            return np.concatenate([audio_a, audio_b])
        fade_out_curve = np.linspace(1, 0, n, dtype=np.float32)
        fade_in_curve = np.linspace(0, 1, n, dtype=np.float32)
        a_end = audio_a[-n:] * fade_out_curve
        b_start = audio_b[:n] * fade_in_curve
        return np.concatenate([audio_a[:-n], a_end + b_start, audio_b[n:]])

    def loop(self, audio: np.ndarray, num_repeats: int = 2) -> np.ndarray:
        result = audio.copy()
        for _ in range(num_repeats - 1):
            result = np.concatenate([result, audio])
        return result

    def reverse(self, audio: np.ndarray) -> np.ndarray:
        return audio[::-1].copy()

    def pitch_shift(self, audio: np.ndarray, semitones: float) -> np.ndarray:
        if abs(semitones) < 0.01:
            return audio.copy()
        factor = 2.0 ** (semitones / 12.0)
        from scipy import signal as scipy_signal
        n = int(len(audio) / factor)
        if n <= 0:
            return audio.copy()
        indices = np.linspace(0, len(audio) - 1, n)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def time_stretch(self, audio: np.ndarray, rate: float) -> np.ndarray:
        if abs(rate - 1.0) < 0.01:
            return audio.copy()
        from scipy import signal as scipy_signal
        n = int(len(audio) * rate)
        if n <= 0:
            return audio.copy()
        indices = np.arange(n) * (len(audio) / n)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def normalize(self, audio: np.ndarray, target_peak: float = 0.99) -> np.ndarray:
        max_val = np.max(np.abs(audio))
        if max_val < 1e-8:
            return audio.copy()
        return np.clip(audio * (target_peak / max_val), -0.99, 0.99)

    def eq(self, audio: np.ndarray, low_gain: float = 1.0, mid_gain: float = 1.0, high_gain: float = 1.0) -> np.ndarray:
        from scipy import signal as scipy_signal
        sos_low = scipy_signal.butter(2, 200, btype='lowpass', output='sos', fs=self.sample_rate)
        sos_mid = scipy_signal.butter(2, [200, 3000], btype='bandpass', output='sos', fs=self.sample_rate)
        sos_high = scipy_signal.butter(2, 3000, btype='highpass', output='sos', fs=self.sample_rate)
        low = scipy_signal.sosfilt(sos_low, audio) * low_gain
        mid = scipy_signal.sosfilt(sos_mid, audio) * mid_gain
        high = scipy_signal.sosfilt(sos_high, audio) * high_gain
        return np.clip(low + mid + high, -0.99, 0.99).astype(np.float32)

    def compress(self, audio: np.ndarray, threshold: float = 0.5, ratio: float = 4.0, attack: float = 0.01, release: float = 0.1) -> np.ndarray:
        result = audio.copy()
        attack_samples = int(attack * self.sample_rate)
        release_samples = int(release * self.sample_rate)
        envelope = 0.0
        for i in range(len(result)):
            if abs(result[i]) > envelope:
                envelope = envelope + (abs(result[i]) - envelope) / max(1, attack_samples)
            else:
                envelope = envelope + (abs(result[i]) - envelope) / max(1, release_samples)
            if envelope > threshold:
                gain = threshold + (envelope - threshold) / ratio
                if envelope > 0:
                    result[i] = result[i] * (gain / envelope)
        return np.clip(result, -0.99, 0.99)

    def denoise(self, audio: np.ndarray, noise_floor: float = 0.01) -> np.ndarray:
        from scipy import signal as scipy_signal
        b, a = scipy_signal.butter(4, 0.1, btype='highpass', fs=2.0)
        result = scipy_signal.filtfilt(b, a, audio)
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def spatialize(self, audio: np.ndarray, azimuth: float = 0.0, elevation: float = 0.0, distance: float = 1.0) -> np.ndarray:
        import math
        az_rad = math.radians(azimuth)
        itd = 0.000625 * math.sin(az_rad)
        itd_samples = int(itd * self.sample_rate)
        left = audio.copy()
        right = audio.copy()
        if itd_samples > 0:
            left = np.pad(left, (itd_samples, 0))[:-itd_samples] if len(left) > itd_samples else left
            right = np.pad(right, (0, itd_samples))[itd_samples:] if len(right) > itd_samples else right
        attenuation = 1.0 / max(1.0, distance)
        left = left * attenuation * (1.0 - 0.3 * abs(math.sin(az_rad)))
        right = right * attenuation * (1.0 - 0.3 * abs(math.cos(az_rad)))
        return np.stack([left, right]).T.astype(np.float32)

    def reverb(self, audio: np.ndarray, room_size: float = 0.5, damping: float = 0.5, wet_mix: float = 0.3) -> np.ndarray:
        from scipy import signal as scipy_signal
        n_delay = int(room_size * self.sample_rate * 0.05)
        decay = 0.5 + room_size * 0.4
        dry = audio
        wet = audio.copy()
        for i in range(3):
            delay = n_delay * (i + 1)
            if delay < len(wet):
                wet = np.pad(wet, (delay, 0))[:-delay] if len(wet) > delay else wet
                wet *= decay * (1.0 - damping)
        result = dry * (1.0 - wet_mix) + wet * wet_mix
        return np.clip(result, -0.99, 0.99).astype(np.float32)

    def delay(self, audio: np.ndarray, delay_time: float = 0.25, feedback: float = 0.3, mix: float = 0.3) -> np.ndarray:
        delay_samples = int(delay_time * self.sample_rate)
        if delay_samples <= 0 or delay_samples > len(audio):
            return audio.copy()
        result = audio.copy()
        delayed = np.zeros_like(audio)
        for _ in range(3):
            shifted = np.zeros_like(audio)
            shifted[delay_samples:] = result[:-delay_samples]
            delayed += shifted
            result = shifted * feedback
        return np.clip(audio * (1 - mix) + delayed * mix, -0.99, 0.99)

    def execute_operation(
        self,
        op: EditOperation,
        audio: np.ndarray,
        parent_artifact_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        save_path: Optional[str] = None,
    ) -> Tuple[np.ndarray, AudioArtifact]:
        method_map = {
            EditOperation.CUT: lambda a, **kw: self.cut(a, kw.get("start", 0.0), kw.get("end", len(a) / self.sample_rate)),
            EditOperation.TRIM: lambda a, **kw: self.trim(a, kw.get("start", 0.0), kw.get("end", len(a) / self.sample_rate)),
            EditOperation.FADE_IN: lambda a, **kw: self.fade_in(a, kw.get("duration", 0.5)),
            EditOperation.FADE_OUT: lambda a, **kw: self.fade_out(a, kw.get("duration", 0.5)),
            EditOperation.LOOP: lambda a, **kw: self.loop(a, kw.get("num_repeats", 2)),
            EditOperation.REVERSE: lambda a, **kw: self.reverse(a),
            EditOperation.PITCH_SHIFT: lambda a, **kw: self.pitch_shift(a, kw.get("semitones", 0.0)),
            EditOperation.TIME_STRETCH: lambda a, **kw: self.time_stretch(a, kw.get("rate", 1.0)),
            EditOperation.NORMALIZE: lambda a, **kw: self.normalize(a, kw.get("target_peak", 0.99)),
            EditOperation.EQ: lambda a, **kw: self.eq(a, kw.get("low_gain", 1.0), kw.get("mid_gain", 1.0), kw.get("high_gain", 1.0)),
            EditOperation.COMPRESS: lambda a, **kw: self.compress(a, kw.get("threshold", 0.5), kw.get("ratio", 4.0)),
            EditOperation.DENOISE: lambda a, **kw: self.denoise(a, kw.get("noise_floor", 0.01)),
            EditOperation.SPATIALIZE: lambda a, **kw: self.spatialize(a, kw.get("azimuth", 0.0), kw.get("elevation", 0.0), kw.get("distance", 1.0)),
            EditOperation.REVERB: lambda a, **kw: self.reverb(a, kw.get("room_size", 0.5), kw.get("damping", 0.5), kw.get("wet_mix", 0.3)),
            EditOperation.DELAY: lambda a, **kw: self.delay(a, kw.get("delay_time", 0.25), kw.get("feedback", 0.3), kw.get("mix", 0.3)),
        }
        params = parameters or {}
        if op in method_map:
            result = method_map[op](audio, **params)
        elif op == EditOperation.CROSSFADE:
            other = np.load(save_path + "_other.npy") if save_path else audio
            result = self.crossfade(audio, other, params.get("fade_duration", 0.3))
        elif op == EditOperation.REPLACE:
            segment = self.cut(audio, params.get("start", 0.0), params.get("end", len(audio) / self.sample_rate))
            replacement = params.get("replacement", np.zeros_like(segment))
            result = audio.copy()
            start_idx = int(params.get("start", 0.0) * self.sample_rate)
            result[start_idx:start_idx + len(replacement)] = replacement
        elif op == EditOperation.EXTEND:
            extension = params.get("extension", audio)
            result = np.concatenate([audio, extension])
        else:
            result = audio.copy()
        input_sha = self._sha256_from_audio(audio)
        output_sha = self._sha256_from_audio(result)
        artifact = self.register_artifact(result, parent_id=parent_artifact_id, path=save_path)
        record = EditOperationRecord(
            op=op,
            timestamp=0.0,
            parameters=params,
            input_sha256=input_sha,
            output_sha256=output_sha,
            parent_id=parent_artifact_id or "",
            artifact_id=artifact.artifact_id,
            duration=len(result) / self.sample_rate,
        )
        artifact.operations.append(record)
        self.operation_history.append(record)
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            import soundfile as sf
            sf.write(save_path, result, self.sample_rate)
            artifact.path = save_path
        return result, artifact

    def get_provenance_chain(self, artifact_id: str) -> List[EditOperationRecord]:
        chain = []
        artifact = self.artifacts.get(artifact_id)
        if artifact:
            for op_record in artifact.operations:
                chain.append(op_record)
                parent_record = self.get_provenance_chain(op_record.parent_id) if op_record.parent_id else []
                chain.extend(parent_record)
        return chain
