"""
Spatial audio director - stereo, binaural, surround-ready, object positioning.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import SpatialModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class SpatialAudioDirector(SpatialModelInterface):
    model_type = "spatial"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
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
            provenance={"type": "spatial_placeholder"},
        )

    async def spatialize(self, audio_path: str, position: Dict[str, float]) -> GenerationResult:
        if not self._model or not self._vocoder:
            raise RuntimeError("SpatialAudioDirector not initialized")
        params = self._model.forward("spatial", "listener", None)
        audio = self._vocoder.synthesize(params, 1.0)
        x, y, z = position.get("x", 0.0), position.get("y", 0.0), position.get("z", 0.0)
        distance = float(np.sqrt(x**2 + y**2 + z**2))
        azimuth = float(np.degrees(np.arctan2(y, x)))
        left_gain = max(0.0, 1.0 - distance * 0.3) * (1.0 if azimuth < 0 else 0.7)
        right_gain = max(0.0, 1.0 - distance * 0.3) * (1.0 if azimuth >= 0 else 0.7)
        stereo = np.stack([audio * left_gain, audio * right_gain], axis=-1)
        output_path = f"/tmp/spatial_{int(time.time())}.wav"
        wavfile.write(output_path, self.config.sample_rate, (np.clip(stereo, -0.99, 0.99) * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=2,
            duration_seconds=1.0,
            seed=None,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={
                "position": position,
                "distance": distance,
                "azimuth": azimuth,
                "type": "spatialization",
                "model": "tiny_numpy",
            },
        )

    async def create_spatial_scene(self, sources: List[Dict[str, Any]], listener: Dict[str, float]) -> GenerationResult:
        output_path = f"/tmp/spatial_scene_{int(time.time())}.wav"
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"num_sources": len(sources), "listener": listener, "type": "spatial_scene"},
        )

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        pass

    async def load_checkpoint(self, path: str) -> None:
        pass

    def get_provenance(self) -> Dict[str, Any]:
        return {"model_type": "spatial"}
