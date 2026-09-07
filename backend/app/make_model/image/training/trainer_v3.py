"""
v3 trainer: trains NumpyUNetV3 (no-attention mode for CPU tractability)
with EMA, val split, augmentation, mixed-cond, and resume.

Uses the existing NumPy autograd primitives extended with linear, reshape,
transpose, matmul, softmax.
"""
from __future__ import annotations

import os
import time
import json
import math
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Iterator

import numpy as np
from PIL import Image

from app.make_model.utils import (
    ensure_dirs, dump_json, load_json, now_iso, sha256_file, get_logger,
)
from app.make_model.image.arch.v3.unet import (
    NumpyUNetV3, NumpyUNetV3Config, count_params_v3, _avg_pool_2x2, _upsample_2x2,
)
from app.make_model.image.arch.v2.conditioning import ConditionVector
from app.make_model.image.arch.diffusion import GaussianDiffusion
from app.make_model.image.training.autograd import (
    Tensor, Param, conv2d, group_norm, linear, reshape, transpose,
    matmul, softmax, sum_dim, film,
)
from app.make_model.image.dataset.v3 import iterate_v3_split


logger = get_logger("make_model.image.v3.trainer")


def _sinusoidal_embedding(t: np.ndarray, dim: int) -> np.ndarray:
    half = dim // 2
    freqs = np.exp(-math.log(10000.0) * np.arange(half, dtype=np.float32) / max(1, half - 1))
    args = t.astype(np.float32)[:, None] * freqs[None, :]
    emb = np.concatenate([np.sin(args), np.cos(args)], axis=1)
    if emb.shape[1] < dim:
        emb = np.concatenate([emb, np.zeros((emb.shape[0], dim - emb.shape[1]), dtype=np.float32)], axis=1)
    return emb


def adagn_autograd(x: Tensor, scale: np.ndarray, shift: np.ndarray,
                   groups: int = 1, eps: float = 1e-5) -> Tensor:
    B, C, H, W = x.data.shape
    if groups <= 0:
        groups = 1
    Cg = C // groups
    xr = x.data.reshape(B, groups, Cg, H, W)
    mean = xr.mean(axis=(2, 3, 4), keepdims=True)
    var = xr.var(axis=(2, 3, 4), keepdims=True)
    xn = (xr - mean) / np.sqrt(var + eps)
    xn = xn.reshape(B, C, H, W)
    out = xn * (1.0 + scale[:, :, None, None]) + shift[:, :, None, None]
    out_t = Tensor(out, requires_grad=True, name="adagn")
    def _bwd(g, gm):
        grad_xn = g * (1.0 + scale[:, :, None, None])
        grad_xr = (grad_xn.reshape(B, groups, Cg, H, W) / np.sqrt(var + eps)).reshape(B, C, H, W)
        x.backward(grad_xr, gm)
    out_t._backward = _bwd
    out_t._parents = (x,)
    return out_t


def adaGNResBlock_v3_forward(x: Tensor, params: Dict[str, Param], prefix: str,
                             tcc: np.ndarray) -> Tensor:
    w1 = params[f"{prefix}_w1"]; b1 = params[f"{prefix}_b1"]
    w2 = params[f"{prefix}_w2"]; b2 = params[f"{prefix}_b2"]
    gn1_g = params[f"{prefix}_gn1_g"]; gn1_b = params[f"{prefix}_gn1_b"]
    gn2_g = params[f"{prefix}_gn2_g"]; gn2_b = params[f"{prefix}_gn2_b"]
    mod_w = params[f"{prefix}_mod"]
    out_ch = w1.data.shape[0]
    mod = tcc @ mod_w.data.T
    gamma1 = mod[:, :out_ch]; beta1 = mod[:, out_ch:2*out_ch]
    gamma2 = mod[:, 2*out_ch:3*out_ch]; beta2 = mod[:, 3*out_ch:4*out_ch]
    h = conv2d(x, w1, b1, pad=1)
    h = group_norm(h, gn1_g, gn1_b)
    h = adagn_autograd(h, gamma1, beta1, groups=min(4, max(1, out_ch)))
    h = h.relu()
    h = conv2d(h, w2, b2, pad=1)
    h = group_norm(h, gn2_g, gn2_b)
    h = adagn_autograd(h, gamma2, beta2, groups=min(4, max(1, out_ch)))
    skip_key = f"{prefix}_skip"
    if skip_key in params:
        b_skip = Param(np.zeros((out_ch,), dtype=np.float32), name=f"_bias_{skip_key}")
        skip = conv2d(x, params[skip_key], b_skip, pad=0)
    else:
        skip = x
    h = h.add(skip)
    h = h.relu()
    return h


