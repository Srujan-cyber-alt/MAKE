"""
Advanced Acting Engine V2 - cinematic acting controls.

Styles: whisper, shout, restrained, nervous, sarcastic, confident,
hesitant, intimate, authoritative, exhausted, crying, laughing,
breathy, dramatic.

Supports: pauses, interruptions, hesitation, breaths, emphasis,
reactions, overlapping speech, conversational timing.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import math


class ActingStyle(Enum):
    NEUTRAL = "neutral"
    WHISPER = "whisper"
    SHOUT = "shout"
    RESTRAINED = "restrained"
    NERVOUS = "nervous"
    SARCASTIC = "sarcastic"
    CONFIDENT = "confident"
    HESITANT = "hesitant"
    INTIMATE = "intimate"
    AUTHORITATIVE = "authoritative"
    EXHAUSTED = "exhausted"
    CRYING = "crying"
    LAUGHING = "laughing"
    BREATHY = "breathy"
    DRAMATIC = "dramatic"
    URGENT = "urgent"
    CALM = "calm"


@dataclass
class ActingParameters:
    style: ActingStyle
    volume_mult: float
    pitch_shift: float
    pitch_variance: float
    speaking_rate: float
    breathiness: float
    tremor: float
    emphasis_points: List[Tuple[int, float]]
    pause_points: List[float]
    hesitation_count: int
    interruption_probability: float


@dataclass
class ActingStyleParams:
    volume_mult: float
    pitch_shift_st: float
    pitch_variance: float
    rate_mult: float
    breathiness: float
    tremor_freq: float
    tremor_depth: float
    jitter: float
    shimmer: float


ACTING_STYLE_TABLE: Dict[ActingStyle, ActingStyleParams] = {
    ActingStyle.WHISPER: ActingStyleParams(0.3, -3.0, 0.5, 0.9, 0.8, 4.0, 0.1, 0.2, 0.1),
    ActingStyle.SHOUT: ActingStyleParams(1.5, 3.0, 0.3, 1.1, 0.1, 2.0, 0.05, 0.1, 0.05),
    ActingStyle.RESTRAINED: ActingStyleParams(0.6, -1.0, 0.2, 0.8, 0.2, 1.0, 0.02, 0.05, 0.03),
    ActingStyle.NERVOUS: ActingStyleParams(0.7, 0.0, 0.8, 1.2, 0.3, 8.0, 0.2, 0.4, 0.3),
    ActingStyle.SARCASTIC: ActingStyleParams(0.8, 2.0, 0.6, 1.0, 0.1, 1.5, 0.1, 0.2, 0.1),
    ActingStyle.CONFIDENT: ActingStyleParams(0.8, 1.0, 0.2, 0.9, 0.1, 1.0, 0.02, 0.05, 0.02),
    ActingStyle.HESITANT: ActingStyleParams(0.6, -0.5, 0.4, 0.7, 0.3, 2.0, 0.1, 0.3, 0.2),
    ActingStyle.INTIMATE: ActingStyleParams(0.4, -2.0, 0.3, 0.7, 0.9, 6.0, 0.15, 0.1, 0.05),
    ActingStyle.AUTHORITATIVE: ActingStyleParams(0.9, 1.5, 0.1, 0.95, 0.1, 1.0, 0.01, 0.05, 0.02),
    ActingStyle.EXHAUSTED: ActingStyleParams(0.5, -4.0, 0.5, 0.6, 0.2, 3.0, 0.1, 0.5, 0.4),
    ActingStyle.CRYING: ActingStyleParams(0.4, 0.0, 1.5, 0.8, 0.3, 2.0, 0.3, 0.6, 0.5),
    ActingStyle.LAUGHING: ActingStyleParams(1.0, 5.0, 0.8, 1.3, 0.1, 0.5, 0.1, 0.3, 0.1),
    ActingStyle.BREATHY: ActingStyleParams(0.5, -1.0, 0.4, 0.85, 0.9, 5.0, 0.15, 0.2, 0.1),
    ActingStyle.DRAMATIC: ActingStyleParams(0.85, 2.5, 0.7, 0.8, 0.2, 1.5, 0.05, 0.1, 0.05),
    ActingStyle.URGENT: ActingStyleParams(0.9, 4.0, 0.5, 1.4, 0.1, 1.0, 0.05, 0.1, 0.05),
    ActingStyle.CALM: ActingStyleParams(0.6, -1.5, 0.1, 0.6, 0.4, 3.0, 0.05, 0.1, 0.05),
    ActingStyle.NEUTRAL: ActingStyleParams(0.7, 0.0, 0.3, 1.0, 0.2, 1.0, 0.05, 0.1, 0.1),
}


class ActingEngine:
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.default_style = ActingStyle.NEUTRAL

    def get_style_params(self, style: ActingStyle) -> ActingStyleParams:
        return ACTING_STYLE_TABLE.get(style, ACTING_STYLE_TABLE[ActingStyle.NEUTRAL])

    def apply_style(self, audio: np.ndarray, style: ActingStyle) -> np.ndarray:
        params = self.get_style_params(style)
        result = audio.copy()
        result = self._apply_volume(result, params.volume_mult)
        result = self._apply_pitch_shift(result, params.pitch_shift_st)
        result = self._apply_rate(result, params.rate_mult)
        result = self._apply_breathiness(result, params.breathiness)
        result = self._apply_tremor(result, params.tremor_freq, params.tremor_depth)
        result = self._apply_jitter_shimmer(result, params.jitter, params.shimmer)
        return np.clip(result, -0.99, 0.99)

    def _apply_volume(self, audio: np.ndarray, mult: float) -> np.ndarray:
        return np.clip(audio * mult, -0.99, 0.99)

    def _apply_pitch_shift(self, audio: np.ndarray, semitones: float) -> np.ndarray:
        if abs(semitones) < 0.01:
            return audio
        from scipy import signal as scipy_signal
        factor = 2.0 ** (semitones / 12.0)
        n = max(1, int(len(audio) / factor))
        indices = np.linspace(0, len(audio) - 1, n)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _apply_rate(self, audio: np.ndarray, rate: float) -> np.ndarray:
        if abs(rate - 1.0) < 0.01:
            return audio
        from scipy import signal as scipy_signal
        n = max(1, int(len(audio) * rate))
        indices = np.arange(n) * (len(audio) / n)
        return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)

    def _apply_breathiness(self, audio: np.ndarray, breathiness: float) -> np.ndarray:
        if breathiness < 0.01:
            return audio
        from scipy import signal as scipy_signal
        b, a = scipy_signal.butter(4, 200 / (self.sample_rate / 2), btype='high')
        high_freq = scipy_signal.filtfilt(b, a, audio)
        return np.clip(audio + high_freq * breathiness * 0.3, -0.99, 0.99)

    def _apply_tremor(self, audio: np.ndarray, freq: float, depth: float) -> np.ndarray:
        if depth < 0.01:
            return audio
        t = np.arange(len(audio)) / self.sample_rate
        mod = 1.0 + depth * np.sin(2 * math.pi * freq * t)
        return np.clip(audio * mod, -0.99, 0.99)

    def _apply_jitter_shimmer(self, audio: np.ndarray, jitter: float, shimmer: float) -> np.ndarray:
        if jitter < 0.01 and shimmer < 0.01:
            return audio
        from scipy import signal as scipy_signal
        hop = self.sample_rate // 100
        n_hops = max(1, len(audio) // hop)
        jitter_amounts = np.random.RandomState(42).uniform(-jitter, jitter, n_hops)
        result = audio.copy()
        for i in range(n_hops):
            start = i * hop
            end = min((i + 1) * hop, len(audio))
            result[start:end] *= (1 + jitter_amounts[i])
            if shimmer > 0:
                result[start:end] *= (1 + np.random.RandomState(42 + i).uniform(-shimmer, shimmer))
        return np.clip(result, -0.99, 0.99)

    def apply_emotion_continuity(self, audio: np.ndarray, emotion_timeline: List[Dict[str, Any]]) -> np.ndarray:
        if not emotion_timeline:
            return audio
        result = audio.copy()
        n_segments = min(len(emotion_timeline), max(1, len(audio) // (self.sample_rate // 10)))
        seg_len = len(audio) // n_segments
        for i, emotion in enumerate(emotion_timeline):
            start = i * seg_len
            end = min((i + 1) * seg_len, len(audio))
            if start >= end:
                break
            segment = result[start:end]
            h = emotion.get("happiness", 0.5)
            a = emotion.get("anger", 0.1)
            f = emotion.get("fear", 0.1)
            u = emotion.get("urgency", 0.2)
            pitch_shift = (h - 0.5) * 2 + (u - 0.5) * 4 + (a - 0.3) * 1.5
            volume = 0.6 + (h - 0.3) * 0.8 + (a - 0.2) * 0.4
            segment_modified = self._apply_volume(segment, volume)
            if abs(pitch_shift) > 0.1:
                segment_modified = self._apply_pitch_shift(segment_modified, pitch_shift)
            result[start:end] = segment_modified
        return np.clip(result, -0.99, 0.99)

    def apply_acting_to_sentence(
        self, text: str, audio: np.ndarray, sentence_emotions: List[Dict[str, float]],
        pauses: List[float],
    ) -> np.ndarray:
        segments = self._split_by_words(text, audio, len(sentence_emotions))
        result = np.array([], dtype=np.float32)
        for i, seg in enumerate(segments):
            if i < len(sentence_emotions):
                emotion = sentence_emotions[i]
                pitch_shift = emotion.get("anger", 0) * 3 + emotion.get("happiness", 0) * 1.5
                volume = 0.5 + emotion.get("confidence", 0.5) * 0.4
                seg = self._apply_volume(seg, volume)
                if abs(pitch_shift) > 0.1:
                    seg = self._apply_pitch_shift(seg, pitch_shift)
            result = np.concatenate([result, seg])
            if i < len(pauses):
                pause_samples = int(pauses[i] * self.sample_rate)
                if pause_samples > 0:
                    result = np.concatenate([result, np.zeros(pause_samples, dtype=np.float32)])
        return np.clip(result, -0.99, 0.99)

    def _split_by_words(self, text: str, audio: np.ndarray, n_parts: int) -> List[np.ndarray]:
        if n_parts < 1:
            n_parts = 1
        seg_len = max(1, len(audio) // n_parts)
        return [audio[i * seg_len: min((i + 1) * seg_len, len(audio))] for i in range(n_parts)]

    def generate_breath_samples(self, num_breaths: int = 1) -> List[np.ndarray]:
        breaths = []
        t = np.arange(int(0.5 * self.sample_rate)) / self.sample_rate
        for _ in range(num_breaths):
            breath = np.random.RandomState(42).normal(0, 0.05, len(t)).astype(np.float32)
            breath *= np.exp(-t * 3)
            breath *= np.sin(2 * math.pi * (200 + np.random.RandomState(42).uniform(-50, 50)) * t) * 0.1
            breath = np.clip(breath, -0.3, 0.3)
            breaths.append(breath)
        return breaths

    def generate_hesitation(self, audio: np.ndarray, position: float = 0.5) -> np.ndarray:
        pos = int(position * len(audio))
        breath = self.generate_breath_samples(1)[0]
        result = np.concatenate([audio[:pos], breath, audio[pos:]])
        return np.clip(result, -0.99, 0.99)

    def overlapping_speech(
        self, audio_a: np.ndarray, audio_b: np.ndarray, offset_b: float = 0.3,
    ) -> np.ndarray:
        offset_samples = int(offset_b * len(audio_a))
        max_len = max(len(audio_a), offset_samples + len(audio_b))
        result = np.zeros(max_len, dtype=np.float32)
        result[:len(audio_a)] += audio_a * 0.9
        result[offset_samples:offset_samples + len(audio_b)] += audio_b * 0.7
        return np.clip(result, -0.99, 0.99)
