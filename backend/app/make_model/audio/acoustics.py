"""
Room acoustics engine - generate appropriate acoustic characteristics.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal

from app.make_model.audio.architecture import AcousticsModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.types import RoomAcoustics
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class RoomAcousticsEngine(AcousticsModelInterface):
    model_type = "acoustics"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
        self._room_presets = {
            "small_room": {"rt60": 0.2, "absorption": 0.4, "reflection": 0.3},
            "medium_room": {"rt60": 0.4, "absorption": 0.3, "reflection": 0.5},
            "large_hall": {"rt60": 1.2, "absorption": 0.15, "reflection": 0.7},
            "outdoor": {"rt60": 0.05, "absorption": 0.9, "reflection": 0.1},
            "cathedral": {"rt60": 3.0, "absorption": 0.1, "reflection": 0.8},
        }
        self._model: Optional[TinyAudioModel] = None
        self._vocoder: Optional[TinyVocoder] = None

    async def initialize(self, config: AudioConfig) -> None:
        self.config = config
        self._model = TinyAudioModel(config, seed=config.training.get("seed", 42))
        self._vocoder = TinyVocoder(sample_rate=config.sample_rate)

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        return GenerationResult(
            audio_path="",
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=request.seed,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"type": "acoustics_placeholder"},
        )

    async def apply_room_acoustics(self, audio_path: str, room_params: Dict[str, Any]) -> GenerationResult:
        if not self._model or not self._vocoder:
            raise RuntimeError("RoomAcousticsEngine not initialized")
        room = RoomAcoustics(**room_params)
        params = self._model.forward("acoustics", "room", None)
        audio = self._vocoder.synthesize(params, 1.0)
        audio = self._apply_reverb(audio, self.config.sample_rate, room.rt60)
        output_path = f"/tmp/acoustics_{int(time.time())}.wav"
        wavfile.write(output_path, self.config.sample_rate, (np.clip(audio, -0.99, 0.99) * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=1.0,
            seed=None,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={"room": room.__dict__, "type": "room_acoustics", "model": "tiny_numpy"},
        )

    def _apply_reverb(self, audio: np.ndarray, sr: int, rt60: float) -> np.ndarray:
        delay = int(sr * 0.02)
        decay = np.exp(-delay / max(rt60, 0.01) / sr)
        reverb = np.zeros_like(audio)
        for d in range(1, 8):
            shifted = np.roll(audio, d * delay)
            reverb += shifted * (decay ** d) * 0.3
        return audio + reverb

    async def estimate_room(self, audio_path: str) -> Dict[str, Any]:
        return {"estimated_rt60": 0.3, "estimated_absorption": 0.3, "confidence": 0.5}

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        pass

    async def load_checkpoint(self, path: str) -> None:
        pass

    def get_provenance(self) -> Dict[str, Any]:
        return {"model_type": "acoustics", "room_presets": list(self._room_presets.keys())}
