"""MAKE Audio — Voice Genome.

Represents a voice as structured, editable parameters rather than a raw
waveform.  Every downstream synthesis module reads these parameters.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple, List
from enum import Enum


class VocalQuality(str, Enum):
    BREATHY = "breathy"
    CLEAR = "clear"
    HOARSE = "hoarse"
    SMOOTH = "smooth"
    RASPY = "raspy"


class Accent(str, Enum):
    GENERAL_AMERICAN = "general_american"
    BRITISH_RP = "british_rp"
    AUSTRALIAN = "australian"
    INDIAN_ENGLISH = "indian_english"


@dataclass
class VoiceGenome:
    name: str = "default"
    gender: str = "neutral"
    sample_rate: int = 22050

    timbre: Dict[str, float] = field(default_factory=lambda: {
        "brightness": 0.5, "warmth": 0.5, "roughness": 0.1, "breathiness": 0.2,
    })
    pitch_mean: float = 120.0
    pitch_range: float = 40.0
    formants: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "F1": (500.0, 0.0), "F2": (1500.0, 0.0), "F3": (2500.0, 0.0),
    })
    articulation: Dict[str, float] = field(default_factory=lambda: {
        "clarity": 0.8, "speed": 1.0, "emphasis": 0.5,
    })
    breath_characteristics: Dict[str, float] = field(default_factory=lambda: {
        "inhalation": 0.1, "exhalation": 0.2, "breathiness": 0.2,
    })
    dynamic_range: Tuple[float, float] = (0.05, 0.8)
    emotional_tendencies: Dict[str, float] = field(default_factory=dict)
    accent: Accent = Accent.GENERAL_AMERICAN
    vocal_quality: VocalQuality = VocalQuality.CLEAR
    vocal_texture: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict
        d = asdict(self)
        d["accent"] = self.accent.value
        d["vocal_quality"] = self.vocal_quality.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "VoiceGenome":
        d = d.copy()
        if "accent" in d and isinstance(d["accent"], str):
            d["accent"] = Accent(d["accent"])
        if "vocal_quality" in d and isinstance(d["vocal_quality"], str):
            d["vocal_quality"] = VocalQuality(d["vocal_quality"])
        return cls(**d)

    def fingerprint(self) -> str:
        import hashlib, json
        d = self.to_dict()
        raw = json.dumps(d, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def with_emotion(self, emotion_state: Dict[str, float]) -> "VoiceGenome":
        new = copy.deepcopy(self)
        h = emotion_state.get("happiness", 0)
        s = emotion_state.get("sadness", 0)
        a = emotion_state.get("anger", 0)
        f = emotion_state.get("fear", 0)
        c = emotion_state.get("calm", 0)
        ex = emotion_state.get("excitement", 0)

        new.pitch_mean += (h + ex) * 25 - s * 30 + f * 35 - c * 12
        new.timbre["brightness"] = max(0, min(1, new.timbre["brightness"] + (h + ex) * 0.3 - s * 0.3))
        new.breath_characteristics["breathiness"] = min(1.0, new.breath_characteristics["breathiness"] + f * 0.4 + h * 0.15)
        lo, hi = new.dynamic_range
        new.dynamic_range = (max(0.01, lo), min(1.0, hi + a * 0.2))
        for key in new.formants:
            freq, gain = new.formants[key]
            new.formants[key] = (freq * (1 - a * 0.08 + h * 0.05), gain + (h - s) * 2)
        if c > 0.5:
            new.vocal_quality = VocalQuality.SMOOTH
        return new

    def with_performance(self, perf: Dict[str, Any]) -> "VoiceGenome":
        new = copy.deepcopy(self)
        if "speed" in perf:
            new.articulation["speed"] = perf["speed"]
        if "emphasis" in perf:
            new.articulation["emphasis"] = perf["emphasis"]
        if "pitch_shift" in perf:
            new.pitch_mean += perf["pitch_shift"]
        if "volume" in perf:
            lo, hi = new.dynamic_range
            vol = perf["volume"]
            new.dynamic_range = (lo * vol, hi * vol)
        return new

    def describe(self) -> str:
        return (f"Voice({self.name}, {self.gender}, SR={self.sample_rate}, "
                f"pitch={self.pitch_mean:.0f}Hz, accent={self.accent.value}, "
                f"quality={self.vocal_quality.value})")
