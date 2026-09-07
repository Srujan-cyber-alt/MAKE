"""
Inference / sampling for the MAKE image subsystem (CPU, NumPy).

Loads a MAKE checkpoint (.npz) and runs the standard DDPM reverse
process. The output is a real PNG/JPEG image written to disk — no
upscaling, no third-party API.

Capabilities:
  - Text-conditioned sampling (prompt embedding)
  - Image-to-image: encode an input image to latents, add controlled
    noise, run partial reverse process. Output is genuinely
    conditioned on the input image.
  - Batch sampling: produce N independent samples in one call.
  - Native resolution sampling: image_size must match the
    checkpoint's training resolution (or a multiple supported by
    the architecture). Resolution is never upscaled beyond native.
"""

from __future__ import annotations

import os
import time
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional, List

import numpy as np
from PIL import Image

from app.make_model.utils import (
    ensure_dirs, dump_json, load_json, now_iso, sha256_file, get_logger,
)
from app.make_model.image.arch.unet import NumpyUNet, NumpyUNetConfig, count_params
from app.make_model.image.arch.diffusion import GaussianDiffusion


logger = get_logger("make_model.image.sampler")


@dataclass
class SamplerConfig:
    model_name: str = "make-image-research-v0"
    checkpoint_path: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    seed: int = 0
    num_inference_steps: int = 25
    image_size: int = 32
    output_path: str = ""
    output_format: str = "png"  # 'png' or 'jpeg'
    arch_version: str = "make-image-cpu-unet-v1"
    # Image-to-image parameters
    init_image_path: str = ""
    init_strength: float = 0.6  # 0=noise (no init), 1=keep init almost intact
    # Batch parameters
    batch_size: int = 1
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SampleResult:
    ok: bool
    code: str
    message: str
    output_path: str = ""
    output_sha256: str = ""
    output_bytes: int = 0
    width: int = 0
    height: int = 0
    channels: int = 0
    model_name: str = ""
    checkpoint_path: str = ""
    checkpoint_sha256: str = ""
    arch_version: str = ""
    arch_config: Dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    prompt: str = ""
    inference_steps: int = 0
    elapsed_seconds: float = 0.0
    hardware: Dict[str, Any] = field(default_factory=dict)
    software: Dict[str, Any] = field(default_factory=dict)
    generation_resolution_native: int = 0
    refinement_resolution_native: int = 0
    interpolation_note: str = ""
    kind: str = "text_to_image"
    init_image_sha256: str = ""
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _hw() -> Dict[str, Any]:
    info = {"device": "cpu", "accelerator": "none", "cuda_available": False, "pytorch_available": False,
            "cpu_count": os.cpu_count()}
    try:
        import psutil  # type: ignore
        info["total_memory_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass
    return info


class ImageSampler:
    def __init__(self, out_root: Optional[str] = None):
        self.paths = ensure_dirs(out_root)
        self.exports_dir = self.paths["exports"] / "images"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def _load_model_state(self, checkpoint_path: str):
        if not os.path.exists(checkpoint_path):
            raise FileNotFoundError(f"checkpoint not found: {checkpoint_path}")
        with np.load(checkpoint_path, allow_pickle=True) as data:
            files = set(data.files)
            arch_cfg = {}
            for k in files:
                if k.startswith("archcfg::"):
                    name = k[len("archcfg::"):]
                    val = data[k]
                    if hasattr(val, "item") and val.ndim == 0:
                        try:
                            v = val.item()
                            if isinstance(v, bytes):
                                v = v.decode("utf-8")
                            arch_cfg[name] = v
                        except Exception:
                            arch_cfg[name] = val.tolist()
                    elif val.ndim == 0:
                        arch_cfg[name] = val.tolist()
                    else:
                        arch_cfg[name] = val.tolist()
            model_state = {k[len("state::"):]: np.asarray(data[k])
                           for k in files if k.startswith("state::")}
        if not arch_cfg or not model_state:
            raise RuntimeError(
                f"Checkpoint {checkpoint_path} has no arch_config/model_state"
            )
        return arch_cfg, model_state

    def _build_model(self, arch_cfg: Dict[str, Any], model_state: Dict[str, Any]) -> NumpyUNet:
        cfg_arch = NumpyUNetConfig.from_dict(dict(arch_cfg))
        model = NumpyUNet(cfg_arch, seed=0)
        model.load_state_dict(model_state, strict=True)
        return model, cfg_arch

    def sample(self, cfg: SamplerConfig) -> SampleResult:
        arch_cfg, model_state = self._load_model_state(cfg.checkpoint_path)
        model, cfg_arch = self._build_model(arch_cfg, model_state)
        model.rng = np.random.default_rng(cfg.seed)

        diffusion = GaussianDiffusion(num_timesteps=cfg_arch.num_timesteps)
        T = diffusion.T
        n = max(1, min(int(cfg.num_inference_steps), T))

        rng = np.random.default_rng(cfg.seed)
        init_sha = ""
        kind = "text_to_image"

        # Image-to-image mode: encode the input image, add noise according to init_strength
        if cfg.init_image_path:
            kind = "image_to_image"
            if not os.path.exists(cfg.init_image_path):
                return SampleResult(ok=False, code="INIT_IMAGE_MISSING",
                                    message=f"init_image_path not found: {cfg.init_image_path}")
            init_sha = sha256_file(cfg.init_image_path)
            with Image.open(cfg.init_image_path) as im:
                im = im.convert("RGB").resize((cfg.image_size, cfg.image_size), Image.BILINEAR)
                init_arr = (np.asarray(im, dtype=np.float32) / 255.0).transpose(2, 0, 1)
            x0 = (init_arr * 2.0 - 1.0)[None, ...].astype(np.float32)
            t_start = max(0, min(int(round((1.0 - max(0.0, min(1.0, cfg.init_strength))) * (T - 1))), T - 1))
            noise = rng.standard_normal(x0.shape).astype(np.float32)
            xt = diffusion.q_sample(x0, np.array([t_start] * 1, dtype=np.int64), noise)
            step_indices = np.linspace(t_start, 0, n, dtype=np.int64)
        else:
            xt = rng.standard_normal((1, 3, cfg.image_size, cfg.image_size)).astype(np.float32)
            step_indices = np.linspace(T - 1, 0, n, dtype=np.int64)

        t0 = time.time()
        for i in range(n):
            t_now = int(step_indices[i])
            t_in = np.array([t_now] * 1, dtype=np.int64)
            eps_pred = model.forward(xt, t_in, prompt=cfg.prompt)
            if t_now == 0:
                sab = float(diffusion.sqrt_alpha_bars[0])
                somab = float(diffusion.sqrt_one_minus_alpha_bars[0])
                xt = (xt - somab * eps_pred) / max(sab, 1e-3)
                break
            beta_t = float(diffusion.betas[t_now])
            alpha_t = float(diffusion.alphas[t_now])
            alpha_bar_t = float(diffusion.alpha_bars[t_now])
            sab = np.sqrt(alpha_bar_t)
            somab = np.sqrt(1.0 - alpha_bar_t)
            x0_pred = (xt - somab * eps_pred) / max(sab, 1e-3)
            mean = (np.sqrt(alpha_t) * (1.0 - diffusion.alpha_bars[t_now - 1]) / max(1.0 - alpha_bar_t, 1e-6)) * x0_pred \
                   + (np.sqrt(diffusion.alpha_bars[t_now - 1]) * beta_t / max(1.0 - alpha_bar_t, 1e-6)) * xt
            var = beta_t * (1.0 - diffusion.alpha_bars[t_now - 1]) / max(1.0 - alpha_bar_t, 1e-6)
            noise = rng.standard_normal(xt.shape).astype(np.float32)
            xt = mean + np.sqrt(var) * noise
        elapsed = time.time() - t0

        x = (xt[0] + 1.0) * 0.5
        x = np.clip(x, 0.0, 1.0)
        arr = (x * 255.0).round().astype(np.uint8).transpose(1, 2, 0)

        if not cfg.output_path:
            ext = "jpg" if cfg.output_format.lower() in ("jpeg", "jpg") else "png"
            cfg.output_path = str(self.exports_dir / f"{cfg.model_name}-seed{cfg.seed}-{int(time.time())}.{ext}")
        Path(cfg.output_path).parent.mkdir(parents=True, exist_ok=True)
        im = Image.fromarray(arr, mode="RGB")
        if cfg.output_format.lower() in ("jpeg", "jpg"):
            im.save(cfg.output_path, format="JPEG", quality=92)
        else:
            im.save(cfg.output_path, format="PNG")
        sha = sha256_file(cfg.output_path)

        result = SampleResult(
            ok=True,
            code="OK",
            message="Sample complete.",
            output_path=cfg.output_path,
            output_sha256=sha,
            output_bytes=os.path.getsize(cfg.output_path),
            width=int(arr.shape[1]),
            height=int(arr.shape[0]),
            channels=3,
            model_name=cfg.model_name,
            checkpoint_path=cfg.checkpoint_path,
            checkpoint_sha256=sha256_file(cfg.checkpoint_path),
            arch_version=cfg_arch.arch_version,
            arch_config=cfg_arch.to_dict(),
            seed=cfg.seed,
            prompt=cfg.prompt,
            inference_steps=n,
            elapsed_seconds=round(elapsed, 4),
            hardware=_hw(),
            software={"framework": "numpy", "make_model": "0.2.0-image"},
            generation_resolution_native=cfg.image_size,
            refinement_resolution_native=0,
            interpolation_note=(
                f"Generated natively at {cfg.image_size}x{cfg.image_size} pixels. "
                "No upscaling or external model used. To obtain a larger image, "
                "increase image_size and retrain; we do not interpolate the "
                "checkpoint to claim a larger generation resolution."
            ),
            kind=kind,
            init_image_sha256=init_sha,
            created_at=now_iso(),
        )
        dump_json(cfg.output_path + ".provenance.json", result.to_dict())
        return result

    def sample_batch(self, cfg: SamplerConfig, count: int) -> List[SampleResult]:
        """Generate `count` independent samples in one call."""
        out: List[SampleResult] = []
        base_seed = cfg.seed
        base_output = cfg.output_path
        for i in range(count):
            cfg_i = SamplerConfig(**{**cfg.to_dict(), "seed": base_seed + i})
            if base_output:
                cfg_i.output_path = base_output.replace(".png", f"-{i}.png").replace(".jpg", f"-{i}.jpg")
            out.append(self.sample(cfg_i))
        return out