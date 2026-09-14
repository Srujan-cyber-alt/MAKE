#!/usr/bin/env python3
from __future__ import annotations
import sys
sys.path.insert(0, '/workspace/9e5e888e-cbcf-427b-8a53-56cdad392c91/sessions/agent_6ba23f4a-6a92-4b9e-aed7-e0be6f899a53/backend')

# Direct imports without going through app package
import json
import hashlib
import time
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

# ModelRegistry implementation copied here
class ModelStatus(str, Enum):
    UNTRAINED = "untrained"
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    CORRUPTED = "corrupted"


@dataclass
class ModelCheckpoint:
    id: str
    model_name: str
    model_version: str
    arch_version: str
    path: str
    sha256: str
    size_bytes: int
    created_at: float
    training_step: int
    epoch: int
    optimizer_state: Dict[str, Any] = field(default_factory=dict)
    scheduler_state: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)
    dataset_fingerprint: str = ""
    seed: int = 42
    training_metadata: Dict[str, Any] = field(default_factory=dict)
    validation_loss: Optional[float] = None
    training_loss: Optional[float] = None
    status: str = ModelStatus.TRAINED.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelCheckpoint":
        return cls(**data)


@dataclass
class ModelEntry:
    name: str
    version: str
    arch_version: str
    model_type: str
    status: str = ModelStatus.UNTRAINED.value
    description: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    checkpoints: List[str] = field(default_factory=list)
    best_checkpoint_id: Optional[str] = None
    latest_checkpoint_id: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dataset_fingerprint: str = ""
    seed: int = 42

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelEntry":
        return cls(**data)


