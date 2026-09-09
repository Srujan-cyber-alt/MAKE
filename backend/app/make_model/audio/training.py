"""
Audio training pipeline - real training with tiny numpy model.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import json
from pathlib import Path

from app.make_model.audio.architecture import AudioConfig
from app.make_model.audio.config_loader import load_audio_config
from app.make_model.audio.tiny_model import TinyAudioModel, train_step, verify_gradients, generate_synthetic_target


class AudioTrainingPipeline:
    def __init__(self, config: Optional[AudioConfig] = None) -> None:
        self.config = config
        self._checkpoints: List[str] = []
        self._metrics: List[Dict[str, Any]] = []
        self._model: Optional[TinyAudioModel] = None
        if self.config is None:
            try:
                self.config = load_audio_config("tiny")
            except FileNotFoundError:
                self.config = load_audio_config("app/make_model/audio/configs/audio_tiny.json")

    async def initialize(self, config_path: Optional[str] = None) -> None:
        if config_path:
            self.config = load_audio_config(config_path)
        seed = self.config.training.get("seed", 42)
        self._model = TinyAudioModel(self.config, seed=seed)

    async def train_step(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        if not self._model:
            await self.initialize()
        texts = batch.get("texts", ["hello world"])
        durations = batch.get("durations", [1.0])
        lr = self.config.training.get("learning_rate", 1e-4)
        loss = train_step(self._model, texts, durations, lr=lr)
        step_metrics = {
            "step": len(self._metrics),
            "loss": loss,
            "learning_rate": lr,
            "timestamp": time.time(),
        }
        self._metrics.append(step_metrics)
        return step_metrics

    async def save_checkpoint(self, path: str) -> str:
        if not self._model:
            raise RuntimeError("Model not initialized")
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._model.save_checkpoint(path)
        checkpoint = {
            "config": self.config.__dict__,
            "metrics": self._metrics,
            "timestamp": time.time(),
            "model_path": path,
        }
        json_path = path.replace(".npz", ".json")
        with open(json_path, "w") as f:
            json.dump(checkpoint, f, indent=2)
        self._checkpoints.append(path)
        return path

    async def load_checkpoint(self, path: str) -> Dict[str, Any]:
        if not self._model:
            await self.initialize()
        self._model.load_checkpoint(path)
        json_path = path.replace(".npz", ".json")
        if Path(json_path).exists():
            with open(json_path, "r") as f:
                checkpoint = json.load(f)
            self._metrics = checkpoint.get("metrics", [])
        else:
            self._metrics = []
        return {"model_path": path, "metrics": self._metrics}

    def verify_gradients(self, text: str = "hello") -> bool:
        if not self._model:
            raise RuntimeError("Model not initialized")
        return verify_gradients(self._model, text)

    def get_training_summary(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self._metrics),
            "checkpoints": self._checkpoints,
            "latest_metrics": self._metrics[-1] if self._metrics else None,
        }
