"""
Voice genome and voice identity memory.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import hashlib
import time
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import (
    VoiceModelInterface, GenerationRequest, GenerationResult, AudioConfig
)
from app.make_model.audio.types import VoiceGenome, AudioTensor
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class VoiceGenomeEngine(VoiceModelInterface):
    model_type = "voice"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
        self._voice_registry: Dict[str, VoiceGenome] = {}
        self._initialized = False
        self._model: Optional[TinyAudioModel] = None
        self._vocoder: Optional[TinyVocoder] = None

    async def initialize(self, config: AudioConfig) -> None:
        self.config = config
        self._model = TinyAudioModel(config, seed=config.training.get("seed", 42))
        self._vocoder = TinyVocoder(sample_rate=config.sample_rate)
        self._initialized = True

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self._initialized:
            raise RuntimeError("VoiceGenomeEngine not initialized")
        voice_id = request.conditioning.get("voice_id", "default")
        if voice_id not in self._voice_registry:
            genome = self._create_default_genome(voice_id)
            self._voice_registry[voice_id] = genome
        emotion = request.conditioning.get("emotion")
        duration = min(request.duration_seconds, self.config.max_duration_seconds if self.config else 10.0)
        seed = request.seed if request.seed is not None else (self.config.training.get("seed", 42) if self.config else 42)
        if self._model and self._vocoder:
            params = self._model.forward(request.prompt, voice_id, emotion)
            audio = self._vocoder.synthesize(params, duration)
        else:
            audio = self._synthesize_reference(request)
        output_path = f"/tmp/voice_{voice_id}_{int(time.time())}.wav"
        self._save_audio(audio, output_path)
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=len(audio) / self.config.sample_rate,
            seed=request.seed,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={"voice_id": voice_id, "type": "voice_synthesis", "model": "tiny_numpy"},
        )

    async def synthesize(self, text: str, voice_id: str, emotion: Optional[str] = None) -> GenerationResult:
        request = GenerationRequest(
            prompt=text,
            conditioning={"voice_id": voice_id, "emotion": emotion},
        )
        return await self.generate(request)

    async def clone_voice(self, reference_audio_path: str, voice_id: str) -> Dict[str, Any]:
        audio = self._load_audio(reference_audio_path)
        genome = self._extract_genome(audio, voice_id)
        self._voice_registry[voice_id] = genome
        return genome.to_dict()

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        if self._model:
            self._model.save_checkpoint(path)
        else:
            import json
            data = {vid: g.to_dict() for vid, g in self._voice_registry.items()}
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

    async def load_checkpoint(self, path: str) -> None:
        if self._model and path.endswith(".npz"):
            self._model.load_checkpoint(path)
        else:
            import json
            with open(path, "r") as f:
                data = json.load(f)
            self._voice_registry = {vid: VoiceGenome(**g) for vid, g in data.items()}

    def get_provenance(self) -> Dict[str, Any]:
        return {
            "model_type": "voice",
            "registered_voices": list(self._voice_registry.keys()),
            "model_id": self.config.model_id if self.config else None,
        }

    def get_voice(self, voice_id: str) -> Optional[VoiceGenome]:
        return self._voice_registry.get(voice_id)

    def _create_default_genome(self, voice_id: str) -> VoiceGenome:
        return VoiceGenome(
            voice_id=voice_id,
            timbre={"spectral_centroid": 0.5, "spectral_rolloff": 0.5},
            pitch_mean=220.0,
            pitch_std=20.0,
            resonance=0.5,
            articulation=0.5,
            speaking_rate=1.0,
            breath_characteristics={"inhale_duration": 0.3, "exhale_duration": 0.5},
            dynamic_range=30.0,
            emotional_tendencies={"neutral": 1.0},
            accent_characteristics={"formant_f1": 0.5, "formant_f2": 0.5},
            vocal_texture={"jitter": 0.01, "shimmer": 0.02},
        )

    def _synthesize_reference(self, request: GenerationRequest) -> np.ndarray:
        sr = self.config.sample_rate if self.config else 16000
        duration = min(request.duration_seconds, self.config.max_duration_seconds if self.config else 10.0)
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        freq = 220.0
        audio = 0.3 * np.sin(2 * np.pi * freq * t)
        audio = audio.astype(np.float32)
        return audio

    def _extract_genome(self, audio: np.ndarray, voice_id: str) -> VoiceGenome:
        return self._create_default_genome(voice_id)

    def _save_audio(self, audio: np.ndarray, path: str) -> None:
        audio_int = (audio * 32767).astype(np.int16)
        wavfile.write(path, self.config.sample_rate if self.config else 16000, audio_int)

    def _load_audio(self, path: str) -> np.ndarray:
        sr, data = wavfile.read(path)
        return data.astype(np.float32) / 32767.0
