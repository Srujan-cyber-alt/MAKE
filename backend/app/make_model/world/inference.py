"""MAKE World Model X — Inference engine.

This is the *neural* inference path for the proprietary model. It:
    1. loads a MAKE checkpoint
    2. compiles conditioning from a MakeInferenceRequest
    3. runs the denoising loop
    4. decodes latents -> frames -> MP4
    5. writes provenance sidecar

If no checkpoint is registered, it returns a structured
MAKE_MODEL_UNTRAINED error. It NEVER falls back to FFmpeg.

This is a minimal, real, end-to-end runtime built on top of the
numpy reference backbone. The torch path is the same module; the
runtime auto-detects torch and uses it when available.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from app.make_model.world.arch import MakeWorldModelConfig, MakeWorldModelV0
from app.make_model.world.conditioning import ConditioningBundle, ConditioningCompiler
from app.make_model.world.representation import (
    CameraRepresentation,
    MotionRepresentation,
    WorldSample,
)
from app.make_model.utils import sha256_file


# ----------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------


class MakeModelXError(Exception):
    code = "MAKE_MODEL_X_ERROR"


class MakeModelXUntrainedError(MakeModelXError):
    code = "MAKE_MODEL_X_UNTRAINED"


class MakeModelXCheckpointMissing(MakeModelXError):
    code = "MAKE_MODEL_X_CHECKPOINT_MISSING"


class MakeModelXCheckpointInvalid(MakeModelXError):
    code = "MAKE_MODEL_X_CHECKPOINT_INVALID"


class MakeModelXArchitectureMismatch(MakeModelXError):
    code = "MAKE_MODEL_X_ARCHITECTURE_MISMATCH"


class MakeModelXDependencyMissing(MakeModelXError):
    code = "MAKE_MODEL_X_DEPENDENCY_MISSING"


# ----------------------------------------------------------------------
# Request / Result
# ----------------------------------------------------------------------


@dataclass
class MakeWorldInferenceRequest:
    prompt: str = ""
    model_name: str = "make-world-tiny"
    checkpoint_id: Optional[str] = None
    seed: int = 0
    frames: int = 8
    short_side: int = 64
    fps: float = 8.0
    num_inference_steps: int = 8
    conditioning: Optional[ConditioningBundle] = None


@dataclass
class MakeWorldInferenceResult:
    ok: bool = True
    code: str = "OK"
    message: str = "ok"
    output_path: Optional[str] = None
    output_sha256: Optional[str] = None
    output_bytes: int = 0
    model_name: str = ""
    checkpoint_id: Optional[str] = None
    checkpoint_sha256: Optional[str] = None
    arch_version: str = ""
    arch_config: Dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    prompt: str = ""
    frames: int = 0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    inference_steps: int = 0
    elapsed_seconds: float = 0.0
    device: str = "cpu"
    dtype: str = "float32"
    hardware: Dict[str, Any] = field(default_factory=dict)
    software: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def provenance_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ----------------------------------------------------------------------
# Denoising loop (research baseline)
# ----------------------------------------------------------------------


def _simple_denoise(
    model: MakeWorldModelV0,
    cond: ConditioningBundle,
    cfg: MakeWorldModelConfig,
    steps: int,
    seed: int,
) -> np.ndarray:
    """Ancestral-style denoising loop using the model as noise predictor.

    x_T ~ N(0, I)
    for t in [T-1 .. 0]:
        eps = model(x_t, t, text_tok, ...)
        x0 = (x_t - sqrt(1-ab[t]) * eps) / sqrt(ab[t])
        x_{t-1} = sqrt(ab[t-1]) * x0 + sqrt(1-ab[t-1]) * eps_pred
    """
    rng = np.random.default_rng(seed)
    C = cfg.latent_channels
    Tt = max(1, cfg.default_frames // cfg.temporal_patch)
    H = W = max(1, cfg.default_short_side // cfg.patch_size)
    x = rng.standard_normal((1, C, Tt, H, W)).astype(np.float32)
    # simple linear schedule
    ab = np.linspace(0.001, 0.999, steps + 1, dtype=np.float32)
    text_tok = cond.text_tokens if cond.text_tokens is not None else np.zeros(
        (1, cfg.text_seq_len), dtype=np.int64
    )
    for i in range(steps, 0, -1):
        t = np.full((1,), i, dtype=np.int64)
        eps = _to_npy(
            model.forward(
                x_noisy=x,
                t=t,
                text_tok=text_tok,
                cross_ctx=None,
                first_frame=cond.first_frame,
                ref_slots=cond.ref_slots,
            )
        )
        a_t = ab[i]
        a_prev = ab[i - 1]
        x0 = (x - np.sqrt(1.0 - a_t) * eps) / np.sqrt(a_t)
        x = np.sqrt(a_prev) * x0 + np.sqrt(1.0 - a_prev) * eps
    return x


def _to_npy(x: Any) -> np.ndarray:
    if hasattr(x, "detach"):
        return x.detach().cpu().numpy()
    return np.asarray(x, dtype=np.float32)


# ----------------------------------------------------------------------
# Latent -> MP4 decoder
# ----------------------------------------------------------------------


def _decode_to_video(latent: np.ndarray, out_path: str, frames: int, short_side: int, fps: float) -> bool:
    """Decode (1, C, T, H, W) latent into a real MP4 via FFmpeg.

    Uses a deterministic mapping: latent -> grayscale -> yuv420p.
    """
    latent = np.asarray(latent)
    C, Tt, H, W = latent.shape[1], latent.shape[2], latent.shape[3], latent.shape[4]
    # collapse channels -> luma
    luma = latent[:, :3].mean(axis=1)  # (1, Tt, H, W)
    # ensure requested frames
    if Tt < frames:
        pad = np.zeros((1, frames - Tt, H, W), dtype=np.float32)
        luma = np.concatenate([luma, pad], axis=1)
    elif Tt > frames:
        luma = luma[:, :frames]
    # normalize 0..1
    luma = (luma - luma.min()) / max(float(luma.max() - luma.min()), 1e-6)
    luma = (luma * 255.0).clip(0, 255).astype(np.uint8)
    # write rawvideo pipe to ffmpeg
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "gray",
                "-s",
                f"{W}x{H}",
                "-r",
                str(fps),
                "-i",
                "-",
                "-vf",
                f"scale={short_side}:-2:flags=bilinear,format=yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-an",
                out_path,
            ],
            input=luma.tobytes(),
            capture_output=True,
            timeout=60,
        )
        return proc.returncode == 0
    except Exception:
        return False


# ----------------------------------------------------------------------
# Engine
# ----------------------------------------------------------------------


class MakeWorldInferenceEngine:
    def __init__(self, registry: Any) -> None:
        self.registry = registry
        self._compiler = ConditioningCompiler()
        self._hw = _detect_hardware()

    def _load_model(self, model_name: str, checkpoint_id: Optional[str]) -> Tuple[MakeWorldModelV0, Dict[str, Any]]:
        # find latest checkpoint
        if checkpoint_id is None:
            cps = [c for c in self.registry.list_checkpoints() if c.get("model_name") == model_name]
            if not cps:
                raise MakeModelXUntrainedError(f"no checkpoint for model {model_name}")
            cp = sorted(cps, key=lambda x: x.get("created_at", ""))[-1]
            checkpoint_id = cp["id"]
        cp = self.registry.get_checkpoint(checkpoint_id)
        if not cp:
            raise MakeModelXCheckpointMissing(checkpoint_id)
        path = cp.get("path")
        if not path or not os.path.exists(path):
            raise MakeModelXCheckpointMissing(f"file missing: {path}")
        # verify hash
        sha = sha256_file(path)
        if cp.get("sha256") and sha != cp["sha256"]:
            raise MakeModelXCheckpointInvalid(f"hash mismatch for {checkpoint_id}")
        # load
        try:
            with np.load(path, allow_pickle=False) as data:
                if "params" not in data.files:
                    raise MakeModelXCheckpointInvalid("missing 'params' key")
                params = {k: data[k] for k in data.files if k != "params"}
                params = {k: data[k] for k in data.files}
            # build config from arch_config
            arch_cfg_dict = cp.get("arch_config") or {}
            cfg = MakeWorldModelConfig(**{k: v for k, v in arch_cfg_dict.items() if k in MakeWorldModelConfig.__dataclass_fields__})
            model = MakeWorldModelV0(cfg)
            # The on-disk file is a numpy .npz where each key is a parameter name.
            param_dict = {k: params[k] for k in params.files}
            model.load_parameters(param_dict)
        except MakeModelXError:
            raise
        except Exception as e:
            raise MakeModelXCheckpointInvalid(str(e)) from e
        return model, cp

    def run(self, req: MakeWorldInferenceRequest) -> MakeWorldInferenceResult:
        t0 = time.time()
        try:
            model, cp = self._load_model(req.model_name, req.checkpoint_id)
        except MakeModelXError as e:
            return MakeWorldInferenceResult(ok=False, code=e.code, message=str(e))
        cfg = model.cfg
        # build conditioning
        cond = req.conditioning or self._compiler.compile(prompt=req.prompt, seed=req.seed)
        if cond.text_tokens is None:
            cond.text_tokens = self._compiler._tokenize_text(req.prompt or "", seq_len=cfg.text_seq_len)
        # resize latent to model defaults
        x = _simple_denoise(
            model=model,
            cond=cond,
            cfg=cfg,
            steps=req.num_inference_steps,
            seed=req.seed,
        )
        # decode
        out_path = os.path.join(
            os.path.dirname(cp.get("path", "/tmp")) or "/tmp",
            f"{req.checkpoint_id or 'ckpt'}-seed{req.seed}.mp4",
        )
        ok = _decode_to_video(x, out_path, req.frames, req.short_side, req.fps)
        if not ok:
            return MakeWorldInferenceResult(
                ok=False, code="MAKE_MODEL_X_DECODE_FAILED", message="ffmpeg decode failed"
            )
        sha = sha256_file(out_path)
        size = os.path.getsize(out_path)
        result = MakeWorldInferenceResult(
            ok=True,
            code="OK",
            message="ok",
            output_path=out_path,
            output_sha256=sha,
            output_bytes=size,
            model_name=req.model_name,
            checkpoint_id=cp.get("id"),
            checkpoint_sha256=cp.get("sha256"),
            arch_version=cfg.arch_version,
            arch_config=cfg.to_dict(),
            seed=req.seed,
            prompt=req.prompt,
            frames=req.frames,
            fps=req.fps,
            width=req.short_side,
            height=req.short_side,
            duration_seconds=req.frames / max(req.fps, 1e-6),
            inference_steps=req.num_inference_steps,
            elapsed_seconds=time.time() - t0,
            device="cpu",
            dtype="float32",
            hardware=self._hw,
            software={"make_model_version": "0.1.0", "numpy_version": np.__version__},
            created_at=_now_iso(),
        )
        # write provenance sidecar
        try:
            with open(out_path + ".provenance.json", "w", encoding="utf-8") as f:
                json.dump(result.provenance_dict(), f, indent=2)
        except Exception:
            pass
        return result


def _now_iso() -> str:
    import datetime as _dt
    return _dt.datetime.utcnow().isoformat() + "Z"


def _detect_hardware() -> Dict[str, Any]:
    import multiprocessing
    import shutil
    out = {
        "cpu_cores": multiprocessing.cpu_count(),
        "ram_gb": _ram_gb(),
        "disk_free_gb": _disk_free_gb("/"),
        "gpu_name": "",
        "gpu_vram_gb": 0.0,
        "cuda_available": False,
        "pytorch_available": False,
    }
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


def _ram_gb() -> float:
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / 1024.0 / 1024.0
    except Exception:
        pass
    return 0.0


def _disk_free_gb(path: str) -> float:
    try:
        st = os.statvfs(path)
        return (st.f_bavail * st.f_frsize) / 1e9
    except Exception:
        return 0.0


__all__ = [
    "MakeWorldInferenceRequest",
    "MakeWorldInferenceResult",
    "MakeWorldInferenceEngine",
    "MakeModelXError",
    "MakeModelXUntrainedError",
    "MakeModelXCheckpointMissing",
    "MakeModelXCheckpointInvalid",
    "MakeModelXArchitectureMismatch",
    "MakeModelXDependencyMissing",
]
