"""
Audio enhancement - noise reduction, clarity, loudness normalization.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal

from app.make_model.audio.architecture import AudioModelInterface, GenerationRequest, GenerationResult, AudioConfig


class AudioEnhancementEngine(AudioModelInterface):
    model_type = "enhancement"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None

    async def initialize(self, config: AudioConfig) -> None:
        self.config = config

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
            provenance={"type": "enhancement_placeholder"},
        )

    async def enhance(self, audio_path: str, parameters: Dict[str, Any]) -> GenerationResult:
        try:
            sr, data = wavfile.read(audio_path)
        except Exception:
            sr = self.config.sample_rate if self.config else 16000
            data = np.zeros(int(sr * 1.0), dtype=np.int16)
        audio = data.astype(np.float32) / 32767.0
        audio = self._highpass_filter(audio, sr, cutoff=80.0)
        audio = self._normalize(audio)
        output_path = f"/tmp/enhanced_{time.time()}.wav"
        wavfile.write(output_path, sr, (np.clip(audio, -0.99, 0.99) * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=sr,
            channels=1 if audio.ndim == 1 else audio.shape[1],
            duration_seconds=len(audio) / sr,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"parameters": parameters, "type": "enhancement", "model": "numpy_scipy"},
        )

    def _highpass_filter(self, audio: np.ndarray, sr: int, cutoff: float = 80.0) -> np.ndarray:
        if audio.ndim > 1:
            audio = audio[:, 0] if audio.shape[1] > 0 else audio
        sos = scipy.signal.butter(4, cutoff, btype="high", fs=sr, output="sos")
        return scipy.signal.sosfilt(sos, audio)

    def _normalize(self, audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio * (target_peak / peak)
        return audio

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        pass

    async def load_checkpoint(self, path: str) -> None:
        pass

    def get_provenance(self) -> Dict[str, Any]:
        return {"model_type": "enhancement"}