class ModelRegistry:
    def __init__(self, registry_path: str) -> None:
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._models: Dict[str, ModelEntry] = {}
        self._checkpoints: Dict[str, ModelCheckpoint] = {}
        self._load()

    def _load(self) -> None:
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    data = json.load(f)
                for name, mdata in data.get("models", {}).items():
                    self._models[name] = ModelEntry.from_dict(mdata)
                for cid, cdata in data.get("checkpoints", {}).items():
                    self._checkpoints[cid] = ModelCheckpoint.from_dict(cdata)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                raise RuntimeError(f"Failed to load model registry: {e}")

    def _save(self) -> None:
        data = {
            "models": {name: m.to_dict() for name, m in self._models.items()},
            "checkpoints": {cid: c.to_dict() for cid, c in self._checkpoints.items()},
        }
        tmp_path = self.registry_path.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        os.replace(tmp_path, self.registry_path)

    def _compute_sha256(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def register_model(
        self,
        name: str,
        version: str,
        arch_version: str,
        model_type: str,
        config: Dict[str, Any],
        dataset_fingerprint: str = "",
        seed: int = 42,
        description: str = "",
    ) -> ModelEntry:
        if name in self._models:
            raise ValueError(f"Model {name} already registered")

        entry = ModelEntry(
            name=name,
            version=version,
            arch_version=arch_version,
            model_type=model_type,
            status=ModelStatus.UNTRAINED.value,
            description=description,
            config=config,
            dataset_fingerprint=dataset_fingerprint,
            seed=seed,
        )
        self._models[name] = entry
        self._save()
        return entry

    def register_checkpoint(
        self,
        model_name: str,
        checkpoint_path: str,
        training_step: int,
        epoch: int,
        optimizer_state: Dict[str, Any],
        scheduler_state: Dict[str, Any],
        training_config: Dict[str, Any],
        dataset_fingerprint: str,
        seed: int,
        training_metadata: Dict[str, Any],
        validation_loss: Optional[float] = None,
        training_loss: Optional[float] = None,
        is_best: bool = False,
    ) -> ModelCheckpoint:
        if model_name not in self._models:
            raise ValueError(f"Model {model_name} not registered")

        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        sha256 = self._compute_sha256(checkpoint_path)
        size_bytes = os.path.getsize(checkpoint_path)

        checkpoint_id = f"{model_name}_step{training_step}_{sha256[:8]}"

        checkpoint = ModelCheckpoint(
            id=checkpoint_id,
            model_name=model_name,
            model_version=self._models[model_name].version,
            arch_version=self._models[model_name].arch_version,
            path=checkpoint_path,
            sha256=sha256,
            size_bytes=size_bytes,
            created_at=time.time(),
            training_step=training_step,
            epoch=epoch,
            optimizer_state=optimizer_state,
            scheduler_state=scheduler_state,
            training_config=training_config,
            dataset_fingerprint=dataset_fingerprint,
            seed=seed,
            training_metadata=training_metadata,
            validation_loss=validation_loss,
            training_loss=training_loss,
            status=ModelStatus.TRAINED.value,
        )

        self._checkpoints[checkpoint_id] = checkpoint
        self._models[model_name].checkpoints.append(checkpoint_id)
        self._models[model_name].latest_checkpoint_id = checkpoint_id
        self._models[model_name].updated_at = time.time()

        if is_best or validation_loss is not None:
            current_best = self._models[model_name].best_checkpoint_id
            if current_best is None or (validation_loss is not None and
                 self._checkpoints[current_best].validation_loss is not None and
                 validation_loss < self._checkpoints[current_best].validation_loss):
                self._models[model_name].best_checkpoint_id = checkpoint_id
                self._models[model_name].status = ModelStatus.TRAINED.value

        self._save()
        return checkpoint

    def get(self, model_name: str) -> Optional[ModelEntry]:
        return self._models.get(model_name)

    def get_checkpoint(self, checkpoint_id: str) -> Optional[ModelCheckpoint]:
        return self._checkpoints.get(checkpoint_id)

    def get_best_checkpoint(self, model_name: str) -> Optional[ModelCheckpoint]:
        model = self._models.get(model_name)
        if not model or not model.best_checkpoint_id:
            return None
        return self._checkpoints.get(model.best_checkpoint_id)

    def verify_checkpoint(self, model_name: str, checkpoint_id: Optional[str] = None) -> bool:
        if checkpoint_id:
            checkpoint = self._checkpoints.get(checkpoint_id)
            if not checkpoint or checkpoint.model_name != model_name:
                return False
        else:
            checkpoint = self.get_best_checkpoint(model_name)
            if not checkpoint:
                return False

        if not os.path.exists(checkpoint.path):
            return False

        actual_sha = self._compute_sha256(checkpoint.path)
        return actual_sha == checkpoint.sha256


# Paths implementation
def get_model_registry_path() -> Path:
    return Path("data/model_registry.json")


# Now register
import torch

registry = ModelRegistry(str(get_model_registry_path()))

# Register the model
entry = registry.register_model(
    name='make_neural_tts_v1',
    version='1.0.0',
    arch_version='1.0',
    model_type='neural_tts',
    config={
        'vocab_size': 256,
        'embed_dim': 256,
        'hidden_dim': 512,
        'num_layers': 4,
        'num_heads': 8,
        'ffn_dim': 1024,
        'dropout': 0.1,
        'sample_rate': 16000,
        'seed': 42,
    },
    dataset_fingerprint='44136fa355b3678a',
    seed=42,
    description='MAKE Neural TTS v1 - Transformer+BiLSTM+Conv1dVocoder',
)

print(f'Registered: {entry.name} v{entry.version}')

# Register the best checkpoint
checkpoint = torch.load('data/checkpoints/neural_audio/step_50_best.pt', map_location='cpu', weights_only=False)

cp = registry.register_checkpoint(
    model_name='make_neural_tts_v1',
    checkpoint_path='data/checkpoints/neural_audio/step_50_best.pt',
    training_step=checkpoint['step'],
    epoch=checkpoint['epoch'],
    optimizer_state=checkpoint['optimizer_state_dict'],
    scheduler_state=checkpoint['scheduler_state_dict'],
    training_config=checkpoint['training_config'],
    dataset_fingerprint=checkpoint['dataset_fingerprint'],
    seed=checkpoint['seed'],
    training_metadata=checkpoint['training_metadata'],
    validation_loss=checkpoint['best_val_loss'],
    training_loss=checkpoint['train_losses'][-1] if checkpoint['train_losses'] else None,
    is_best=True,
)

print(f'Registered checkpoint: {cp.id}')
print(f'SHA256: {cp.sha256}')
print(f'Validation loss: {cp.validation_loss}')

# Verify
print(f'Verify: {registry.verify_checkpoint("make_neural_tts_v1")}')
print(f'Best checkpoint: {registry.get_best_checkpoint("make_neural_tts_v1").sha256}')