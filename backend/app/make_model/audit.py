"""
Model ownership audit for the MAKE proprietary model program.

Returns a structured report with a verdict:
  YES      - a real MAKE-owned checkpoint exists and is valid
  PARTIAL  - code path exists but no trained weights present
  NO       - required modules are missing

The audit never infers YES from architecture code alone.
"""

from __future__ import annotations
import os
from typing import Any, Dict, List

from app.make_model.registry import OWNER
from app.make_model.training import detect_hardware
from app.make_model.utils import now_iso


def run_ownership_audit() -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    status = reg.get_status()
    hw = detect_hardware()
    cp_reports: List[Dict[str, Any]] = []
    for cp in status["checkpoints"]:
        v = reg.verify_checkpoint(cp["id"])
        cp_reports.append({**cp, "verify": v})
    suspicious: List[Dict[str, Any]] = []
    cps_dir = os.path.join(os.environ.get("MAKE_MODEL_ROOT", "/tmp/make_model_artifacts"), "checkpoints")
    if os.path.isdir(cps_dir):
        for fn in os.listdir(cps_dir):
            if fn.endswith((".safetensors", ".bin", ".gguf", ".onnx")):
                suspicious.append({"file": fn, "reason": "weight-shaped file in MAKE checkpoints dir; verify provenance"})
    from app.make_model.arch import MakeModelConfig
    arch_code = True
    from app.make_model.training import CheckpointManager, TrainingRun
    training_code = True
    from app.make_model.inference import MakeInferenceEngine
    inference_code = True
    n_valid_checkpoints = sum(1 for r in cp_reports if r["verify"].get("ok"))
    has_make_owned = any(cp.get("owner") == OWNER for cp in status["checkpoints"])
    if n_valid_checkpoints > 0 and has_make_owned and hw.pytorch_available:
        verdict = "YES"
        verdict_reason = (
            f"Found {n_valid_checkpoints} MAKE-owned checkpoint(s) with valid "
            f"on-disk SHA-256 and torch is available."
        )
    elif status["checkpoint_count"] > 0:
        verdict = "PARTIAL"
        verdict_reason = "Checkpoints registered but integrity failed or torch missing."
    elif training_code and inference_code and arch_code:
        verdict = "PARTIAL"
        verdict_reason = (
            "Architecture, training, and inference code are present; no "
            "trained checkpoint has been produced yet. Model state is UNTRAINED."
        )
    else:
        verdict = "NO"
        verdict_reason = "Required MAKE model modules are missing."
    return {
        "verdict": verdict,
        "verdict_reason": verdict_reason,
        "owner": OWNER,
        "owner_consistent": has_make_owned or status["checkpoint_count"] == 0,
        "suspicious_files": suspicious,
        "hardware": hw.to_dict(),
        "registry_status": {
            "overall_state": status["overall_state"],
            "model_count": status["model_count"],
            "checkpoint_count": status["checkpoint_count"],
            "training_run_count": status["training_run_count"],
        },
        "checkpoint_reports": cp_reports,
        "module_paths": {
            "arch": "app.make_model.arch",
            "dataset": "app.make_model.dataset",
            "training": "app.make_model.training",
            "inference": "app.make_model.inference",
            "registry": "app.make_model.registry",
            "audit": "app.make_model.audit",
        },
        "audited_at": now_iso(),
    }
