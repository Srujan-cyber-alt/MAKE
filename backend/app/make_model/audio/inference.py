"""
CPU-first audio inference engine.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import hashlib
import numpy as np
from pathlib import Path

from app.make_model.audio.architecture import AudioConfig, GenerationRequest, GenerationResult
from app.make_model.audio.config_loader import load_audio_config
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class AudioInferenceEngine:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or load_audio_config("tiny")
        self._loaded = False
        self._provenance_log: List[Dict[str, Any]] = []
        self._model: Optional[TinyAudioModel] = None
        self._vocoder: Optional[TinyVocoder] = None

    async def initialize(self, config_path: Optional[str] = None) -> None:
        if config_path:
            self.config = load_audio_config(config_path)
        seed = self.config.training.get("seed", 42)
        self._model = TinyAudioModel(self.config, seed=seed)
        self._vocoder = TinyVocoder(sample_rate=self.config.sample_rate)
        self._loaded = True

    async def infer(self, request: GenerationRequest) -> GenerationResult:
        if not self._loaded:
            await self.initialize()
        start = time.time()
        if not self._model or not self._vocoder:
            raise RuntimeError("Inference engine not initialized")
        text = request.prompt or "silence"
        speaker = request.conditioning.get("speaker", "default")
        emotion = request.conditioning.get("emotion")
        duration = min(request.duration_seconds, self.config.max_duration_seconds)
        seed = request.seed if request.seed is not None else self.config.training.get("seed", 42)
        if seed != self._model.seed:
            self._model = TinyAudioModel(self.config, seed=seed)
        params = self._model.forward(text, speaker, emotion)
        audio = self._vocoder.synthesize(params, duration)
        output_path = f"/tmp/infer_{int(time.time())}_{seed}.wav"
        import scipy.io.wavfile as wavfile
        wavfile.write(output_path, self.config.sample_rate, (audio * 32767).astype(np.int16))
        latency = (time.time() - start) * 1000
        result = GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=len(audio) / self.config.sample_rate,
            seed=request.seed,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=latency,
            provenance={"type": "inference", "model": "tiny_numpy"},
        )
        self._provenance_log.append(result.provenance)
        return result

    def get_provenance_log(self) -> List[Dict[str, Any]]:
        return list(self._provenance_log)