def v3_unet_forward_autograd(model: NumpyUNetV3, x_np: np.ndarray, t_np: np.ndarray,
                             cond: ConditionVector, id_vec: Optional[np.ndarray],
                             params: Dict[str, Param]) -> Tensor:
    cfg = model.cfg
    t_np = t_np.astype(np.int64)
    cond_vec = cond.to_array()
    if cond_vec.ndim == 1:
        cond_vec = np.broadcast_to(cond_vec[None, :], (t_np.shape[0], cond_vec.shape[0])).copy()
    if cond_vec.shape[1] != cfg.condition_dim:
        new = np.zeros((cond_vec.shape[0], cfg.condition_dim), dtype=np.float32)
        n_ = min(cond_vec.shape[1], cfg.condition_dim)
        new[:, :n_] = cond_vec[:, :n_]
        cond_vec = new
    t_emb = _sinusoidal_embedding(t_np, cfg.time_dim)
    tc_pre = np.concatenate([t_emb, cond_vec], axis=1)
    tc_pre_relu = np.maximum(0.0, tc_pre @ params["tc_w1"].data.T)
    tc = tc_pre_relu @ params["tc_w2"].data.T

    x = Tensor(x_np, requires_grad=True, name="x")
    h = conv2d(x, params["stem_w"], params["stem_b"], pad=1)
    skips = []
    for li, lvl in enumerate(model.enc_levels):
        for bi, rb in enumerate(lvl["blocks"]):
            h = adaGNResBlock_v3_forward(h, params, f"enc{li}_b{bi}", tc)
        skips.append((h, lvl["out_ch"]))
        if lvl["downsample"]:
            h = Tensor(_avg_pool_2x2(h.data), requires_grad=True, name=f"down_{li}")
    h = adaGNResBlock_v3_forward(h, params, "mid0", tc)
    h = adaGNResBlock_v3_forward(h, params, "mid1", tc)
    if "id_w" in params and id_vec is not None:
        idb = id_vec @ params["id_w"].data.T + params["id_b"].data
        b, c = idb.shape
        bcast = idb.reshape(b, c, 1, 1) + np.zeros((1, 1, h.data.shape[2], h.data.shape[3]), dtype=np.float32)
        id_t = Tensor(bcast, requires_grad=False, name="id_bias")
        h = h.add(id_t)
    for li, lvl in enumerate(model.dec_levels):
        skip_h, skip_ch = skips.pop()
        if h.data.shape[2] != skip_h.data.shape[2] or h.data.shape[3] != skip_h.data.shape[3]:
            h = Tensor(_upsample_2x2(h.data), requires_grad=True, name=f"up_{li}")
        h = h.concat(skip_h, axis=1)
        for bi, rb in enumerate(lvl["blocks"]):
            h = adaGNResBlock_v3_forward(h, params, f"dec{li}_b{bi}", tc)
    if "detail_w" in params:
        d = conv2d(h, params["detail_w"], params["detail_b"], pad=1)
        d = d.relu()
        d = conv2d(d, params["detail_proj_w"], params["detail_proj_b"], pad=0)
        h = h.add(d)
    h = group_norm(h, params["out_gn_g"], params["out_gn_b"])
    h = h.relu()
    out = conv2d(h, params["out_w"], params["out_b"], pad=1)
    return out


# ---------------------------------------------------------------------------
# EMA + AdamW
# ---------------------------------------------------------------------------


