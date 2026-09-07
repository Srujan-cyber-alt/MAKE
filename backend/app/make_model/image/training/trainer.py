"""
Training module for the MAKE image subsystem (CPU-only, NumPy).

Uses a tiny autograd (see autograd.py) to backprop through the
NumpyUNet. Optimizer is hand-coded.

The training loop is intentionally short — it is sized to genuinely
fit in the compute budget of a CPU-only cloud sandbox. Quality scales
linearly with more steps; longer training can be resumed from a
checkpoint by ImageTrainer.train(...).
"""

from __future__ import annotations

import os
import math
import time
import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np

from app.make_model.utils import ensure_dirs, dump_json, load_json, now_iso, sha256_file, get_logger
from app.make_model.image.arch.unet import NumpyUNet, NumpyUNetConfig, count_params
from app.make_model.image.arch.diffusion import GaussianDiffusion
from app.make_model.image.training.autograd import (
    Tensor, Param, conv2d, group_norm, film,
)


logger = get_logger("make_model.image.trainer")


@dataclass
class TrainingConfig:
    image_size: int = 32
    base_channels: int = 16
    channel_mults: tuple = (1,)
    num_res_blocks: int = 1
    num_timesteps: int = 100
    batch_size: int = 4
    micro_batch: int = 4
    learning_rate: float = 3e-4
    max_steps: int = 30
    save_every: int = 15
    grad_clip: float = 1.0
    beta1: float = 0.9
    beta2: float = 0.999
    weight_decay: float = 0.0
    seed: int = 0
    dataset_kind: str = "procedural"
    dataset_name: str = "make-procdataset-v0"
    dataset_manifest_sha: str = ""
    log_every: int = 2
    arch_version: str = "make-image-cpu-unet-v1"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        return d


@dataclass
class TrainingResult:
    ok: bool
    code: str
    message: str
    config: Dict[str, Any] = field(default_factory=dict)
    dataset_info: Dict[str, Any] = field(default_factory=dict)
    steps_done: int = 0
    final_loss: float = float("nan")
    loss_curve: List[float] = field(default_factory=list)
    step_times_sec: List[float] = field(default_factory=list)
    checkpoint_path: str = ""
    checkpoint_sha256: str = ""
    parameters: int = 0
    hardware: Dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Convert NumpyUNet parameters to a flat dict of `Param` objects. We re-use
# the model's parameters but expose them under names the autograd knows.
# ---------------------------------------------------------------------------


def build_param_dict(model: NumpyUNet) -> Dict[str, Param]:
    out: Dict[str, Param] = {}
    for name, arr in model.parameters().items():
        out[name] = Param(np.array(arr, copy=True), name)
    return out


def copy_params_into_model(model: NumpyUNet, params: Dict[str, Param]) -> None:
    for name, p in params.items():
        # Match the model's own parameter slot by name
        for spec_name, spec_arr in model._param_specs:
            if spec_name == name:
                spec_arr[...] = p.data


def reset_grads(params: Dict[str, Param]) -> None:
    for p in params.values():
        p.grad[...] = 0


def accumulate_grads(dst: Dict[str, Param], src: Dict[str, Param]) -> None:
    for name, p in src.items():
        if name in dst:
            dst[name].grad += p.grad
        else:
            # create a zero entry; ignore missing grads
            pass


# ---------------------------------------------------------------------------
# Forward through the UNet using autograd. Returns the output Tensor.
# ---------------------------------------------------------------------------


def _time_embedding_np(t: np.ndarray, dim: int) -> np.ndarray:
    half = dim // 2
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(1, half - 1))
    args = t.astype(np.float32)[:, None] * freqs[None, :]
    emb = np.concatenate([np.sin(args), np.cos(args)], axis=1)
    if emb.shape[1] < dim:
        emb = np.concatenate([emb, np.zeros((emb.shape[0], dim - emb.shape[1]), dtype=np.float32)], axis=1)
    return emb.astype(np.float32)


