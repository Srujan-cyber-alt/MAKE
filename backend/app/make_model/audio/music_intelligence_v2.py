"""
Music intelligence V2.

Captures tempo, meter, key, harmony, melody, rhythm, instrumentation for
deterministic music generation and analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class Meter(str, Enum):
    FOUR_FOUR = "4/4"
    THREE_FOUR = "3/4"
    SIX_EIGHT = "6/8"
    FIVE_FOUR = "5/4"
    SEVEN_EIGHT = "7/8"


class Key(str, Enum):
    C_MAJOR = "C"
    G_MAJOR = "G"
    D_MAJOR = "D"
    A_MAJOR = "A"
    E_MAJOR = "E"
    B_MAJOR = "B"
    F_SHARP_MAJOR = "F#"
    A_MINOR = "Am"
    E_MINOR = "Em"
    B_MINOR = "Bm"
    F_SHARP_MINOR = "F#m"
    C_SHARP_MINOR = "C#m"
    G_SHARP_MINOR = "G#m"
    D_SHARP_MINOR = "D#m"
    A_SHARP_MINOR = "A#m"


@dataclass
class Harmony:
    """Chord progression description."""

    progression: List[str] = field(default_factory=list)
    tension: float = 0.5
    resolution: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progression": list(self.progression),
            "tension": self.tension,
            "resolution": self.resolution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Harmony":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class Melody:
    """Melodic contour description."""

    motif: List[int] = field(default_factory=list)
    range_semitones: int = 12
    movement: str = "conjunct"  # conjunct | disjunct
    repetition: float = 0.3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motif": list(self.motif),
            "range_semitones": self.range_semitones,
            "movement": self.movement,
            "repetition": self.repetition,
        }


@dataclass
class RhythmPattern:
    """Rhythmic pattern description."""

    pattern: List[float] = field(default_factory=list)
    syncopation: float = 0.3
    swing: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": list(self.pattern),
            "syncopation": self.syncopation,
            "swing": self.swing,
        }


@dataclass
class Instrumentation:
    """Instrument assignment."""

    instruments: List[str] = field(default_factory=list)
    velocity_map: Dict[str, float] = field(default_factory=dict)
    pan_map: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruments": list(self.instruments),
            "velocity_map": dict(self.velocity_map),
            "pan_map": dict(self.pan_map),
        }


@dataclass
class MusicIntelligence:
    """High-level musical description."""

    tempo: float = 120.0
    meter: Meter = Meter.FOUR_FOUR
    key: Key = Key.C_MAJOR
    harmony: Harmony = field(default_factory=Harmony)
    melody: Melody = field(default_factory=Melody)
    rhythm: RhythmPattern = field(default_factory=RhythmPattern)
    instrumentation: Instrumentation = field(default_factory=Instrumentation)
    genre: str = "ambient"
    energy: float = 0.5
    duration: float = 8.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tempo": self.tempo,
            "meter": self.meter.value,
            "key": self.key.value,
            "harmony": self.harmony.to_dict(),
            "melody": self.melody.to_dict(),
            "rhythm": self.rhythm.to_dict(),
            "instrumentation": self.instrumentation.to_dict(),
            "genre": self.genre,
            "energy": self.energy,
            "duration": self.duration,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicIntelligence":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "meter" in filtered and not isinstance(filtered["meter"], Meter):
            filtered["meter"] = Meter(filtered["meter"])
        if "key" in filtered and not isinstance(filtered["key"], Key):
            filtered["key"] = Key(filtered["key"])
        if "harmony" in filtered and isinstance(filtered["harmony"], dict):
            filtered["harmony"] = Harmony.from_dict(filtered["harmony"])
        if "melody" in filtered and isinstance(filtered["melody"], dict):
            filtered["melody"] = Melody.from_dict(filtered["melody"]) if hasattr(Melody, "from_dict") else Melody(**filtered["melody"])
        if "rhythm" in filtered and isinstance(filtered["rhythm"], dict):
            filtered["rhythm"] = RhythmPattern(**filtered["rhythm"])
        if "instrumentation" in filtered and isinstance(filtered["instrumentation"], dict):
            filtered["instrumentation"] = Instrumentation(**filtered["instrumentation"])
        return cls(**filtered)

    def beat_duration(self) -> float:
        return 60.0 / max(1.0, self.tempo)

    def bars(self) -> int:
        beat = self.beat_duration()
        beats_per_bar = int(self.meter.value.split("/")[0])
        return max(1, int(self.duration / (beat * beats_per_bar)))

    def midi_notes(self) -> List[int]:
        """Return a simple diatonic scale based on the key."""
        base = {"C": 60, "G": 62, "D": 64, "A": 65, "E": 67, "B": 71, "F#": 66}
        root = base.get(self.key.value, 60)
        if self.key.value.endswith("m"):
            scale = [0, 2, 3, 5, 7, 8, 10]
        else:
            scale = [0, 2, 4, 5, 7, 9, 11]
        return [root + step for step in scale]