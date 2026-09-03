"""
HTTP API for the MAKE proprietary model program.

Endpoints:
  GET  /api/v1/make-model/status
  GET  /api/v1/make-model/hardware
  GET  /api/v1/make-model/models
  GET  /api/v1/make-model/models/{model_name}
  GET  /api/v1/make-model/training/runs
  GET  /api/v1/make-model/training/runs/{run_id}
  GET  /api/v1/make-model/checkpoints
  POST /api/v1/make-model/training/validate
  POST /api/v1/make-model/inference/validate
  GET  /api/v1/make-model/audit
"""

from __future__ import annotations
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Body

from app.make_model.utils import load_json


router = APIRouter(prefix="/api/v1/make-model", tags=["make-model"])


@router.get("/status")
def get_status() -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    return get_registry().get_status()


@router.get("/hardware")
def get_hardware() -> Dict[str, Any]:
    from app.make_model.training import detect_hardware
    return detect_hardware().to_dict()


@router.get("/models")
def list_models() -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    return {"models": reg.list_models()}


@router.get("/models/{model_name}")
def get_model(model_name: str) -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    m = reg.get_model(model_name)
    if not m:
        raise HTTPException(status_code=404, detail=f"model {model_name!r} not found")
    m["checkpoints"] = reg.list_checkpoints(model_name=model_name)
    return m


@router.get("/training/runs")
def list_runs() -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    return {"runs": reg.list_training_runs()}


@router.get("/training/runs/{run_id}")
def get_run(run_id: str) -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    r = reg.get_training_run(run_id)
    if not r:
        raise HTTPException(status_code=404, detail=f"run {run_id!r} not found")
    return r


@router.get("/checkpoints")
def list_checkpoints(model: Optional[str] = None) -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    return {"checkpoints": reg.list_checkpoints(model_name=model)}


@router.post("/training/validate")
def training_validate(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    from app.make_model.training import TrainingConfig, validate_training_readiness
    cfg_dict = payload.get("config", {})
    dataset_manifest = payload.get("dataset_manifest", "")
    cfg = TrainingConfig.from_dict(cfg_dict)
    return validate_training_readiness(cfg, dataset_manifest_path=dataset_manifest)


@router.post("/inference/validate")
def inference_validate() -> Dict[str, Any]:
    from app.make_model.inference import inference_availability
    return inference_availability()


@router.get("/audit")
def audit() -> Dict[str, Any]:
    from app.make_model.audit import run_ownership_audit
    return run_ownership_audit()