class EMAState:
    __slots__ = ("shadow", "decay", "t")
    def __init__(self, params: Dict[str, np.ndarray], decay: float = 0.995):
        self.shadow = {k: np.array(v, copy=True) for k, v in params.items()}
        self.decay = decay
        self.t = 0
    def update(self, params: Dict[str, np.ndarray]) -> None:
        self.t += 1
        d = self.decay
        for k, v in params.items():
            self.shadow[k] = d * self.shadow[k] + (1.0 - d) * v
    def state_dict(self) -> Dict[str, Any]:
        return {"shadow": {k: v.tolist() for k, v in self.shadow.items()},
                "decay": self.decay, "t": self.t}


class AdamWState:
    __slots__ = ("m", "v", "t")
    def __init__(self, shape):
        self.m = np.zeros(shape, dtype=np.float32)
        self.v = np.zeros(shape, dtype=np.float32)
        self.t = 0


def adamw_step(params, state, cfg, eps: float = 1e-8):
    for name, p in params.items():
        g = p.grad
        if np.all(g == 0):
            continue
        if name not in state:
            state[name] = AdamWState(p.data.shape)
        s = state[name]
        s.t += 1
        s.m = 0.9 * s.m + (1.0 - 0.9) * g
        s.v = 0.999 * s.v + (1.0 - 0.999) * (g * g)
        mh = s.m / (1.0 - 0.9 ** s.t)
        vh = s.v / (1.0 - 0.999 ** s.t)
        p.data -= cfg.learning_rate * (mh / (np.sqrt(vh) + eps) + cfg.weight_decay * p.data)


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


@dataclass
class V3TrainingConfig:
    image_size: int = 32
    base_channels: int = 24
    channel_mults: tuple = (1, 2, 4)
    num_res_blocks: int = 2
    num_timesteps: int = 200
    batch_size: int = 4
    learning_rate: float = 3e-4
    max_steps: int = 60
    save_every: int = 20
    grad_clip: float = 1.0
    weight_decay: float = 1e-4
    seed: int = 0
    log_every: int = 5
    arch_version: str = "make-image-cpu-unet-v3"
    cfg_drop_p: float = 0.15
    dataset_name: str = "stream_v3_main"
    split: str = "train"
    val_split: str = "val"
    val_every: int = 20
    val_steps: int = 5
    resume_from: str = ""
    ema_decay: float = 0.995
    augmentation: bool = True
    notes: str = ""

    def to_dict(self):
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        return d


@dataclass
class V3TrainingResult:
    ok: bool
    code: str
    message: str
    config: Dict[str, Any] = field(default_factory=dict)
    steps_done: int = 0
    final_loss: float = float("nan")
    final_val_loss: float = float("nan")
    loss_curve: List[float] = field(default_factory=list)
    val_loss_curve: List[float] = field(default_factory=list)
    step_times_sec: List[float] = field(default_factory=list)
    checkpoint_path: str = ""
    checkpoint_sha256: str = ""
    ema_checkpoint_path: str = ""
    ema_checkpoint_sha256: str = ""
    parameters: int = 0
    hardware: Dict[str, Any] = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    created_at: str = field(default_factory=now_iso)

    def to_dict(self):
        return asdict(self)


