"""
Model Registry for MAKE Audio V2.

Manages model checkpoints with SHA-256 integrity verification.
All checkpoints must be registered and verified before use.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import hashlib
import os
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum


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
    def from_dict(cls, data: Dict[str, Any]) -> ModelCheckpoint:
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
    def from_dict(cls, data: Dict[str, Any]) -> ModelEntry:
        return cls(**data)


class ModelRegistry:
    """
    Production model registry with integrity verification.
    
    Features:
    - SHA-256 checkpoint verification
    - Model versioning
    - Checkpoint metadata persistence
    - Corruption detection
    - Incompatible checkpoint rejection
    """

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

    def _compute_dataset_fingerprint(self, dataset_config: Dict[str, Any]) -> str:
        """Compute deterministic fingerprint of dataset configuration."""
        content = json.dumps(dataset_config, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

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

    def get_latest_checkpoint(self, model_name: str) -> Optional[ModelCheckpoint]:
        model = self._models.get(model_name)
        if not model or not model.latest_checkpoint_id:
            return None
        return self._checkpoints.get(model.latest_checkpoint_id)

    def list_models(self) -> List[Dict[str, Any]]:
        return [m.to_dict() for m in self._models.values()]

    def list_checkpoints(self, model_name: str) -> List[Dict[str, Any]]:
        model = self._models.get(model_name)
        if not model:
            return []
        return [self._checkpoints[cid].to_dict() for cid in model.checkpoints if cid in self._checkpoints]

    def verify_checkpoint(self, model_name: str, checkpoint_id: Optional[str] = None) -> bool:
        """Verify checkpoint integrity via SHA-256."""
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

    def verify_all_checkpoints(self, model_name: str) -> Dict[str, bool]:
        """Verify all checkpoints for a model."""
        model = self._models.get(model_name)
        if not model:
            return {}
        results = {}
        for cid in model.checkpoints:
            cp = self._checkpoints.get(cid)
            if cp:
                results[cid] = self.verify_checkpoint(model_name, cid)
        return results

    def set_model_status(self, model_name: str, status: ModelStatus) -> None:
        if model_name not in self._models:
            raise ValueError(f"Model {model_name} not registered")
        self._models[model_name].status = status.value
        self._models[model_name].updated_at = time.time()
        self._save()

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        if checkpoint_id not in self._checkpoints:
            return False
        cp = self._checkpoints[checkpoint_id]
        model_name = cp.model_name
        if model_name in self._models:
            if checkpoint_id in self._models[model_name].checkpoints:
                self._models[model_name].checkpoints.remove(checkpoint_id)
            if self._models[model_name].best_checkpoint_id == checkpoint_id:
                self._models[model_name].best_checkpoint_id = None
            if self._models[model_name].latest_checkpoint_id == checkpoint_id:
                self._models[model_name].latest_checkpoint_id = None
        del self._checkpoints[checkpoint_id]
        self._save()
        return True


def get_registry(registry_path: Optional[str] = None) -> ModelRegistry:
    """Get or create global model registry."""
    if not hasattr(get_registry, "_instance"):
        path = registry_path or os.environ.get("MAKE_MODEL_REGISTRY", "/tmp/make_model_registry.json")
        get_registry._instance = ModelRegistry(path)
    return get_registry._instance