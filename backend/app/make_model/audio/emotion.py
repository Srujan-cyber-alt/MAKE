"""
Emotion engine - control happiness, sadness, anger, fear, calm, excitement, tension, etc.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import time
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import EmotionModelInterface, GenerationRequest, GenerationResult, AudioConfig
from app.make_model.audio.types import EmotionVector, AudioTensor
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class EmotionEngine(EmotionModelInterface):
    model_type = "emotion"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
        self._emotion_presets: Dict[str, EmotionVector] = {
            "neutral": EmotionVector(),
            "happy": EmotionVector(happiness=0.9, excitement=0.6, confidence=0.7),
            "sad": EmotionVector(sadness=0.9, calm=0.4, exhaustion=0.3),
            "angry": EmotionVector(anger=0.9, tension=0.8, confidence=0.6),
            "fearful": EmotionVector(fear=0.9, tension=0.7, exhaustion=0.3),
            "calm": EmotionVector(calm=0.9, happiness=0.3),
            "excited": EmotionVector(excitement=0.9, happiness=0.7, confidence=0.6),
            "tense": EmotionVector(tension=0.9, fear=0.4),
            "confident": EmotionVector(confidence=0.9, calm=0.5),
            "intimate": EmotionVector(intimacy=0.9, calm=0.6),
            "exhausted": EmotionVector(exhaustion=0.9, sadness=0.4, calm=0.3),
            "surprised": EmotionVector(surprise=0.9, excitement=0.5, tension=0.4),
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
            provenance={"type": "emotion_placeholder"},
        )

    async def apply_emotion(self, audio_path: str, emotion: str, intensity: float = 1.0) -> GenerationResult:
        if emotion not in self._emotion_presets:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail=f"Unknown emotion: {emotion}")
        if not self._model or not self._vocoder:
            raise RuntimeError("EmotionEngine not initialized")
        text = f"emotion_{emotion}"
        params = self._model.forward(text, "default", emotion)
        duration = 1.0
        audio = self._vocoder.synthesize(params, duration)
        output_path = audio_path.replace(".wav", f"_emotion_{emotion}.wav") if audio_path.endswith(".wav") else f"/tmp/emotion_{emotion}_{int(time.time())}.wav"
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
            provenance={"emotion": emotion, "intensity": intensity, "type": "emotion_application", "model": "tiny_numpy"},
        )

    async def blend_emotions(self, audio_path: str, emotions: List[str], weights: List[float]) -> GenerationResult:
        if len(emotions) != len(weights):
            raise ValueError("Emotions and weights must have same length")
        blended = EmotionVector()
        for emotion, weight in zip(emotions, weights):
            if emotion not in self._emotion_presets:
                continue
            preset = self._emotion_presets[emotion]
            for key in blended.__dataclass_fields__:
                setattr(blended, key, getattr(blended, key, 0.0) + getattr(preset, key, 0.0) * weight)
        output_path = audio_path.replace(".wav", "_emotion_blended.wav") if audio_path.endswith(".wav") else f"/tmp/emotion_blended_{int(time.time())}.wav"
        if self._model and self._vocoder:
            params = self._model.forward("blended_emotion", "default", emotions[0] if emotions else None)
            audio = self._vocoder.synthesize(params, 1.0)
            wavfile.write(output_path, self.config.sample_rate, (audio * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=1.0,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"blended_emotions": dict(zip(emotions, weights)), "type": "emotion_blend"},
        )

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        import json
        from pathlib import Path
        data = self.get_provenance()
        data["checkpoint_type"] = "stateless_dsp"
        data["timestamp"] = time.time()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    async def load_checkpoint(self, path: str) -> None:
        import json
        from pathlib import Path
        if Path(path).exists():
            with open(path, "r") as f:
                _data = json.load(f)

    def get_provenance(self) -> Dict[str, Any]:
        return {"model_type": "emotion", "available_emotions": list(self._emotion_presets.keys())}

    def _scale_emotion(self, vector: EmotionVector, intensity: float) -> EmotionVector:
        result = EmotionVector()
        for key in result.__dataclass_fields__:
            val = getattr(vector, key, 0.0)
            setattr(result, key, min(1.0, val * intensity))
        return result
