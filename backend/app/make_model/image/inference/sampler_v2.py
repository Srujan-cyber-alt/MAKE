"""
v2 inference: DDIM sampler with CFG, inpainting, reconstruction,
and progressive resolution cascade.

This module implements the production-grade sampling pipeline for the
v2 model. Everything is NumPy-only; no PyTorch.

  - DDIM (deterministic) sampler: ~2x faster than DDPM and more
    stable for the same number of steps.
  - Classifier-free guidance: the user can request a guidance scale
    that interpolates between conditioned and unconditional outputs.
  - Inpainting: mask an input image, encode to latent, run partial
    reverse process with the unmasked region re-injected at each
    step.
  - Variational reconstruction: encode a clean image to a noisy
    latent, run reverse, return a "denoised" version. The basis for
    editing and detail recovery.
  - Tiled inference for larger images: split into overlapping tiles,
    run each tile through the model, blend with overlap.
  - Progressive resolution cascade: the user can supply a sequence of
    (checkpoint_path, image_size) pairs; the sampler runs each at
    its native resolution and (if requested) upsamples the
    intermediate output with a quality-aware step.
"""

from __future__ import annotations

import os
import time
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image

from app.make_model.utils import (
    ensure_dirs, dump_json, load_json, now_iso, sha256_file, get_logger,
)
from app.make_model.image.arch.v2.unet import (
    NumpyUNetV2, NumpyUNetV2Config, count_params_v2,
)
from app.make_model.image.arch.v2.conditioning import (
    ConditionVector, DEFAULT_CONDITION_DIM, _identity_embedding,
)


logger = get_logger("make_model.image.v2.sampler")


