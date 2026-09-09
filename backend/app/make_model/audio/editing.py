"""
Audio editing - word replacement, timing adjustment, emphasis modification.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import EditingModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class AudioEditingEngine(EditingModelInterface):
    model_type = "editing"

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
            provenance={"type": "editing_placeholder"},
        )

    async def replace_segment(self, audio_path: str, start: float, end: float, replacement: str) -> GenerationResult:
        if not self._model or not self._vocoder:
            raise RuntimeError("AudioEditingEngine not initialized")
        duration = max(0.1, end - start)
        params = self._model.forward(replacement, "editor", None)
        audio = self._vocoder.synthesize(params, duration)
        output_path = f"/tmp/edited_{int(time.time())}.wav"
        wavfile.write(output_path, self.config.sample_rate, (audio * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=duration,
            seed=None,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={
                "start": start,
                "end": end,
                "replacement": replacement,
                "type": "segment_replacement",
                "model": "tiny_numpy",
            },
        )

    async def adjust_timing(self, audio_path: str, stretch_factor: float) -> GenerationResult:
        output_path = audio_path.replace(".wav", "_timing.wav")
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"stretch_factor": stretch_factor, "type": "timing_adjustment"},
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
        return {"model_type": "editing"}