def _augment(x0: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    if rng.random() < 0.5:
        x0 = np.flip(x0, axis=2).copy()
    return x0


def _load_arrays_from_split(dataset_name: str, split: str, target_size: int,
                             out_root: str, max_images: Optional[int] = None
                             ) -> np.ndarray:
    rows = iterate_v3_split(dataset_name, split, out_root)
    if max_images:
        rows = rows[:max_images]
    out = []
    for row in rows:
        path = Path(out_root) / "datasets" / dataset_name / row["source"] / row["filename"]
        try:
            with Image.open(path) as im:
                im = im.convert("RGB").resize((target_size, target_size), Image.BILINEAR)
                arr = (np.asarray(im, dtype=np.float32) / 255.0).transpose(2, 0, 1)
            out.append(arr)
        except Exception:
            continue
    if not out:
        raise RuntimeError(f"No images loaded from split {split} of {dataset_name}")
    return np.stack(out, axis=0).astype(np.float32)


def _save_checkpoint_v3(model: NumpyUNetV3, cfg, step: int, loss_curve: List[float],
                         out_path: str, ema_state: Optional[EMAState] = None) -> str:
    arch = model.cfg.to_dict()
    state = model.state_dict()
    payload: Dict[str, Any] = {
        "schema_version": np.int32(3),
        "owner": "MAKE",
        "arch_version": cfg.arch_version,
        "global_step": np.int32(step),
        "loss_curve": np.array(loss_curve, dtype=np.float32),
        "framework_version": "numpy",
        "pytorch_version": "none (CPU-only NumPy v3 path)",
        "git_commit": "n/a",
        "created_at": now_iso(),
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
    if ema_state is not None:
        for k, v in ema_state.shadow.items():
            payload[f"ema::{k}"] = np.asarray(v, dtype=np.float32)
    payload["config_json"] = np.array(json.dumps(cfg.to_dict()))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_path, **payload)
    return out_path


def _load_checkpoint_v3(path: str, model: NumpyUNetV3, params: Dict[str, Param],
                         ema_state: Optional[EMAState] = None) -> int:
    with np.load(path, allow_pickle=True) as data:
        files = set(data.files)
        step = int(data["global_step"]) if "global_step" in files else 0
        loss_curve = list(data["loss_curve"].tolist()) if "loss_curve" in files else []
        for k in files:
            if k.startswith("state::"):
                name = k[len("state::"):]
                if name in params:
                    arr = np.asarray(data[k])
                    params[name].data[...] = arr
        if ema_state is not None:
            for k in list(ema_state.shadow.keys()):
                ek = f"ema::{k}"
                if ek in files:
                    ema_state.shadow[k] = np.asarray(data[ek])
    model.load_state_dict({k: p.data for k, p in params.items()}, strict=True)
    return step, loss_curve


class V3Trainer:
    def __init__(self, cfg: V3TrainingConfig, out_root: Optional[str] = None):
        self.cfg = cfg
        self.paths = ensure_dirs(out_root)
        self.ckpt_dir = self.paths["checkpoints"]
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)
        ucfg = NumpyUNetV3Config(
            image_size=cfg.image_size,
            base_channels=cfg.base_channels,
            channel_mults=tuple(cfg.channel_mults),
            num_res_blocks=cfg.num_res_blocks,
            num_timesteps=cfg.num_timesteps,
            arch_version=cfg.arch_version,
            attention_resolution=0,
        )
        self.model = NumpyUNetV3(ucfg, seed=cfg.seed)
        self.diffusion = GaussianDiffusion(num_timesteps=cfg.num_timesteps)
        self.params = {n: Param(np.array(a, copy=True), n)
                       for n, a in self.model.parameters().items()}
        self.adamw: Dict[str, AdamWState] = {}
        self.ema = EMAState({k: np.array(v, copy=True) for k, v in self.model.parameters().items()},
                            decay=cfg.ema_decay)

    def _sample_conditions(self, batch_size: int, rng: np.random.Generator
                           ) -> Tuple[List[ConditionVector], List[Optional[np.ndarray]]]:
        conds: List[ConditionVector] = []
        ids: List[Optional[np.ndarray]] = []
        for _ in range(batch_size):
            if rng.random() < self.cfg.cfg_drop_p:
                conds.append(ConditionVector(
                    drop_prompt=True, drop_camera=True, drop_lighting=True,
                    drop_materials=True, drop_composition=True, drop_style=True, drop_identity=True))
                ids.append(np.zeros((self.model.cfg.identity_dim,), dtype=np.float32))
                continue
            from app.make_model.image.arch.v2.conditioning import (
                CAMERA_DISTANCES, CAMERA_ANGLES, CAMERA_LENSES,
                LIGHTING_TIME, LIGHTING_DIRECTION, LIGHTING_MOOD,
                MATERIALS, COMPOSITIONS, STYLES, _identity_embedding,
            )
            c = ConditionVector(
                prompt=f"sample-{rng.integers(0, 1<<30)}",
                camera_distance=str(CAMERA_DISTANCES[rng.integers(0, len(CAMERA_DISTANCES))]),
                camera_angle=str(CAMERA_ANGLES[rng.integers(0, len(CAMERA_ANGLES))]),
                camera_lens=str(CAMERA_LENSES[rng.integers(0, len(CAMERA_LENSES))]),
                lighting_time=str(LIGHTING_TIME[rng.integers(0, len(LIGHTING_TIME))]),
                lighting_direction=str(LIGHTING_DIRECTION[rng.integers(0, len(LIGHTING_DIRECTION))]),
                lighting_mood=str(LIGHTING_MOOD[rng.integers(0, len(LIGHTING_MOOD))]),
                materials=[str(MATERIALS[rng.integers(0, len(MATERIALS))])],
                composition=str(COMPOSITIONS[rng.integers(0, len(COMPOSITIONS))]),
                style=str(STYLES[rng.integers(0, len(STYLES))]),
                identity=f"id-{rng.integers(0, 16)}",
            )
            conds.append(c)
            ids.append(_identity_embedding(c.identity, self.model.cfg.identity_dim))
        return conds, ids

    def train(self, dataset_name: str, split: str = "train",
              val_split: str = "val", out_root: Optional[str] = None) -> V3TrainingResult:
        cfg = self.cfg
        rng = np.random.default_rng(cfg.seed)
        loss_curve: List[float] = []
        val_loss_curve: List[float] = []
        step_times: List[float] = []
        start_step = 0

        if cfg.resume_from and os.path.exists(cfg.resume_from):
            start_step, loss_curve = _load_checkpoint_v3(cfg.resume_from, self.model, self.params, self.ema)
            logger.info(f"Resumed from {cfg.resume_from} at step {start_step}")

        t0 = time.time()
        try:
            train_arr = _load_arrays_from_split(dataset_name, split, cfg.image_size,
                                                 out_root or str(self.paths["root"]))
            val_arr = _load_arrays_from_split(dataset_name, val_split, cfg.image_size,
                                               out_root or str(self.paths["root"]), max_images=32)
        except RuntimeError as e:
            return V3TrainingResult(ok=False, code="EMPTY_DATASET", message=str(e))

        n_train = train_arr.shape[0]
        logger.info(f"v3 train: {n_train} train images, {val_arr.shape[0]} val images")

        for step in range(start_step + 1, cfg.max_steps + 1):
            step_t0 = time.time()
            for p in self.params.values():
                p.grad[...] = 0
            # Sample batch
            idx = rng.integers(0, n_train, size=(cfg.batch_size,))
            x0 = train_arr[idx].astype(np.float32)
            if cfg.augmentation:
                x0 = np.stack([_augment(x0[i], rng) for i in range(cfg.batch_size)])
            x0 = x0 * 2.0 - 1.0
            t = rng.integers(0, self.diffusion.T, size=(cfg.batch_size,)).astype(np.int64)
            noise = rng.standard_normal(x0.shape).astype(np.float32)
            xt = self.diffusion.q_sample(x0, t, noise)
            conds, ids = self._sample_conditions(cfg.batch_size, rng)
            # Use the first cond for the whole batch (same as v2/v1)
            cond = conds[0]
            id_stack = np.stack(ids, axis=0) if ids[0] is not None else None
            out = v3_unet_forward_autograd(self.model, xt, t, cond, id_stack, self.params)
            diff = out.data - noise
            loss = float((diff * diff).mean())
            grad_eps = 2.0 * diff / diff.size * diff.shape[0]
            out.backward(grad_eps)
            gnorm_sq = 0.0
            for p in self.params.values():
                gnorm_sq += float((p.grad * p.grad).sum())
            gnorm = gnorm_sq ** 0.5
            clip = cfg.grad_clip
            if gnorm > clip and gnorm > 0:
                scale = clip / gnorm
                for p in self.params.values():
                    p.grad *= scale
            adamw_step(self.params, self.adamw, cfg)
            # Sync model weights
            self.model.load_state_dict({k: p.data for k, p in self.params.items()}, strict=False)
            # EMA update
            self.ema.update({k: p.data for k, p in self.params.items()})
            step_dt = time.time() - step_t0
            step_times.append(step_dt)
            loss_curve.append(loss)
            if step % cfg.log_every == 0 or step == 1:
                logger.info(f"[v3-train] step {step}/{cfg.max_steps} loss={loss:.5f} gnorm={gnorm:.3f} dt={step_dt:.2f}s elapsed={time.time()-t0:.1f}s")
            if step % cfg.save_every == 0 or step == cfg.max_steps:
                ckpt_path = self.ckpt_dir / f"{cfg.arch_version}-step{step}.npz"
                _save_checkpoint_v3(self.model, cfg, step, loss_curve, str(ckpt_path), self.ema)
            if step % cfg.val_every == 0 or step == cfg.max_steps:
                vloss = self._validate(val_arr, cfg.val_steps, rng)
                val_loss_curve.append(vloss)
                logger.info(f"[v3-val] step {step} val_loss={vloss:.5f}")
        final_step = cfg.max_steps
        ckpt_path = self.ckpt_dir / f"{cfg.arch_version}-step{final_step}.npz"
        ema_path = str(ckpt_path).replace(".npz", ".ema.npz")
        _save_checkpoint_v3(self.model, cfg, final_step, loss_curve, str(ckpt_path), self.ema)
        # Also write EMA-only checkpoint
        ema_params = {k: np.array(v, copy=True) for k, v in self.ema.shadow.items()}
        ema_payload = {f"state::{k}": np.ascontiguousarray(v) for k, v in ema_params.items()}
        ema_payload["schema_version"] = np.int32(3)
        ema_payload["arch_version"] = np.array(cfg.arch_version)
        ema_payload["global_step"] = np.int32(final_step)
        ema_payload["loss_curve"] = np.array(loss_curve, dtype=np.float32)
        np.savez_compressed(ema_path, **ema_payload)
        ckpt_sha = sha256_file(str(ckpt_path))
        ema_sha = sha256_file(ema_path)
        elapsed = time.time() - t0
        result = V3TrainingResult(
            ok=True, code="OK", message="v3 training complete.",
            config=cfg.to_dict(), steps_done=final_step,
            final_loss=loss_curve[-1] if loss_curve else float("nan"),
            final_val_loss=val_loss_curve[-1] if val_loss_curve else float("nan"),
            loss_curve=loss_curve, val_loss_curve=val_loss_curve, step_times_sec=step_times,
            checkpoint_path=str(ckpt_path), checkpoint_sha256=ckpt_sha,
            ema_checkpoint_path=ema_path, ema_checkpoint_sha256=ema_sha,
            parameters=count_params_v3(self.model),
            hardware={"device": "cpu", "cuda_available": False, "pytorch_available": False,
                      "cpu_count": os.cpu_count()},
            elapsed_seconds=round(elapsed, 3),
        )
        dump_json(str(ckpt_path) + ".training.json", result.to_dict())
        return result

    def _validate(self, val_arr: np.ndarray, n_steps: int, rng: np.random.Generator) -> float:
        losses = []
        for _ in range(n_steps):
            idx = rng.integers(0, val_arr.shape[0], size=(self.cfg.batch_size,))
            x0 = val_arr[idx].astype(np.float32) * 2.0 - 1.0
            t = rng.integers(0, self.diffusion.T, size=(self.cfg.batch_size,)).astype(np.int64)
            noise = rng.standard_normal(x0.shape).astype(np.float32)
            xt = self.diffusion.q_sample(x0, t, noise)
            cond = ConditionVector()
            out = v3_unet_forward_autograd(self.model, xt, t, cond, None, self.params)
            diff = out.data - noise
            losses.append(float((diff * diff).mean()))
        return float(np.mean(losses))