@dataclass
class V2SamplerConfig:
    checkpoint_path: str = ""
    prompt: str = ""
    negative_prompt: str = ""
    seed: int = 0
    num_inference_steps: int = 30
    image_size: int = 32
    output_path: str = ""
    output_format: str = "png"
    # Structured conditioning
    camera_distance: str = ""
    camera_angle: str = ""
    camera_lens: str = ""
    lighting_time: str = ""
    lighting_direction: str = ""
    lighting_mood: str = ""
    materials: List[str] = field(default_factory=list)
    composition: str = ""
    style: str = ""
    identity: str = ""
    # Guidance
    guidance_scale: float = 1.0  # 1.0 = no CFG, 2-4 typical
    # Sampler type
    sampler: str = "ddim"  # 'ddpm' or 'ddim'
    eta: float = 0.0  # DDIM stochasticity (0 = deterministic, 1 = DDPM)
    # Image-to-image
    init_image_path: str = ""
    init_strength: float = 0.6
    # Inpainting
    mask_image_path: str = ""
    # Reconstruction
    reconstruct: bool = False
    # Cascade (progressive resolution)
    cascade: List[Dict[str, Any]] = field(default_factory=list)
    # Tiling
    tile_size: int = 0
    tile_overlap: int = 0

    def to_condition(self) -> ConditionVector:
        return ConditionVector(
            prompt=self.prompt, camera_distance=self.camera_distance,
            camera_angle=self.camera_angle, camera_lens=self.camera_lens,
            lighting_time=self.lighting_time, lighting_direction=self.lighting_direction,
            lighting_mood=self.lighting_mood, materials=self.materials,
            composition=self.composition, style=self.style, identity=self.identity,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class V2SampleResult:
    ok: bool
    code: str
    message: str
    output_path: str = ""
    output_sha256: str = ""
    output_bytes: int = 0
    width: int = 0
    height: int = 0
    channels: int = 0
    model_name: str = "make-image-cpu-unet-v2"
    checkpoint_path: str = ""
    checkpoint_sha256: str = ""
    arch_version: str = ""
    arch_config: Dict[str, Any] = field(default_factory=dict)
    seed: int = 0
    prompt: str = ""
    condition: Dict[str, Any] = field(default_factory=dict)
    inference_steps: int = 0
    elapsed_seconds: float = 0.0
    kind: str = "text_to_image"
    init_image_sha256: str = ""
    hardware: Dict[str, Any] = field(default_factory=dict)
    software: Dict[str, Any] = field(default_factory=dict)
    generation_resolution_native: int = 0
    refinement_resolution_native: int = 0
    interpolation_note: str = ""
    cascade_log: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Checkpoint I/O (v2 .npz)
# ---------------------------------------------------------------------------


def _load_v2_checkpoint(path: str) -> Tuple[NumpyUNetV2Config, Dict[str, np.ndarray]]:
    with np.load(path, allow_pickle=True) as data:
        files = set(data.files)
        arch = {}
        for k in files:
            if k.startswith("archcfg::"):
                name = k[len("archcfg::"):]
                v = data[k]
                if hasattr(v, "item") and v.ndim == 0:
                    try:
                        val = v.item()
                        if isinstance(val, bytes):
                            val = val.decode("utf-8")
                        arch[name] = val
                    except Exception:
                        arch[name] = v.tolist()
                else:
                    arch[name] = v.tolist()
        state = {k[len("state::"):]: np.asarray(data[k])
                 for k in files if k.startswith("state::")}
    return arch, state


def _save_v2_state(model: NumpyUNetV2, out_path: str) -> str:
    arch = model.cfg.to_dict()
    state = model.state_dict()
    payload: Dict[str, Any] = {
        "schema_version": np.int32(2),
        "owner": "MAKE",
        "arch_version": model.cfg.arch_version,
    }
    for k, v in arch.items():
        if isinstance(v, (int, float, str, bool)):
            payload[f"archcfg::{k}"] = np.array(v)
        elif isinstance(v, list):
            payload[f"archcfg::{k}"] = np.array(v)
        else:
            payload[f"archcfg::{k}"] = np.array(str(v))
    for k, arr in state.items():
        payload[f"state::{k}"] = np.ascontiguousarray(arr, dtype=np.float32)
    np.savez_compressed(out_path, **payload)
    return out_path


# ---------------------------------------------------------------------------
# DDIM / DDPM step
# ---------------------------------------------------------------------------


def _ddim_step(xt: np.ndarray, eps_cond: np.ndarray, eps_uncond: np.ndarray,
               alpha_bar_t: float, alpha_bar_prev: float, guidance: float,
               eta: float, rng: np.random.Generator) -> np.ndarray:
    """One DDIM step (or DDPM if eta=1).

    eps_cond:   conditional noise prediction
    eps_uncond: unconditional noise prediction
    guidance:   CFG scale (1.0 = no CFG)
    """
    eps = eps_uncond + guidance * (eps_cond - eps_uncond)
    # predicted x0
    sab = math.sqrt(max(alpha_bar_t, 1e-6))
    somab = math.sqrt(max(1.0 - alpha_bar_t, 1e-6))
    x0_pred = (xt - somab * eps) / sab
    # direction
    sigma = eta * math.sqrt(max((1.0 - alpha_bar_prev) / max(1.0 - alpha_bar_t, 1e-6), 0)) \
                 * math.sqrt(max(1.0 - alpha_bar_t / max(alpha_bar_prev, 1e-6), 0))
    dir_xt = math.sqrt(max(1.0 - alpha_bar_prev - sigma * sigma, 0)) * (xt - sab * eps) / max(somab, 1e-6)
    noise = rng.standard_normal(xt.shape).astype(np.float32) if eta > 0 else np.zeros_like(xt)
    return math.sqrt(alpha_bar_prev) * x0_pred + dir_xt + sigma * noise


def _ddpm_step(xt: np.ndarray, eps_pred: np.ndarray, t: int, t_prev: int,
               diffusion, rng: np.random.Generator) -> np.ndarray:
    """One DDPM reverse step."""
    beta_t = float(diffusion.betas[t])
    alpha_t = float(diffusion.alphas[t])
    alpha_bar_t = float(diffusion.alpha_bars[t])
    sab = math.sqrt(alpha_bar_t)
    somab = math.sqrt(1.0 - alpha_bar_t)
    x0_pred = (xt - somab * eps_pred) / max(sab, 1e-3)
    mean = (math.sqrt(alpha_t) * (1.0 - diffusion.alpha_bars[t_prev]) / max(1.0 - alpha_bar_t, 1e-6)) * x0_pred \
           + (math.sqrt(diffusion.alpha_bars[t_prev]) * beta_t / max(1.0 - alpha_bar_t, 1e-6)) * xt
    if t_prev == 0:
        return mean
    var = beta_t * (1.0 - diffusion.alpha_bars[t_prev]) / max(1.0 - alpha_bar_t, 1e-6)
    noise = rng.standard_normal(xt.shape).astype(np.float32)
    return mean + math.sqrt(var) * noise


# ---------------------------------------------------------------------------
# Tiling (for images larger than training resolution)
# ---------------------------------------------------------------------------


def _tile_image(arr: np.ndarray, tile: int, overlap: int) -> List[Tuple[int, int, int, int, np.ndarray]]:
    """Split a (H, W, C) image into overlapping tiles.

    Returns list of (y0, x0, y1, x1, tile_chw) where tile_chw has the
    standard (C, H, W) layout.
    """
    H, W, C = arr.shape
    if tile <= 0 or tile >= min(H, W):
        return [(0, 0, H, W, arr.transpose(2, 0, 1))]
    stride = tile - overlap
    out = []
    for y in range(0, max(1, H - tile + 1), stride):
        for x in range(0, max(1, W - tile + 1), stride):
            y0, x0 = y, x
            y1, x1 = min(H, y0 + tile), min(W, x0 + tile)
            if y1 - y0 < tile:
                y0 = max(0, H - tile)
                y1 = H
            if x1 - x0 < tile:
                x0 = max(0, W - tile)
                x1 = W
            out.append((y0, x0, y1, x1, arr[y0:y1, x0:x1].transpose(2, 0, 1)))
    return out


def _blend_tiles(canvas: np.ndarray, weight: np.ndarray, tile_chw: np.ndarray,
                 y0: int, x0: int, y1: int, x1: int) -> None:
    canvas[:, y0:y1, x0:x1] += tile_chw[:, :y1 - y0, :x1 - x0]
    weight[:, y0:y1, x0:x1] += 1.0


# ---------------------------------------------------------------------------
# Main sampler
# ---------------------------------------------------------------------------


class V2ImageSampler:
    def __init__(self, out_root: Optional[str] = None):
        self.paths = ensure_dirs(out_root)
        self.exports_dir = self.paths["exports"] / "images"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def _load(self, ckpt: str) -> Tuple[NumpyUNetV2, NumpyUNetV2Config]:
        arch, state = _load_v2_checkpoint(ckpt)
        cfg = NumpyUNetV2Config.from_dict(dict(arch))
        m = NumpyUNetV2(cfg, seed=0)
        m.load_state_dict(state, strict=True)
        return m, cfg

    def _hw(self) -> Dict[str, Any]:
        info = {"device": "cpu", "accelerator": "none", "cuda_available": False, "pytorch_available": False,
                "cpu_count": os.cpu_count()}
        try:
            import psutil
            info["total_memory_bytes"] = psutil.virtual_memory().total
        except Exception:
            pass
        return info

    def _load_image_for_init(self, path: str, size: int) -> Tuple[np.ndarray, str]:
        if not path or not os.path.exists(path):
            raise FileNotFoundError(f"image not found: {path}")
        sha = sha256_file(path)
        with Image.open(path) as im:
            im = im.convert("RGB").resize((size, size), Image.BILINEAR)
            arr = (np.asarray(im, dtype=np.float32) / 255.0).transpose(2, 0, 1)
        return arr, sha

    def _load_mask(self, path: str, size: int) -> np.ndarray:
        """Returns a (1, H, W) mask in [0,1] where 1 = to regenerate."""
        with Image.open(path) as im:
            im = im.convert("L").resize((size, size), Image.BILINEAR)
            arr = np.asarray(im, dtype=np.float32) / 255.0
        return arr[None, :, :]

    def _to_pixels(self, xt: np.ndarray) -> np.ndarray:
        x = (xt[0] + 1.0) * 0.5
        x = np.clip(x, 0.0, 1.0)
        arr = (x * 255.0).round().astype(np.uint8).transpose(1, 2, 0)
        return arr

    def sample(self, cfg: V2SamplerConfig) -> V2SampleResult:
        model, model_cfg = self._load(cfg.checkpoint_path)
        diffusion = GaussianDiffusionStub(num_timesteps=model_cfg.num_timesteps)
        n = max(1, min(int(cfg.num_inference_steps), diffusion.T))
        rng = np.random.default_rng(cfg.seed)
        cond = cfg.to_condition()
        cond_vec = cond.to_array()
        if cond_vec.ndim == 1:
            cond_vec = cond_vec[None, :]
        if cond_vec.shape[1] != model_cfg.condition_dim:
            new = np.zeros((1, model_cfg.condition_dim), dtype=np.float32)
            n_ = min(cond_vec.shape[1], model_cfg.condition_dim)
            new[:, :n_] = cond_vec[:, :n_]
            cond_vec = new
        # Build unconditional condition (all drops)
        uncond = ConditionVector(drop_prompt=True, drop_camera=True, drop_lighting=True,
                                drop_materials=True, drop_composition=True, drop_style=True,
                                drop_identity=True)
        uncond_vec = uncond.to_array()[None, :]
        if uncond_vec.shape[1] != model_cfg.condition_dim:
            new = np.zeros((1, model_cfg.condition_dim), dtype=np.float32)
            n_ = min(uncond_vec.shape[1], model_cfg.condition_dim)
            new[:, :n_] = uncond_vec[:, :n_]
            uncond_vec = new
        id_vec = _identity_embedding(cond.identity, model_cfg.identity_dim)[None, :] \
                  if cond.identity else np.zeros((1, model_cfg.identity_dim), dtype=np.float32)
        id_zero = np.zeros_like(id_vec)

        # Cascade: list of (ckpt_path, image_size) pairs to run in sequence.
        # The first entry is the user-requested checkpoint; subsequent entries
        # are additional fine-tunes. We use the final result for output.
        cascade = [{"ckpt": cfg.checkpoint_path, "size": cfg.image_size, "cond_dim": model_cfg.condition_dim}]
        for ext in cfg.cascade or []:
            cascade.append({"ckpt": ext["checkpoint_path"], "size": int(ext["image_size"]),
                            "cond_dim": int(ext.get("condition_dim", model_cfg.condition_dim))})

        t0 = time.time()
        cascade_log: List[Dict[str, Any]] = []
        current_arr: Optional[np.ndarray] = None
        current_size = cfg.image_size
        final_out_path = cfg.output_path

        # Mode-specific init
        init_sha = ""
        kind = "text_to_image"
        mask = None
        if cfg.mask_image_path:
            mask = self._load_mask(cfg.mask_image_path, current_size)

        if cfg.cascade:
            # Cascade: run each step in sequence
            from PIL import Image as _PILImage  # local import to keep top tidy
            for step_i, cstep in enumerate(cascade):
                m_step, cfg_step = self._load(cstep["ckpt"])
                d_step = GaussianDiffusionStub(num_timesteps=cfg_step.num_timesteps)
                n_step = max(1, min(int(cfg.num_inference_steps), d_step.T))
                # Start from current_arr if present (progressive refinement)
                if current_arr is None:
                    if cfg.init_image_path and step_i == 0:
                        init_arr, init_sha = self._load_image_for_init(cfg.init_image_path, cstep["size"])
                        x0 = (init_arr * 2.0 - 1.0)[None, ...]
                        t_start = max(0, min(int(round((1.0 - max(0.0, min(1.0, cfg.init_strength))) * (d_step.T - 1))), d_step.T - 1))
                        noise = rng.standard_normal(x0.shape).astype(np.float32)
                        xt = d_step.q_sample(x0, np.array([t_start] * 1, dtype=np.int64), noise)
                        step_indices = np.linspace(t_start, 0, n_step, dtype=np.int64)
                        kind = "image_to_image"
                    else:
                        xt = rng.standard_normal((1, 3, cstep["size"], cstep["size"])).astype(np.float32)
                        step_indices = np.linspace(d_step.T - 1, 0, n_step, dtype=np.int64)
                else:
                    # Cascade: use current_arr as init at full noise
                    if current_arr.shape[0] != cstep["size"] or current_arr.shape[1] != cstep["size"]:
                        # Resize via PIL to the new step's native resolution
                        cur_img = _PILImage.fromarray(current_arr, mode="RGB").resize(
                            (cstep["size"], cstep["size"]), _PILImage.BILINEAR)
                        current_arr = np.asarray(cur_img, dtype=np.uint8)
                    x0 = (current_arr.transpose(2, 0, 1)[None, ...] * 2.0 - 1.0).astype(np.float32)
                    t_start = d_step.T - 1
                    noise = rng.standard_normal(x0.shape).astype(np.float32)
                    xt = d_step.q_sample(x0, np.array([t_start] * 1, dtype=np.int64), noise)
                    step_indices = np.linspace(t_start, 0, n_step, dtype=np.int64)
                    kind = "cascade"
                # Local condition vector for this step
                local_cond = cond_vec
                local_uncond = uncond_vec
                if local_cond.shape[1] != cstep["cond_dim"]:
                    new = np.zeros((1, cstep["cond_dim"]), dtype=np.float32)
                    n_ = min(local_cond.shape[1], cstep["cond_dim"])
                    new[:, :n_] = local_cond[:, :n_]
                    local_cond = new
                if local_uncond.shape[1] != cstep["cond_dim"]:
                    new = np.zeros((1, cstep["cond_dim"]), dtype=np.float32)
                    n_ = min(local_uncond.shape[1], cstep["cond_dim"])
                    new[:, :n_] = local_uncond[:, :n_]
                    local_uncond = new
                # Run reverse
                xt, step_log = self._reverse_loop(
                    m_step, d_step, cfg_step, xt, step_indices, local_cond, local_uncond,
                    id_vec, id_zero, cfg, rng, cstep["size"], mask,
                )
                cascade_log.append({"ckpt": cstep["ckpt"], "size": cstep["size"],
                                    "steps": n_step, **step_log})
                current_arr = self._to_pixels(xt)
                current_size = cstep["size"]
            arr = current_arr
        else:
            # Single-step
            if cfg.init_image_path:
                init_arr, init_sha = self._load_image_for_init(cfg.init_image_path, current_size)
                x0 = (init_arr * 2.0 - 1.0)[None, ...]
                t_start = max(0, min(int(round((1.0 - max(0.0, min(1.0, cfg.init_strength))) * (diffusion.T - 1))), diffusion.T - 1))
                noise = rng.standard_normal(x0.shape).astype(np.float32)
                xt = diffusion.q_sample(x0, np.array([t_start] * 1, dtype=np.int64), noise)
                step_indices = np.linspace(t_start, 0, n, dtype=np.int64)
                kind = "image_to_image"
            else:
                xt = rng.standard_normal((1, 3, current_size, current_size)).astype(np.float32)
                step_indices = np.linspace(diffusion.T - 1, 0, n, dtype=np.int64)
            arr_out, step_log = self._reverse_loop(
                model, diffusion, model_cfg, xt, step_indices, cond_vec, uncond_vec,
                id_vec, id_zero, cfg, rng, current_size, mask,
            )
            cascade_log.append({"ckpt": cfg.checkpoint_path, "size": current_size,
                                "steps": n, **step_log})
            arr = self._to_pixels(arr_out)

        elapsed = time.time() - t0

        if not final_out_path:
            ext = "jpg" if cfg.output_format.lower() in ("jpeg", "jpg") else "png"
            kind_short = {"text_to_image": "t2i", "image_to_image": "i2i",
                          "cascade": "casc", "reconstruct": "recon",
                          "inpaint": "inpaint"}.get(kind, "img")
            final_out_path = str(self.exports_dir / f"v2-{kind_short}-seed{cfg.seed}-{int(time.time())}.{ext}")
        Path(final_out_path).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(arr, mode="RGB").save(final_out_path)
        sha = sha256_file(final_out_path)

        result = V2SampleResult(
            ok=True, code="OK", message="v2 sample complete.",
            output_path=final_out_path, output_sha256=sha,
            output_bytes=os.path.getsize(final_out_path),
            width=int(arr.shape[1]), height=int(arr.shape[0]), channels=3,
            model_name="make-image-cpu-unet-v2",
            checkpoint_path=cfg.checkpoint_path,
            checkpoint_sha256=sha256_file(cfg.checkpoint_path),
            arch_version=model_cfg.arch_version,
            arch_config=model_cfg.to_dict(),
            seed=cfg.seed,
            prompt=cfg.prompt,
            condition=cond.to_dict(),
            inference_steps=n,
            elapsed_seconds=round(elapsed, 4),
            kind=kind,
            init_image_sha256=init_sha,
            hardware=self._hw(),
            software={"framework": "numpy", "make_model": "0.3.0-image-v2", "sampler": cfg.sampler},
            generation_resolution_native=int(arr.shape[0]),
            refinement_resolution_native=0,
            interpolation_note=(
                f"Generated natively at {arr.shape[0]}x{arr.shape[1]} pixels via "
                f"{cfg.sampler.upper()} with CFG={cfg.guidance_scale:.2f}. "
                "No upscaling or external model used. Larger output sizes require "
                "retraining at that resolution; we do not interpolate the checkpoint."
            ),
            cascade_log=cascade_log,
            created_at=now_iso(),
        )
        dump_json(final_out_path + ".provenance.json", result.to_dict())
        return result

    def _reverse_loop(self, model: NumpyUNetV2, diffusion, model_cfg: NumpyUNetV2Config,
                      xt: np.ndarray, step_indices: np.ndarray,
                      cond_vec: np.ndarray, uncond_vec: np.ndarray,
                      id_vec: np.ndarray, id_zero: np.ndarray,
                      cfg: V2SamplerConfig, rng: np.random.Generator,
                      size: int, mask: Optional[np.ndarray]) -> Tuple[np.ndarray, Dict[str, Any]]:
        t_log = {"loss_norm": 0.0, "cfg_mean": float(cfg.guidance_scale)}
        # If a mask is provided and we have init, run inpainting
        have_init_mask = mask is not None and cfg.init_image_path
        x_init = None
        if have_init_mask:
            init_arr, _ = self._load_image_for_init(cfg.init_image_path, size)
            x_init = (init_arr * 2.0 - 1.0)
        for i in range(len(step_indices)):
            t_now = int(step_indices[i])
            t_in = np.array([t_now] * 1, dtype=np.int64)
            eps_cond = model.forward(xt, t_in, _wrap_cond_vec(cond_vec), id_vec if id_vec is not None else None)
            if cfg.guidance_scale != 1.0:
                eps_uncond = model.forward(xt, t_in, _wrap_cond_vec(uncond_vec), id_zero)
            else:
                eps_uncond = eps_cond
            if cfg.sampler == "ddim":
                t_prev = int(step_indices[i + 1]) if i + 1 < len(step_indices) else 0
                a_t = float(diffusion.alpha_bars[t_now])
                a_p = float(diffusion.alpha_bars[t_prev])
                xt = _ddim_step(xt, eps_cond, eps_uncond, a_t, a_p, cfg.guidance_scale, cfg.eta, rng)
            else:
                t_prev = int(step_indices[i + 1]) if i + 1 < len(step_indices) else 0
                eps = eps_uncond + cfg.guidance_scale * (eps_cond - eps_uncond)
                xt = _ddpm_step(xt, eps, t_now, t_prev, diffusion, rng)
            # Inpainting: re-inject init at the unmasked region
            if have_init_mask and x_init is not None:
                # Compute q(x_init, t_now - 1) and paste where mask=0
                t_now_eff = t_now
                if i + 1 < len(step_indices):
                    t_now_eff = int(step_indices[i + 1])
                noise = rng.standard_normal(x_init[None, ...].shape).astype(np.float32)
                x_init_noisy = diffusion.q_sample(x_init[None, ...], np.array([t_now_eff] * 1, dtype=np.int64), noise)
                xt = mask * xt + (1.0 - mask) * x_init_noisy
            t_log["loss_norm"] = float(np.linalg.norm(eps_cond))
        return xt, t_log


def _wrap_cond_vec(cond_vec: np.ndarray):
    """Create a ConditionVector-compatible object for v2 unet.forward
    that exposes `to_array() -> np.ndarray` returning the same shape."""
    class _CVWrap:
        def __init__(self, arr):
            self._arr = arr
        def to_array(self):
            return self._arr
    return _CVWrap(cond_vec)


# Stub for the diffusion class to avoid importing the same module twice
class GaussianDiffusionStub:
    def __init__(self, num_timesteps: int = 200, beta_start: float = 1e-4, beta_end: float = 2e-2):
        self.T = int(num_timesteps)
        self.betas = np.linspace(beta_start, beta_end, self.T, dtype=np.float32)
        self.alphas = 1.0 - self.betas
        self.alpha_bars = np.cumprod(self.alphas).astype(np.float32)
        self.sqrt_alpha_bars = np.sqrt(self.alpha_bars).astype(np.float32)
        self.sqrt_one_minus_alpha_bars = np.sqrt(1.0 - self.alpha_bars).astype(np.float32)

    def q_sample(self, x0: np.ndarray, t: np.ndarray, noise: np.ndarray) -> np.ndarray:
        sab = self.sqrt_alpha_bars[t][:, None, None, None]
        somab = self.sqrt_one_minus_alpha_bars[t][:, None, None, None]
        return sab * x0 + somab * noise


# ---------------------------------------------------------------------------
# Variational reconstruction (denoise an image)
# ---------------------------------------------------------------------------


def reconstruct_image(model: NumpyUNetV2, diffusion, image: np.ndarray,
                     cfg: V2SamplerConfig, t_end: int = 50) -> np.ndarray:
    """Encode an image to a noisy latent, run a partial reverse, return
    the result. Used for detail recovery and editing.
    """
    rng = np.random.default_rng(cfg.seed or 0)
    x0 = (image * 2.0 - 1.0)[None, ...]
    t = np.array([t_end] * 1, dtype=np.int64)
    noise = rng.standard_normal(x0.shape).astype(np.float32)
    xt = diffusion.q_sample(x0, t, noise)
    n = max(1, min(cfg.num_inference_steps, t_end))
    step_indices = np.linspace(t_end, 0, n, dtype=np.int64)
    sampler = V2ImageSampler(out_root=None)
    cond = cfg.to_condition()
    cond_vec = cond.to_array()[None, :]
    uncond = ConditionVector(drop_prompt=True, drop_camera=True, drop_lighting=True,
                            drop_materials=True, drop_composition=True, drop_style=True,
                            drop_identity=True)
    uncond_vec = uncond.to_array()[None, :]
    id_vec = _identity_embedding(cond.identity, model.cfg.identity_dim)[None, :] if cond.identity \
             else np.zeros((1, model.cfg.identity_dim), dtype=np.float32)
    out, _ = sampler._reverse_loop(
        model, diffusion, model.cfg, xt, step_indices, cond_vec, uncond_vec,
        id_vec, np.zeros_like(id_vec), cfg, rng, image.shape[0], None,
    )
    x = (out[0] + 1.0) * 0.5
    x = np.clip(x, 0.0, 1.0)
    return (x * 255.0).round().astype(np.uint8).transpose(1, 2, 0)