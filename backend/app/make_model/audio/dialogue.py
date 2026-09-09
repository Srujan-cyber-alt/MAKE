"""
Dialogue engine - multi-speaker dialogue generation and memory.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import numpy as np
import scipy.io.wavfile as wavfile

from app.make_model.audio.architecture import (
    DialogueModelInterface, GenerationRequest, GenerationResult, AudioConfig
)
from app.make_model.audio.tiny_model import TinyAudioModel, TinyVocoder


class DialogueEngine(DialogueModelInterface):
    model_type = "dialogue"

    def __init__(self) -> None:
        self.config: Optional[AudioConfig] = None
        self._dialogue_history: List[Dict[str, Any]] = []
        self._speaker_contexts: Dict[str, Dict[str, Any]] = {}
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
            provenance={"type": "dialogue_placeholder"},
        )

    async def generate_dialogue(self, script: List[Dict[str, str]], voices: Dict[str, str]) -> GenerationResult:
        if not self._model or not self._vocoder:
            raise RuntimeError("DialogueEngine not initialized")
        output_path = f"/tmp/dialogue_{int(time.time())}.wav"
        segments = []
        for line in script:
            speaker = line.get("speaker", "default")
            text = line.get("text", "")
            voice_id = voices.get(speaker, speaker)
            emotion = line.get("emotion")
            duration = min(len(text) * 0.08 + 0.5, self.config.max_duration_seconds if self.config else 10.0)
            params = self._model.forward(text, voice_id, emotion)
            seg = self._vocoder.synthesize(params, duration)
            segments.append(seg)
            self._dialogue_history.append({
                "timestamp": time.time(),
                "speaker": speaker,
                "text": text,
                "emotion": emotion,
                "output_duration": duration,
            })
            if speaker not in self._speaker_contexts:
                self._speaker_contexts[speaker] = {
                    "previous_emotion": "neutral",
                    "emotional_state": {"neutral": 1.0},
                    "conversation_turns": 0,
                }
            self._speaker_contexts[speaker]["conversation_turns"] += 1
        if segments:
            audio = np.concatenate(segments)
        else:
            audio = np.zeros(int(self.config.sample_rate * 0.1), dtype=np.float32)
        wavfile.write(output_path, self.config.sample_rate, (audio * 32767).astype(np.int16))
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate,
            channels=self.config.channels,
            duration_seconds=len(audio) / self.config.sample_rate,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={
                "script_length": len(script),
                "speakers": list(voices.keys()),
                "type": "dialogue_generation",
                "model": "tiny_numpy",
            },
        )

    async def repair_dialogue(self, audio_path: str, transcript: str) -> GenerationResult:
        output_path = audio_path.replace(".wav", "_repaired.wav")
        return GenerationResult(
            audio_path=output_path,
            sample_rate=self.config.sample_rate if self.config else 16000,
            channels=self.config.channels if self.config else 1,
            duration_seconds=0.0,
            seed=None,
            model_id=self.config.model_id if self.config else "",
            model_version=self.config.version if self.config else "",
            latency_ms=0.0,
            provenance={"transcript": transcript, "type": "dialogue_repair"},
        )

    async def evaluate_quality(self, audio_path: str) -> Any:
        from app.make_model.audio.quality import AudioQualityEvaluator
        evaluator = AudioQualityEvaluator()
        return await evaluator.evaluate(audio_path)

    async def save_checkpoint(self, path: str) -> None:
        import json
        with open(path, "w") as f:
            json.dump({
                "history": self._dialogue_history,
                "speaker_contexts": self._speaker_contexts,
            }, f, indent=2)

    async def load_checkpoint(self, path: str) -> None:
        import json
        with open(path, "r") as f:
            data = json.load(f)
        self._dialogue_history = data.get("history", [])
        self._speaker_contexts = data.get("speaker_contexts", {})

    def get_provenance(self) -> Dict[str, Any]:
        return {
            "model_type": "dialogue",
            "dialogue_turns": len(self._dialogue_history),
            "speakers": list(self._speaker_contexts.keys()),
        }
