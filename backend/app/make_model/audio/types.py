"""
Audio type definitions for MAKE Audio V2.

Central type definitions used across all audio components.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np


@dataclass
class AudioTensor:
    """Audio tensor with metadata."""
    data: np.ndarray
    sample_rate: int
    channels: int
    duration_seconds: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VoiceGenome:
    """Voice identity genome with deterministic embedding."""
    voice_id: str
    timbre: Dict[str, float]
    pitch_mean: float
    pitch_std: float
    resonance: float
    articulation: float
    speaking_rate: float
    breath_characteristics: Dict[str, float]
    dynamic_range: float
    emotional_tendencies: Dict[str, float]
    accent_characteristics: Dict[str, float]
    vocal_texture: Dict[str, float]

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
        }


@dataclass
class EmotionVector:
    """Continuous emotion control vector."""
    happiness: float = 0.0
    sadness: float = 0.0
    anger: float = 0.0
    fear: float = 0.0
    surprise: float = 0.0
    disgust: float = 0.0
    excitement: float = 0.0
    calm: float = 0.0
    tension: float = 0.0
    confidence: float = 0.0
    intimacy: float = 0.0
    exhaustion: float = 0.0


@dataclass
class ProvenanceRecord:
    """Immutable record of audio generation lineage."""
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


@dataclass
class RoomAcoustics:
    """Room acoustics parameters."""
    room_type: str
    rt60: float
    absorption: Dict[str, float]
    reflections: List[Dict[str, Any]]
    volume: float
    surface_area: float


@dataclass
class PerformanceParameters:
    """Performance/acting parameters."""
    pitch_hz: float = 120.0
    rate: float = 1.0
    volume: float = 1.0
    energy: float = 0.5
    breathiness: float = 0.0
    tremor: float = 0.0
    whisper: float = 0.0
    shout: float = 0.0
    hesitation: float = 0.0
    emphasis: float = 0.0
    pause: float = 0.0


@dataclass
class FoleyEvent:
    """Foley sound event."""
    event_type: str
    timing: float
    material: str
    surface: str
    intensity: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpatialPosition:
    """3D spatial position."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    distance: float = 1.0
    elevation: float = 0.0
    azimuth: float = 0.0