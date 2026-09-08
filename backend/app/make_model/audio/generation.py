"""
Unified audio generation API.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import uuid

from app.make_model.audio.architecture import (
    AudioModelInterface, GenerationRequest, GenerationResult, AudioConfig
)
from app.make_model.audio.config_loader import load_audio_config, get_default_config


class AudioGenerationPipeline:
    def __init__(self, config_path: Optional[str] = None) -> None:
        self.config = load_audio_config(config_path) if config_path else get_default_config("tiny")
        self._models: Dict[str, AudioModelInterface] = {}
        self._register_default_models()

    def _register_default_models(self) -> None:
        from app.make_model.audio.voice import VoiceGenomeEngine
        from app.make_model.audio.emotion import EmotionEngine
        from app.make_model.audio.performance import PerformanceDirector
        from app.make_model.audio.dialogue import DialogueEngine
        from app.make_model.audio.spatial import SpatialAudioDirector
        from app.make_model.audio.acoustics import RoomAcousticsEngine
        from app.make_model.audio.foley import FoleyEngine
        from app.make_model.audio.soundscape import SoundscapeEngine
        from app.make_model.audio.music import MusicIntelligence
        from app.make_model.audio.editing import AudioEditingEngine
        from app.make_model.audio.repair import AudioRepairEngine
        from app.make_model.audio.enhancement import AudioEnhancementEngine
        from app.make_model.audio.mixing import CinematicMixDirector
        models = {
            "voice": VoiceGenomeEngine(),
            "emotion": EmotionEngine(),
            "performance": PerformanceDirector(),
            "dialogue": DialogueEngine(),
            "spatial": SpatialAudioDirector(),
            "acoustics": RoomAcousticsEngine(),
            "foley": FoleyEngine(),
            "soundscape": SoundscapeEngine(),
            "music": MusicIntelligence(),
            "editing": AudioEditingEngine(),
            "repair": AudioRepairEngine(),
            "enhancement": AudioEnhancementEngine(),
            "mixing": CinematicMixDirector(),
        }
        for name, model in models.items():
            self._models[name] = model

    async def initialize(self) -> None:
        for model in self._models.values():
            await model.initialize(self.config)

    async def generate(self, model_type: str, request: GenerationRequest) -> GenerationResult:
        model = self._models.get(model_type)
        if not model:
            raise ValueError(f"Unknown model type: {model_type}")
        return await model.generate(request)

    async def synthesize_voice(self, text: str, voice_id: str, emotion: Optional[str] = None) -> GenerationResult:
        model = self._models.get("voice")
        if not model:
            raise RuntimeError("Voice model not initialized")
        return await model.synthesize(text, voice_id, emotion)

    async def generate_dialogue(self, script: List[Dict[str, str]], voices: Dict[str, str]) -> GenerationResult:
        model = self._models.get("dialogue")
        if not model:
            raise RuntimeError("Dialogue model not initialized")
        return await model.generate_dialogue(script, voices)

    async def apply_emotion(self, audio_path: str, emotion: str, intensity: float = 1.0) -> GenerationResult:
        model = self._models.get("emotion")
        if not model:
            raise RuntimeError("Emotion model not initialized")
        return await model.apply_emotion(audio_path, emotion, intensity)

    async def generate_music(self, prompt: str, duration: float, genre: str) -> GenerationResult:
        model = self._models.get("music")
        if not model:
            raise RuntimeError("Music model not initialized")
        return await model.generate_music(prompt, duration, genre)

    async def mix_tracks(self, tracks: List[Dict[str, Any]], output_format: str = "wav") -> GenerationResult:
        model = self._models.get("mixing")
        if not model:
            raise RuntimeError("Mixing model not initialized")
        return await model.mix_tracks(tracks, output_format)

    def get_model(self, model_type: str) -> Optional[AudioModelInterface]:
        return self._models.get(model_type)

    def list_models(self) -> List[str]:
        return list(self._models.keys())
