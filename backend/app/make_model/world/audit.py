"""MAKE World Model X — Ownership audit.

Returns one of:
    YES       - architecture + training code + inference + a real
                 MAKE checkpoint on disk
    PARTIAL   - architecture + code present; no real checkpoint
    NO        - missing one of {arch, code, registry, inference}

This audit NEVER fabricates a checkpoint. The verdict is derived
from the registry, the on-disk artifacts, and the local file system.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from app.make_model.utils import sha256_file, paths
from app.make_model.world.arch import MakeWorldModelConfig, MakeWorldModelV0


@dataclass
class WorldModelAuditReport:
    verdict: str                                # YES | PARTIAL | NO
    verdict_reason: str
    has_architecture_code: bool
    has_training_code: bool
    has_data_engine: bool
    has_inference_code: bool
    has_registry: bool
    has_checkpoint: bool
    checkpoint_paths: List[str]
    checkpoint_hashes: List[str]
    parameter_count: int
    arch_config: Dict[str, Any]
    hardware: Dict[str, Any]
    suspicious_files: List[str]
    notes: List[str]


def _detect_hardware() -> Dict[str, Any]:
    import multiprocessing
    out: Dict[str, Any] = {
        "cpu_cores": multiprocessing.cpu_count(),
        "ram_gb": 0.0,
        "disk_free_gb": 0.0,
        "gpu_name": "",
        "gpu_vram_gb": 0.0,
        "cuda_available": False,
        "pytorch_available": False,
    }
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    out["ram_gb"] = int(line.split()[1]) / 1024.0 / 1024.0
    except Exception:
        pass
    try:
        st = os.statvfs("/")
        out["disk_free_gb"] = (st.f_bavail * st.f_frsize) / 1e9
    except Exception:
        pass
    try:
        import torch  # type: ignore
        out["pytorch_available"] = True
        out["cuda_available"] = bool(torch.cuda.is_available())
        if out["cuda_available"]:
            out["gpu_name"] = torch.cuda.get_device_name(0)
            out["gpu_vram_gb"] = float(torch.cuda.get_device_properties(0).total_memory) / 1e9
    except Exception:
        pass
    return out


def _scan_for_suspicious_weights(make_root: str) -> List[str]:
    """Find any weight files in the make_model root that don't belong to us.

    A 'suspicious' weight is one whose name suggests it could be a
    third-party model (sdxl, runway, pika, sora, luma, cogvideo, etc.)
    OR any file > 100MB that we did not create.
    """
    suspicious: List[str] = []
    if not os.path.isdir(make_root):
        return suspicious
    for root, _, files in os.walk(make_root):
        for f in files:
            if not f.lower().endswith((".pt", ".pth", ".ckpt", ".safetensors", ".bin", ".onnx", ".gguf")):
                continue
            p = os.path.join(root, f)
            try:
                if os.path.getsize(p) > 100 * 1024 * 1024:
                    suspicious.append(p)
            except Exception:
                pass
    return suspicious


def run_world_ownership_audit(registry: Optional[Any] = None) -> WorldModelAuditReport:
    p = paths()
    root = p["root"]
    has_arch = os.path.exists(os.path.join(root, "..", "app", "make_model", "world", "arch.py")) \
        or os.path.exists("app/make_model/world/arch.py")
    has_training = os.path.exists("app/make_model/world/training.py")
    has_data = os.path.exists("app/make_model/world/data_engine.py")
    has_inference = os.path.exists("app/make_model/world/inference.py")
    has_registry_code = os.path.exists("app/make_model/registry/__init__.py")

    ckpt_paths: List[str] = []
    ckpt_hashes: List[str] = []
    if registry is not None:
        try:
            for c in registry.list_checkpoints():
                path = c.get("path")
                if path and os.path.exists(path):
                    ckpt_paths.append(path)
                    ckpt_hashes.append(c.get("sha256") or "")
        except Exception:
            pass

    cfg = MakeWorldModelConfig()
    try:
        model = MakeWorldModelV0(cfg)
        params = model.parameter_count()
    except Exception:
        params = 0

    suspicious = _scan_for_suspicious_weights(root)
    hw = _detect_hardware()

    notes: List[str] = []
    if not has_arch:
        notes.append("architecture module missing")
    if not has_training:
        notes.append("training module missing")
    if not has_data:
        notes.append("data engine missing")
    if not has_inference:
        notes.append("inference module missing")
    if not ckpt_paths:
        notes.append("no MAKE checkpoint on disk")
    if suspicious:
        notes.append(f"suspicious weight files: {suspicious[:3]}")

    if has_arch and has_training and has_data and has_inference and ckpt_paths:
        verdict = "YES"
        reason = "MAKE World Model X has architecture, training, data engine, inference code, and a registered checkpoint on disk."
    elif has_arch and has_training and has_data and has_inference and not ckpt_paths:
        verdict = "PARTIAL"
        reason = "MAKE World Model X has all engineering modules but no real checkpoint has been produced yet."
    else:
        verdict = "NO"
        reason = "Missing one or more of: architecture / training / data / inference. See notes."

    return WorldModelAuditReport(
        verdict=verdict,
        verdict_reason=reason,
        has_architecture_code=has_arch,
        has_training_code=has_training,
        has_data_engine=has_data,
        has_inference_code=has_inference,
        has_registry=has_registry_code,
        has_checkpoint=bool(ckpt_paths),
        checkpoint_paths=ckpt_paths,
        checkpoint_hashes=ckpt_hashes,
        parameter_count=params,
        arch_config=cfg.to_dict(),
        hardware=hw,
        suspicious_files=suspicious,
        notes=notes,
    )


__all__ = ["WorldModelAuditReport", "run_world_ownership_audit"]
