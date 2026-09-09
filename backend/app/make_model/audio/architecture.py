"""
MAKE Audio core architecture interfaces.

All audio components implement these interfaces.
No component may depend on another component's internal implementation.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from pathlib import Path
import json


class AudioModelType(str, Enum):
    VOICE = "voice"
    EMOTION = "emotion"
    PERFORMANCE = "performance"
    DIALOGUE = "dialogue"
    SPATIAL = "spatial"
    ACOUSTICS = "acoustics"
    FOLEY = "foley"
    SOUNDSCAPE = "soundscape"
    MUSIC = "music"
    EDITING = "editing"
    REPAIR = "repair"
    MIXING = "mixing"


@dataclass
class AudioConfig:
    model_id: str
    model_name: str
    version: str
    sample_rate: int
    channels: int
    bit_depth: int
    max_duration_seconds: float
    latent_dim: int
    hidden_dim: int
    num_layers: int
    num_heads: int
    ffn_dim: int
    dropout: float
    vocab_size: int
    codebook_size: int
    codebook_dim: int
    num_codebooks: int
    training: Dict[str, Any]
    inference: Dict[str, Any]
    dataset: Dict[str, Any]
    quality: Dict[str, Any]
    paths: Dict[str, str]
    description: str = ""
    hardware_requirements: Optional[Dict[str, Any]] = field(default=None)

    @classmethod
    def from_json(cls, path: str | Path) -> AudioConfig:
        with open(path, "r") as f:
            data = json.load(f)
        return cls(**data)


@dataclass
class GenerationRequest:
    prompt: str = ""
    duration_seconds: float = 5.0
    sample_rate: int = 16000
    seed: Optional[int] = None
    temperature: float = 1.0
    top_k: int = 50
    max_tokens: int = 1024
    conditioning: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    audio_path: str
    sample_rate: int
    channels: int
    duration_seconds: float
    seed: Optional[int]
    model_id: str
    model_version: str
    latency_ms: float
    provenance: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    snr_db: float
    clipping_ratio: float
    silence_ratio: float
    spectral_stability: float
    intelligibility_score: Optional[float] = None
    voice_consistency: Optional[float] = None
    timing_accuracy: Optional[float] = None
    spatial_consistency: Optional[float] = None
    artifact_score: Optional[float] = None
    overall_score: float = 0.0
    passed: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class AudioModelInterface(ABC):
    model_type: AudioModelType

    @abstractmethod
    async def initialize(self, config: AudioConfig) -> None:
        raise NotImplementedError

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def evaluate_quality(self, audio_path: str) -> QualityReport:
        raise NotImplementedError

    @abstractmethod
    async def save_checkpoint(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def load_checkpoint(self, path: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_provenance(self) -> Dict[str, Any]:
        raise NotImplementedError


class VoiceModelInterface(AudioModelInterface):
    model_type = AudioModelType.VOICE

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, emotion: Optional[str] = None) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def clone_voice(self, reference_audio_path: str, voice_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class EmotionModelInterface(AudioModelInterface):
    model_type = AudioModelType.EMOTION

    @abstractmethod
    async def apply_emotion(self, audio_path: str, emotion: str, intensity: float = 1.0) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def blend_emotions(self, audio_path: str, emotions: List[str], weights: List[float]) -> GenerationResult:
        raise NotImplementedError


class PerformanceModelInterface(AudioModelInterface):
    model_type = AudioModelType.PERFORMANCE

    @abstractmethod
    async def adjust_performance(self, audio_path: str, parameters: Dict[str, Any]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def add_pauses(self, audio_path: str, pause_positions: List[float]) -> GenerationResult:
        raise NotImplementedError


class DialogueModelInterface(AudioModelInterface):
    model_type = AudioModelType.DIALOGUE

    @abstractmethod
    async def generate_dialogue(self, script: List[Dict[str, str]], voices: Dict[str, str]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def repair_dialogue(self, audio_path: str, transcript: str) -> GenerationResult:
        raise NotImplementedError


class SpatialModelInterface(AudioModelInterface):
    model_type = AudioModelType.SPATIAL

    @abstractmethod
    async def spatialize(self, audio_path: str, position: Dict[str, float]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def create_spatial_scene(self, sources: List[Dict[str, Any]], listener: Dict[str, float]) -> GenerationResult:
        raise NotImplementedError


class AcousticsModelInterface(AudioModelInterface):
    model_type = AudioModelType.ACOUSTICS

    @abstractmethod
    async def apply_room_acoustics(self, audio_path: str, room_params: Dict[str, Any]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def estimate_room(self, audio_path: str) -> Dict[str, Any]:
        raise NotImplementedError


class FoleyModelInterface(AudioModelInterface):
    model_type = AudioModelType.FOLEY

    @abstractmethod
    async def generate_foley(self, event_type: str, timing: float, metadata: Dict[str, Any]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def sync_foley(self, video_path: str, foley_events: List[Dict[str, Any]]) -> GenerationResult:
        raise NotImplementedError


class SoundscapeModelInterface(AudioModelInterface):
    model_type = AudioModelType.SOUNDSCAPE

    @abstractmethod
    async def generate_soundscape(self, environment: str, duration: float, parameters: Dict[str, Any]) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def blend_soundscape(self, base_audio: str, overlay_audio: str, blend_ratio: float = 0.5) -> GenerationResult:
        raise NotImplementedError


class MusicModelInterface(AudioModelInterface):
    model_type = AudioModelType.MUSIC

    @abstractmethod
    async def generate_music(self, prompt: str, duration: float, genre: str) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def arrange_music(self, stems: Dict[str, str], structure: Dict[str, Any]) -> GenerationResult:
        raise NotImplementedError


class EditingModelInterface(AudioModelInterface):
    model_type = AudioModelType.EDITING

    @abstractmethod
    async def replace_segment(self, audio_path: str, start: float, end: float, replacement: str) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def adjust_timing(self, audio_path: str, stretch_factor: float) -> GenerationResult:
        raise NotImplementedError


class RepairModelInterface(AudioModelInterface):
    model_type = AudioModelType.REPAIR

    @abstractmethod
    async def remove_noise(self, audio_path: str, noise_profile: Optional[str] = None) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def dereverberate(self, audio_path: str) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def repair_clipping(self, audio_path: str) -> GenerationResult:
        raise NotImplementedError


class MixingModelInterface(AudioModelInterface):
    model_type = AudioModelType.MIXING

    @abstractmethod
    async def mix_tracks(self, tracks: List[Dict[str, Any]], output_format: str = "wav") -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def auto_duck(self, background_path: str, foreground_path: str, threshold: float = -20.0) -> GenerationResult:
        raise NotImplementedError
