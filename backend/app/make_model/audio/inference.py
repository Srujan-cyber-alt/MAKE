"""
CPU-first audio inference engine.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import hashlib
from pathlib import Path

from app.make_model.audio.architecture import AudioConfig, GenerationRequest, GenerationResult
from app.make_model.audio.config_loader import load_audio_config


class AudioInferenceEngine:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config or load_audio_config("tiny")
        self._loaded = False
        self._provenance_log: List[Dict[str, Any]] = []

    async def initialize(self, config_path: Optional[str] = None) -> None:
        if config_path:
            self.config = load_audio_config(config_path)
        self._loaded = True

    async def infer(self, request: GenerationRequest) -> GenerationResult:
        if not self._loaded:
            await self.initialize()
        start = time.time()
        result = GenerationResult(
            audio_path="",
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=0.0,
            seed=request.seed,
            model_id=self.config.model_id,
            model_version=self.config.version,
            latency_ms=0.0,
            provenance={"type": "inference_placeholder"},
        )
        result.latency_ms = (time.time() - start) * 1000
        self._provenance_log.append(result.provenance)
        return result

    def get_provenance_log(self) -> List[Dict[str, Any]]:
        return list(self._provenance_log)
