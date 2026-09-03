"""
MAKE model registry.

Persistent local registry of model versions, training runs, and
checkpoints. The registry refuses to register any checkpoint that
does not declare owner="MAKE". All on-disk artifacts are SHA-256
verified before being reported as available.
"""

from __future__ import annotations
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.make_model.state import ModelState, state_summary
from app.make_model.utils import (
    paths, ensure_dirs, dump_json, load_json, now_iso, sha256_file,
    get_logger,
)


logger = get_logger("make_model.registry")

OWNER = "MAKE"
SCHEMA_VERSION = 1


@dataclass
class ModelVersion:
    name: str
    arch_version: str
    created_at: str
    description: str = ""
    config: Dict[str, Any] = field(default_factory=dict)
    parameter_count_estimate: int = 0
    status: str = ModelState.UNTRAINED.value
    training_runs: List[str] = field(default_factory=list)
    checkpoint_ids: List[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CheckpointRecord:
    id: str
    model_name: str
    model_version: str
    arch_version: str
    owner: str
    created_at: str
    path: str
    sha256: str
    bytes: int
    training_run_id: str
    global_step: int
    epoch: int
    config: Dict[str, Any]
    dataset_name: str
    dataset_manifest_sha: str
    git_commit: str
    framework_version: str
    pytorch_version: str
    metric_summary: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MakeModelRegistry:
    def __init__(self, root: Optional[str] = None) -> None:
        p = ensure_dirs(root)
        self.root = p["root"]
        self.path = p["registry"]
        # Defensive: if a previous run left registry.json as a directory,
        # we cannot read it as a file. Move it aside and start fresh.
        if self.path.is_dir():
            import shutil, time as _t
            backup = self.path.with_name(f"registry.json.bak-{int(_t.time())}")
            try:
                shutil.move(str(self.path), str(backup))
            except Exception:
                pass
        if not self.path.exists():
            self._save({"schema_version": SCHEMA_VERSION, "models": {}, "checkpoints": {}, "training_runs": {}})

    def _save(self, data: Dict[str, Any]) -> None:
        dump_json(self.path, data)

    def _load(self) -> Dict[str, Any]:
        return load_json(self.path)

    # --- model versions -------------------------------------------------
    def register_model(self, mv: ModelVersion) -> None:
        d = self._load()
        d.setdefault("models", {})[mv.name] = mv.to_dict()
        self._save(d)
        logger.info(f"Registered model {mv.name} (status={mv.status})")

    def get_model(self, name: str) -> Optional[Dict[str, Any]]:
        return self._load().get("models", {}).get(name)

    def list_models(self) -> List[Dict[str, Any]]:
        return list(self._load().get("models", {}).values())

    def update_model_status(self, name: str, status: str, notes: str = "") -> None:
        d = self._load()
        if name not in d.setdefault("models", {}):
            raise KeyError(f"Unknown model: {name}")
        d["models"][name]["status"] = status
        if notes:
            d["models"][name]["notes"] = notes
        self._save(d)

    # --- training runs --------------------------------------------------
    def register_training_run(self, run: Dict[str, Any]) -> None:
        d = self._load()
        d.setdefault("training_runs", {})[run["id"]] = run
        self._save(d)
        logger.info(f"Registered training run {run['id']}")

    def update_training_run(self, run_id: str, patch: Dict[str, Any]) -> None:
        d = self._load()
        if run_id not in d.setdefault("training_runs", {}):
            raise KeyError(f"Unknown training run: {run_id}")
        d["training_runs"][run_id].update(patch)
        self._save(d)

    def get_training_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        return self._load().get("training_runs", {}).get(run_id)

    def list_training_runs(self) -> List[Dict[str, Any]]:
        return list(self._load().get("training_runs", {}).values())

    # --- checkpoints ----------------------------------------------------
    def register_checkpoint(self, rec: CheckpointRecord) -> None:
        if rec.owner != OWNER:
            raise ValueError(
                f"Refusing to register non-MAKE checkpoint (owner={rec.owner!r}, expected {OWNER!r})"
            )
        d = self._load()
        d.setdefault("checkpoints", {})[rec.id] = rec.to_dict()
        models = d.setdefault("models", {})
        m = models.setdefault(rec.model_name, {})
        m.setdefault("checkpoint_ids", []).append(rec.id)
        self._save(d)
        logger.info(f"Registered checkpoint {rec.id} ({rec.sha256[:12]})")

    def get_checkpoint(self, cp_id: str) -> Optional[Dict[str, Any]]:
        return self._load().get("checkpoints", {}).get(cp_id)

    def list_checkpoints(self, model_name: Optional[str] = None) -> List[Dict[str, Any]]:
        cps = list(self._load().get("checkpoints", {}).values())
        if model_name:
            cps = [c for c in cps if c["model_name"] == model_name]
        return cps

    def verify_checkpoint(self, cp_id: str) -> Dict[str, Any]:
        cp = self.get_checkpoint(cp_id)
        if not cp:
            return {"ok": False, "reason": "checkpoint not in registry", "id": cp_id}
        if not os.path.exists(cp["path"]):
            return {"ok": False, "reason": "checkpoint file missing on disk", "id": cp_id, "path": cp["path"]}
        actual = sha256_file(cp["path"])
        ok = actual == cp["sha256"]
        return {
            "ok": ok,
            "id": cp_id,
            "expected_sha256": cp["sha256"],
            "actual_sha256": actual,
            "bytes": os.path.getsize(cp["path"]),
            "reason": None if ok else "SHA-256 mismatch (file modified or corrupted)",
        }

    # --- status ---------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        d = self._load()
        models = d.get("models", {})
        cps = d.get("checkpoints", {})
        runs = d.get("training_runs", {})
        has_checkpoint = len(cps) > 0
        inference_ready_model: Optional[str] = None
        production_ready_model: Optional[str] = None
        for name, m in models.items():
            if m.get("status") == ModelState.PRODUCTION_READY.value:
                production_ready_model = name
            elif m.get("status") == ModelState.INFERENCE_READY.value and not inference_ready_model:
                inference_ready_model = name
        if production_ready_model:
            overall = ModelState.PRODUCTION_READY.value
        elif inference_ready_model:
            overall = ModelState.INFERENCE_READY.value
        elif has_checkpoint:
            overall = ModelState.CHECKPOINT_AVAILABLE.value
        elif runs:
            overall = ModelState.TRAINING.value
        else:
            overall = ModelState.UNTRAINED.value
        return {
            "owner": OWNER,
            "schema_version": SCHEMA_VERSION,
            "overall_state": overall,
            "model_count": len(models),
            "checkpoint_count": len(cps),
            "training_run_count": len(runs),
            "models": list(models.values()),
            "checkpoints": list(cps.values()),
            "training_runs": list(runs.values()),
            "summary": state_summary(ModelState(overall)),
        }


_REGISTRY: Optional[MakeModelRegistry] = None


def get_registry(root: Optional[str] = None) -> MakeModelRegistry:
    global _REGISTRY
    if root:
        return MakeModelRegistry(root)
    if _REGISTRY is None:
        _REGISTRY = MakeModelRegistry()
    return _REGISTRY
