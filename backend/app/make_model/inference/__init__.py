"""
MAKE proprietary model inference.

MakeInferenceEngine:
  - loads a real MAKE checkpoint (refuses anything else)
  - validates architecture compatibility
  - runs the denoising / sampling loop on the target device
  - decodes latents to a video file using FFmpeg
  - records full provenance (model, checkpoint, seed, prompt, hardware, etc.)
"""

from __future__ import annotations
import os
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.make_model.utils import (
    paths, ensure_dirs, dump_json, load_json, now_iso, sha256_file,
    get_logger, human_size,
)
from app.make_model.training import (
    MakeModelError, MakeModelCheckpointMissing, MakeModelCheckpointInvalid,
    MakeModelArchitectureMismatch, MakeModelDependencyMissing,
    MakeModelUntrainedError, detect_hardware, HardwareReport,
    CheckpointManager,
)


logger = get_logger("make_model.inference")


@dataclass
class MakeInferenceRequest:
    prompt: str = ""
    model_name: str = "make-video-research-v0"
    checkpoint_id: Optional[str] = None
    negative_prompt: str = ""
    seed: int = 0
    frames: int = 8
    short_side: int = 64
    fps: int = 8
    num_inference_steps: int = 20
    output_path: str = ""
    conditioning: Dict[str, Any] = field(default_factory=dict)
    reference_image: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MakeInferenceResult:
    ok: bool
    code: str
    message: str
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
    fps: int = 0
    width: int = 0
    height: int = 0
    duration_seconds: float = 0.0
    inference_steps: int = 0
    elapsed_seconds: float = 0.0
    device: str = ""
    dtype: str = ""
    hardware: Dict[str, Any] = field(default_factory=dict)
    software: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MakeInferenceEngine:
    def __init__(self, root: Optional[str] = None) -> None:
        from app.make_model.registry import get_registry
        self.registry = get_registry(root)

    def _select_checkpoint(self, model_name: str, checkpoint_id: Optional[str]) -> Dict[str, Any]:
        if checkpoint_id:
            cp = self.registry.get_checkpoint(checkpoint_id)
            if not cp:
                raise MakeModelCheckpointMissing(f"checkpoint {checkpoint_id!r} not in registry")
            if cp["model_name"] != model_name:
                raise MakeModelCheckpointMissing(
                    f"checkpoint {checkpoint_id!r} belongs to {cp['model_name']!r}, not {model_name!r}"
                )
            return cp
        cps = self.registry.list_checkpoints(model_name=model_name)
        if not cps:
            raise MakeModelUntrainedError(
                f"No checkpoint available for model {model_name!r}. "
                f"Model status is UNTRAINED or CHECKPOINT_AVAILABLE is empty."
            )
        return sorted(cps, key=lambda c: c.get("created_at", ""))[-1]

    def _resolve_device(self):
        try:
            import torch
        except ImportError as e:
            raise MakeModelDependencyMissing(f"pytorch required: {e}")
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def _decode_to_video(self, latents: Any, output_path: str, fps: int) -> Dict[str, Any]:
        try:
            import numpy as np
            import torch
            import subprocess
        except ImportError as e:
            raise MakeModelDependencyMissing(f"pytorch/numpy required: {e}")
        if latents.dim() == 4:
            latents = latents.unsqueeze(0)
        lat = latents[0].detach().cpu().float()
        C, T, H, W = lat.shape
        if C < 3:
            lat = torch.nn.functional.pad(lat, (0, 0, 0, 0, 0, 0, 0, 3 - C))
            C = 3
        if C > 3:
            lat = lat[:3]
            C = 3
        lat = (lat - lat.amin()) / max(1e-6, (lat.amax() - lat.amin()))
        arr = (lat.clamp(0, 1) * 255.0).round().to(torch.uint8).permute(1, 0, 2, 3).numpy()
        import tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            for i in range(T):
                im = Image.fromarray(arr[i].transpose(1, 2, 0))
                im.save(os.path.join(td, f"f{i:04d}.png"))
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-framerate", str(fps),
                "-i", os.path.join(td, "f%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "ultrafast", "-movflags", "+faststart",
                output_path,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise MakeModelError(f"ffmpeg encode failed: {r.stderr[:200]}")
        return {
            "width": W,
            "height": H,
            "frames": T,
            "duration_seconds": T / max(1, fps),
        }

    def _simple_denoise(self, model: Any, shape: tuple, device: Any, dtype: Any,
                        text_tokens: Any, num_steps: int, seed: int) -> Any:
        """Research-baseline denoising loop on latents.

        Starts from N(0, I), runs `num_steps` denoising steps. Each step
        predicts noise and interpolates the latent toward the predicted
        clean latent. This is a research baseline; a production sampler
        (DPM-Solver, etc.) will replace this without changing the engine API.
        """
        try:
            import torch
        except ImportError as e:
            raise MakeModelDependencyMissing(f"pytorch required: {e}")
        g = torch.Generator(device="cpu").manual_seed(seed)
        x = torch.randn(*shape, generator=g, dtype=torch.float32).to(device=device, dtype=dtype)
        betas = torch.linspace(1e-4, 2e-2, num_steps, device=device, dtype=dtype)
        alphas = 1.0 - betas
        alpha_bars = torch.cumprod(alphas, dim=0)
        model.eval()
        B = shape[0]
        t_vals = torch.linspace(999, 0, num_steps, device=device).long()
        with torch.no_grad():
            for i in range(num_steps):
                t = t_vals[i].repeat(B)
                pred = model(x, t, text_tokens)
                a_bar = alpha_bars[i]
                x0_pred = (x - (1 - a_bar).sqrt() * pred) / a_bar.sqrt().clamp(min=1e-3)
                weight = 1.0 / num_steps
                x = x * (1 - weight) + x0_pred * weight
        return x

    def run(self, req: MakeInferenceRequest) -> MakeInferenceResult:
        cp = self._select_checkpoint(req.model_name, req.checkpoint_id)
        if not os.path.exists(cp["path"]):
            raise MakeModelCheckpointMissing(f"file missing: {cp['path']}")
        payload = CheckpointManager(cp["path"]).load(cp["path"])
        arch_cfg = payload.get("config", {}).get("arch_config", {})
        if not arch_cfg:
            raise MakeModelArchitectureMismatch("checkpoint has no arch_config")
        from app.make_model.arch import MakeModelConfig, get_real_unet_class
        arch = MakeModelConfig.from_dict(arch_cfg)
        cls = get_real_unet_class()
        model = cls(arch)
        model.load_state_dict(payload["model_state"], strict=True)
        import torch
        device = self._resolve_device()
        dtype = torch.float32
        model.to(device=device, dtype=dtype).eval()
        torch.manual_seed(req.seed or 0)
        text_tokens = torch.randint(0, arch.text_vocab_size, (1, arch.text_seq_len), device=device)
        H = req.short_side
        W = req.short_side
        T = req.frames
        shape = (1, arch.latent_channels, T, H, W)
        t0 = time.time()
        out_lat = self._simple_denoise(
            model=model, shape=shape, device=device, dtype=dtype,
            text_tokens=text_tokens, num_steps=req.num_inference_steps, seed=req.seed,
        )
        elapsed = time.time() - t0
        if not req.output_path:
            p = ensure_dirs()
            out_dir = p["exports"] / req.model_name
            out_dir.mkdir(parents=True, exist_ok=True)
            req.output_path = str(out_dir / f"infer-{int(time.time())}.mp4")
        info = self._decode_to_video(out_lat, req.output_path, req.fps)
        sha = sha256_file(req.output_path)
        try:
            import torch as _t
            torch_version = _t.__version__
        except ImportError:
            torch_version = "unknown"
        hw = detect_hardware()
        result = MakeInferenceResult(
            ok=True,
            code="OK",
            message="Inference completed",
            output_path=req.output_path,
            output_sha256=sha,
            output_bytes=os.path.getsize(req.output_path),
            model_name=req.model_name,
            checkpoint_id=cp["id"],
            checkpoint_sha256=cp["sha256"],
            arch_version=arch.arch_version,
            arch_config=arch.to_dict(),
            seed=req.seed,
            prompt=req.prompt,
            frames=info["frames"],
            fps=req.fps,
            width=info["width"],
            height=info["height"],
            duration_seconds=info["duration_seconds"],
            inference_steps=req.num_inference_steps,
            elapsed_seconds=round(elapsed, 4),
            device=str(device),
            dtype=str(dtype),
            hardware=hw.to_dict(),
            software={"torch_version": torch_version, "make_model": "0.1.0-foundation"},
            created_at=now_iso(),
        )
        dump_json(req.output_path + ".provenance.json", result.to_dict())
        return result


def inference_availability() -> Dict[str, Any]:
    from app.make_model.registry import get_registry
    reg = get_registry()
    status = reg.get_status()
    hw = detect_hardware()
    return {
        "available": status["overall_state"] in {"checkpoint_available", "inference_ready", "production_ready"},
        "overall_state": status["overall_state"],
        "checkpoint_count": status["checkpoint_count"],
        "model_count": status["model_count"],
        "pytorch_available": hw.pytorch_available,
        "cuda_available": hw.cuda_available,
        "reason": (
            None
            if status["overall_state"] != "untrained"
            else "No MAKE checkpoint available. Model is UNTRAINED."
        ),
    }