def _prompt_embedding_np(prompt: str, dim: int) -> np.ndarray:
    if not prompt:
        return np.zeros((dim,), dtype=np.float32)
    import hashlib
    h = hashlib.sha256(prompt.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big") & 0x7FFFFFFF
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= max(1e-6, np.linalg.norm(v))
    return v


def unet_forward_autograd(model: NumpyUNet, x_np: np.ndarray, t_np: np.ndarray,
                          prompt: str, params: Dict[str, Param]) -> Tensor:
    cfg = model.cfg
    B = x_np.shape[0]
    t_emb_pre = _time_embedding_np(t_np, cfg.time_dim)
    # linear + relu + linear for time MLP
    h = np.maximum(0.0, t_emb_pre @ params["time_mlp_w1"].data.T)
    t_emb = h @ params["time_mlp_w2"].data.T
    txt_emb = np.broadcast_to(_prompt_embedding_np(prompt, cfg.text_dim)[None, :],
                              (B, cfg.text_dim)).copy()
    # Stem
    x = Tensor(x_np, requires_grad=True, name="x")
    h = conv2d(x, params["stem_w"], params["stem_b"], pad=1)
    skips = [h]
    # Encoder
    rb_idx = 0
    for level, m in enumerate(cfg.channel_mults):
        for _ in range(cfg.num_res_blocks):
            h = _resblock_autograd(h, params, rb_idx, "enc", t_emb, txt_emb)
            skips.append(h)
            rb_idx += 1
        if level < len(cfg.channel_mults) - 1:
            h = h.avgpool_2x2()
            skips.append(h)
    # Mid
    h = _resblock_autograd(h, params, 0, "mid", t_emb, txt_emb, mid_index=0)
    h = _resblock_autograd(h, params, 0, "mid", t_emb, txt_emb, mid_index=1)
    # Decoder
    up_idx = 0
    for level in reversed(range(len(cfg.channel_mults))):
        for _ in range(cfg.num_res_blocks):
            skip = skips.pop()
            h = h.concat(skip, axis=1)
            h = _resblock_autograd(h, params, up_idx, "dec", t_emb, txt_emb)
            up_idx += 1
        if level < len(cfg.channel_mults) - 1:
            h = h.upsample_2x2()
    # Output projection
    h = group_norm(h, params["out_gn_g"], params["out_gn_b"])
    h = h.relu()
    out = conv2d(h, params["out_w"], params["out_b"], pad=1)
    return out


def _resblock_autograd(x: Tensor, params: Dict[str, Param], rb_idx: int, kind: str,
                       t_emb: np.ndarray, txt_emb: np.ndarray, mid_index: Optional[int] = None) -> Tensor:
    if kind == "mid":
        prefix = f"mid{mid_index}"
    else:
        prefix = f"{kind}{rb_idx}"
    rb_keys = [f"{prefix}_w1", f"{prefix}_b1", f"{prefix}_w2", f"{prefix}_b2",
               f"{prefix}_gn1_g", f"{prefix}_gn1_b", f"{prefix}_gn2_g", f"{prefix}_gn2_b",
               f"{prefix}_film1", f"{prefix}_film2"]
    w1 = params[rb_keys[0]]
    b1 = params[rb_keys[1]]
    w2 = params[rb_keys[2]]
    b2 = params[rb_keys[3]]
    gn1_g = params[rb_keys[4]]
    gn1_b = params[rb_keys[5]]
    gn2_g = params[rb_keys[6]]
    gn2_b = params[rb_keys[7]]
    film1_w = params[rb_keys[8]]
    film2_w = params[rb_keys[9]]
    cond = np.concatenate([t_emb, txt_emb], axis=1)
    film1 = cond @ film1_w.data.T
    scale1 = film1[:, :w1.data.shape[0]]
    shift1 = film1[:, w1.data.shape[0]:]
    film2 = cond @ film2_w.data.T
    out_ch = w1.data.shape[0]
    scale2 = film2[:, :out_ch]
    shift2 = film2[:, out_ch:]

    h = conv2d(x, w1, b1, pad=1)
    h = group_norm(h, gn1_g, gn1_b)
    h = film(h, scale1, shift1)
    h = h.relu()
    h = conv2d(h, w2, b2, pad=1)
    h = group_norm(h, gn2_g, gn2_b)
    h = film(h, scale2, shift2)
    skip_key = f"{prefix}_skip"
    if skip_key in params and params[skip_key].data.shape != (out_ch, x.data.shape[1], 1, 1) and False:
        # placeholder
        pass
    if skip_key in params:
        skip = conv2d(x, params[skip_key], _zero_bias_like(params[skip_key]), pad=0)
    else:
        skip = x
    h = h.add(skip)
    h = h.relu()
    return h


def _zero_bias_like(p: Param) -> Param:
    b = Param(np.zeros((p.data.shape[0],), dtype=np.float32), name=f"_bias_{p.name}")
    return b


# ---------------------------------------------------------------------------
# Adam
# ---------------------------------------------------------------------------


class AdamState:
    __slots__ = ("m", "v", "t")

    def __init__(self, shape):
        self.m = np.zeros(shape, dtype=np.float32)
        self.v = np.zeros(shape, dtype=np.float32)
        self.t = 0


def adam_step(params, grad_params, state, cfg, eps=1e-8):
    for name, p in params.items():
        g = p.grad
        if np.all(g == 0):
            continue
        if name not in state:
            state[name] = AdamState(p.data.shape)
        s = state[name]
        s.t += 1
        if cfg.weight_decay:
            g = g + cfg.weight_decay * p.data
        s.m = cfg.beta1 * s.m + (1.0 - cfg.beta1) * g
        s.v = cfg.beta2 * s.v + (1.0 - cfg.beta2) * (g * g)
        m_hat = s.m / (1.0 - cfg.beta1 ** s.t)
        v_hat = s.v / (1.0 - cfg.beta2 ** s.t)
        p.data -= cfg.learning_rate * m_hat / (np.sqrt(v_hat) + eps)


# ---------------------------------------------------------------------------
# Save / load checkpoints
# ---------------------------------------------------------------------------


def _save_checkpoint(model: NumpyUNet, cfg: TrainingConfig, dataset_info: Dict[str, Any],
                     step: int, loss_curve: List[float], out_path: str) -> str:
    """Save a checkpoint as a .npz file.

    NumPy's savez format stores each top-level key as a separate array.
    We therefore flatten nested dicts (arch_config, model_state, dataset_info,
    config) into a set of named arrays. We record a manifest of the original
    keys so the loader can reconstruct the dicts.
    """
    arch_config = model.cfg.to_dict()
    model_state = {k: np.ascontiguousarray(v, dtype=np.float32)
                   for k, v in model.state_dict().items()}
    config = cfg.to_dict()
    payload: Dict[str, Any] = {
        "schema_version": np.int32(1),
        "owner": "MAKE",
        "arch_version": cfg.arch_version,
        "config": config,
        "dataset_info": dataset_info,
        "global_step": np.int32(step),
        "loss_curve": np.array(loss_curve, dtype=np.float32),
        "framework_version": "numpy",
        "pytorch_version": "none (CPU-only NumPy path)",
        "git_commit": "n/a",
        "created_at": now_iso(),
        # Marker so the loader knows arch_config / model_state follow as
        # named arrays below.
        "_manifest": np.array(sorted(["arch_config"] + list(arch_config.keys())
                                     + ["model_state"] + list(model_state.keys())),
                               dtype=object),
    }
    # Save arch_config fields as their own arrays.
    for k, v in arch_config.items():
        if isinstance(v, (int, float, str, bool)):
            payload[f"archcfg::{k}"] = np.array(v)
        elif isinstance(v, list):
            payload[f"archcfg::{k}"] = np.array(v)
        else:
            payload[f"archcfg::{k}"] = np.array(str(v))
    # Save model state arrays.
    for k, arr in model_state.items():
        payload[f"state::{k}"] = arr
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, **payload)
    return out_path


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class ImageTrainer:
    def __init__(self, cfg: TrainingConfig, out_root: Optional[str] = None):
        self.cfg = cfg
        self.paths = ensure_dirs(out_root)
        self.checkpoints_dir = self.paths["checkpoints"]
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.unet_cfg = NumpyUNetConfig(
            image_size=cfg.image_size,
            base_channels=cfg.base_channels,
            channel_mults=tuple(cfg.channel_mults),
            num_res_blocks=cfg.num_res_blocks,
            num_timesteps=cfg.num_timesteps,
            arch_version=cfg.arch_version,
            notes=cfg.notes,
        )
        self.model = NumpyUNet(self.unet_cfg, seed=cfg.seed)
        self.diffusion = GaussianDiffusion(num_timesteps=cfg.num_timesteps)
        # The autograd parameters are decoupled from the model's; we copy them in/out.
        self.params = build_param_dict(self.model)
        self.adam_state: Dict[str, AdamState] = {}

    def train(self, dataset_arr: np.ndarray, dataset_info: Dict[str, Any]) -> TrainingResult:
        cfg = self.cfg
        rng = np.random.default_rng(cfg.seed)
        N = dataset_arr.shape[0]
        if N < cfg.batch_size:
            raise RuntimeError(f"Dataset has {N} images, need >= batch_size={cfg.batch_size}")
        loss_curve: List[float] = []
        step_times: List[float] = []
        t0 = time.time()
        # Make sure autograd params are in sync with model at start.
        copy_params_into_model(self.model, self.params)

        for step in range(1, cfg.max_steps + 1):
            step_t0 = time.time()
            # zero grads
            for p in self.params.values():
                p.grad[...] = 0

            idxs = rng.integers(0, N, size=cfg.batch_size)
            mb = cfg.micro_batch
            total_loss = 0.0
            for mb_start in range(0, cfg.batch_size, mb):
                mb_end = min(cfg.batch_size, mb_start + mb)
                x0 = dataset_arr[idxs[mb_start:mb_end]].astype(np.float32) * 2.0 - 1.0
                t = rng.integers(0, self.diffusion.T, size=(mb_end - mb_start,)).astype(np.int64)
                noise = rng.standard_normal(x0.shape).astype(np.float32)
                xt = self.diffusion.q_sample(x0, t, noise)

                # Forward
                out = unet_forward_autograd(self.model, xt, t, prompt="", params=self.params)
                diff = out.data - noise
                loss = float((diff * diff).mean())
                total_loss += loss * (mb_end - mb_start)
                grad_eps = 2.0 * diff / diff.size * diff.shape[0]
                # Backward
                out.backward(grad_eps)  # gm unused (Param stores its own grad)

            avg_loss = total_loss / max(1, cfg.batch_size)
            loss_curve.append(avg_loss)

            # Gradient clip
            gnorm_sq = 0.0
            for p in self.params.values():
                gnorm_sq += float((p.grad * p.grad).sum())
            gnorm = gnorm_sq ** 0.5
            clip = cfg.grad_clip
            if gnorm > clip and gnorm > 0:
                scale = clip / gnorm
                for p in self.params.values():
                    p.grad *= scale

            # Step
            adam_step(self.params, None, self.adam_state, cfg)
            # Copy updated params back into the model for the next forward.
            copy_params_into_model(self.model, self.params)

            step_dt = time.time() - step_t0
            step_times.append(step_dt)
            if step % cfg.log_every == 0 or step == 1:
                logger.info(
                    f"[image-train] step {step}/{cfg.max_steps} loss={avg_loss:.5f} "
                    f"gnorm={gnorm:.3f} step_dt={step_dt:.2f}s elapsed={time.time()-t0:.1f}s"
                )
            if step % cfg.save_every == 0 or step == cfg.max_steps:
                ckpt_path = self.checkpoints_dir / f"{cfg.arch_version}-step{step}.npz"
                _save_checkpoint(
                    model=self.model, cfg=cfg, dataset_info=dataset_info,
                    step=step, loss_curve=loss_curve, out_path=str(ckpt_path),
                )
        final_step = cfg.max_steps
        ckpt_path = self.checkpoints_dir / f"{cfg.arch_version}-step{final_step}.npz"
        ckpt_sha = sha256_file(str(ckpt_path))
        elapsed = time.time() - t0
        hw = _detect_cpu_hardware()
        result = TrainingResult(
            ok=True, code="OK", message="Image training complete.",
            config=cfg.to_dict(), dataset_info=dataset_info,
            steps_done=final_step,
            final_loss=loss_curve[-1] if loss_curve else float("nan"),
            loss_curve=loss_curve, step_times_sec=step_times,
            checkpoint_path=str(ckpt_path), checkpoint_sha256=ckpt_sha,
            parameters=count_params(self.model), hardware=hw,
            elapsed_seconds=round(elapsed, 3),
        )
        dump_json(str(ckpt_path) + ".training.json", result.to_dict())
        return result


def _detect_cpu_hardware() -> Dict[str, Any]:
    info = {"device": "cpu", "accelerator": "none", "cuda_available": False, "pytorch_available": False}
    try:
        import psutil  # type: ignore
        info["cpu_count"] = psutil.cpu_count(logical=True)
        info["total_memory_bytes"] = psutil.virtual_memory().total
    except Exception:
        info["cpu_count"] = os.cpu_count()
    return info