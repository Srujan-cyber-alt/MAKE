"""
MAKE Audio Intelligence & Generation Subsystem.

CPU-first, MAKE-native audio architecture.
No third-party AI generation APIs.
"""

from app.make_model.audio.architecture import (
    AudioModelInterface,
    VoiceModelInterface,
    EmotionModelInterface,
    PerformanceModelInterface,
    DialogueModelInterface,
    SpatialModelInterface,
    AcousticsModelInterface,
    FoleyModelInterface,
    SoundscapeModelInterface,
    MusicModelInterface,
    EditingModelInterface,
    RepairModelInterface,
    MixingModelInterface,
)
from app.make_model.audio.config_loader import load_audio_config, AudioConfig

__all__ = [
    "AudioModelInterface",
    "VoiceModelInterface",
    "EmotionModelInterface",
    "PerformanceModelInterface",
    "DialogueModelInterface",
    "SpatialModelInterface",
    "AcousticsModelInterface",
    "FoleyModelInterface",
    "SoundscapeModelInterface",
    "MusicModelInterface",
    "EditingModelInterface",
    "RepairModelInterface",
    "MixingModelInterface",
    "load_audio_config",
    "AudioConfig",
]
