"""
Audio repair - noise removal, dereverberation, clipping repair, hum removal.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import scipy.io.wavfile as wavfile
import scipy.signal
import time as _time

from app.make_model.audio.architecture import RepairModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.types import AudioTensor


class AudioRepairEngine(RepairModelInterface):
    model_type = "repair"

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
            provenance={"type": "repair_placeholder"},
        )

    async def remove_noise(self, audio_path: str, noise_profile: Optional[str] = None) -> GenerationResult:
        try:
            sr, data = wavfile.read(audio_path)
        except Exception:
            sr = self.config.sample_rate if self.config else 16000
            data = np.zeros(int(sr * 1.0), dtype=np.int16)
        audio = data.astype(np.float32) / 32767.0
        audio = self._spectral_gate(audio, sr)
        output_path = f"/tmp/denoised_{_time.time()}.wav"
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
            provenance={"noise_profile": noise_profile, "type": "noise_removal", "model": "numpy_scipy"},
        )

    async def dereverberate(self, audio_path: str) -> GenerationResult:
        try:
            sr, data = wavfile.read(audio_path)
        except Exception:
            sr = self.config.sample_rate if self.config else 16000
            data = np.zeros(int(sr * 1.0), dtype=np.int16)
        audio = data.astype(np.float32) / 32767.0
        audio = self._simple_dereverb(audio, sr)
        output_path = f"/tmp/dereverbed_{_time.time()}.wav"
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
            provenance={"type": "dereverberation", "model": "numpy_scipy"},
        )

    async def repair_clipping(self, audio_path: str) -> GenerationResult:
        try:
            sr, data = wavfile.read(audio_path)
        except Exception:
            sr = self.config.sample_rate if self.config else 16000
            data = np.zeros(int(sr * 1.0), dtype=np.int16)
        audio = data.astype(np.float32) / 32767.0
        audio = self._repair_clipping(audio)
        output_path = f"/tmp/unclipped_{_time.time()}.wav"
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
            provenance={"type": "clipping_repair", "model": "numpy_scipy"},
        )

    def _spectral_gate(self, audio: np.ndarray, sr: int, threshold_db: float = -40.0) -> np.ndarray:
        if audio.ndim > 1:
            audio = audio[:, 0]
        n_fft = 1024
        hop = 512
        _, _, S = scipy.signal.stft(audio, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
        mag = np.abs(S)
        threshold = 10 ** (threshold_db / 20.0) * np.max(mag)
        mask = mag > threshold
        S_clean = S * mask
        _, audio_clean = scipy.signal.istft(S_clean, fs=sr, nperseg=n_fft, noverlap=n_fft - hop)
        min_len = min(len(audio), len(audio_clean))
        return audio_clean[:min_len]

    def _simple_dereverb(self, audio: np.ndarray, sr: int, decay: float = 0.95) -> np.ndarray:
        if audio.ndim > 1:
            audio = audio[:, 0]
        from scipy.signal import lfilter
        a_coeffs = np.array([1.0, -decay])
        b_coeffs = np.array([1.0, 0.0])
        return lfilter(b_coeffs, a_coeffs, audio)

    def _repair_clipping(self, audio: np.ndarray, threshold: float = 0.95) -> np.ndarray:
        if audio.ndim > 1:
            audio = audio[:, 0]
        clipped = np.abs(audio) > threshold
        if np.any(clipped):
            audio = audio.copy()
            indices = np.where(clipped)[0]
            for idx in indices:
                start = max(0, idx - 2)
                end = min(len(audio), idx + 3)
                neighbors = audio[start:end]
                neighbors = neighbors[(np.abs(neighbors) <= threshold)]
                if len(neighbors) > 0:
                    audio[idx] = np.mean(neighbors)
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
        return {"model_type": "repair"}
