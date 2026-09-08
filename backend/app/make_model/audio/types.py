"""
MAKE Audio types and shared utilities.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from pathlib import Path
import time


class AudioFormat(str, Enum):
    WAV = "wav"
    FLAC = "flac"
    MP3 = "mp3"
    OGG = "ogg"


@dataclass
class AudioTensor:
    data: Any  # numpy array
    sample_rate: int
    channels: int
    duration_seconds: float
    format: AudioFormat = AudioFormat.WAV

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.data.shape

    @property
    def dtype(self):
        return self.data.dtype


@dataclass
class VoiceGenome:
    voice_id: str
    timbre: Dict[str, float] = field(default_factory=dict)
    pitch_mean: float = 0.0
    pitch_std: float = 0.0
    resonance: float = 0.0
    articulation: float = 0.0
    speaking_rate: float = 0.0
    breath_characteristics: Dict[str, float] = field(default_factory=dict)
    dynamic_range: float = 0.0
    emotional_tendencies: Dict[str, float] = field(default_factory=dict)
    accent_characteristics: Dict[str, float] = field(default_factory=dict)
    vocal_texture: Dict[str, float] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voice_id": self.voice_id,
            "timbre": self.timbre,
            "pitch_mean": self.pitch_mean,
            "pitch_std": self.pitch_std,
            "resonance": self.resonance,
            "articulation": self.articulation,
            "speaking_rate": self.speaking_rate,
            "breath_characteristics": self.breath_characteristics,
            "dynamic_range": self.dynamic_range,
            "emotional_tendencies": self.emotional_tendencies,
            "accent_characteristics": self.accent_characteristics,
            "vocal_texture": self.vocal_texture,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class EmotionVector:
    happiness: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    calm: float = 0.0
    excitement: float = 0.0
    tension: float = 0.0
    confidence: float = 0.0
    intimacy: float = 0.0
    exhaustion: float = 0.0
    surprise: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> EmotionVector:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def blend(self, other: EmotionVector, weight: float = 0.5) -> EmotionVector:
        result = EmotionVector()
        for key in result.__dataclass_fields__:
            self_val = getattr(self, key, 0.0)
            other_val = getattr(other, key, 0.0)
            setattr(result, key, self_val * (1 - weight) + other_val * weight)
        return result


@dataclass
class PerformanceParameters:
    emphasis: List[Tuple[float, float]] = field(default_factory=list)
    pauses: List[Tuple[float, float]] = field(default_factory=list)
    speed: float = 1.0
    volume: float = 1.0
    pitch_shift: float = 0.0
    hesitation: List[float] = field(default_factory=list)
    breath_positions: List[float] = field(default_factory=list)
    dramatic_timing: List[Tuple[float, float]] = field(default_factory=list)


@dataclass
class SpatialPosition:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    distance: float = 1.0
    elevation: float = 0.0


@dataclass
class RoomAcoustics:
    room_size: str = "medium"
    materials: Dict[str, float] = field(default_factory=dict)
    absorption: float = 0.3
    reflection: float = 0.5
    rt60: float = 0.3
    source_distance: float = 1.0


@dataclass
class ProvenanceRecord:
    artifact_id: str
    model_id: str
    model_version: str
    generation_parameters: Dict[str, Any]
    source_inputs: List[str]
    transformations: List[Dict[str, Any]]
    timestamps: List[str]
    content_hash: str
    dataset_lineage: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
