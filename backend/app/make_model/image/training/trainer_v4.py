"""
v4 trainer for the MAKE image subsystem.

Trains NumpyUNetV4 with hand-coded autograd, EMA, val split,
augmentation, mixed-cond, and resume.
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
from app.make_model.image.arch.v3.unet import _avg_pool_2x2, _upsample_2x2
from app.make_model.image.arch.v4.unet import (
    NumpyUNetV4, NumpyUNetV4Config,
)
from app.make_model.image.arch.v2.conditioning import ConditionVector
from app.make_model.image.arch.diffusion import GaussianDiffusion
from app.make_model.image.training.autograd import (
    Tensor, Param, conv2d, group_norm, linear, reshape, transpose,
    matmul, softmax, sum_dim, film,
)
from app.make_model.image.dataset.v3 import iterate_v3_split


logger = get_logger("make_model.image.v4.trainer")


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


def pre_norm_resblock_v4_forward(x: Tensor, params: Dict[str, Param], prefix: str,
                                  tcc: np.ndarray) -> Tensor:
    out_ch = params[f"{prefix}.w2"].data.shape[0]
    gn1_g = params[f"{prefix}.gn1_g"]
    gn1_b = params[f"{prefix}.gn1_b"]
    h = group_norm(x, gn1_g, gn1_b)
    h = h.relu()
    w1 = params[f"{prefix}.w1"]
    b1 = params[f"{prefix}.b1"]
    h = conv2d(h, w1, b1, pad=1)
    gn2_g = params[f"{prefix}.gn2_g"]
    gn2_b = params[f"{prefix}.gn2_b"]
    h = group_norm(h, gn2_g, gn2_b)
    mod_w = params[f"{prefix}.mod"]
    mod = tcc @ mod_w.data.T
    gamma1 = mod[:, :out_ch]; beta1 = mod[:, out_ch:2*out_ch]
    h = adagn_autograd(h, gamma1, beta1, groups=min(4, max(1, out_ch)))
    h = h.relu()
    w2 = params[f"{prefix}.w2"]
    b2 = params[f"{prefix}.b2"]
    h = conv2d(h, w2, b2, pad=1)
    skip_key = f"{prefix}.skip"
    if skip_key in params:
        b_skip = Param(np.zeros((out_ch,), dtype=np.float32), name=f"_bias_{prefix}.skip")
        skip = conv2d(x, params[skip_key], b_skip, pad=0)
    else:
        skip = x
    h = h.add(skip)
    return h


def cross_attention_v4_forward(x: Tensor, params: Dict[str, Param], prefix: str,
                                cond_seq: np.ndarray) -> Tensor:
    B, C, H, W = x.data.shape
    T = cond_seq.shape[1]
    ln_g = params[f"{prefix}.ln_g"]
    ln_b = params[f"{prefix}.ln_b"]
    xn = group_norm(x, ln_g, ln_b)
    xn = reshape(xn, (B, C, H * W))
    xn = transpose(xn, (0, 2, 1))
    w_k = params[f"{prefix}.w_k"]
    b_k = params[f"{prefix}.b_k"]
    w_v = params[f"{prefix}.w_v"]
    b_v = params[f"{prefix}.b_v"]
    kp = matmul(cond_seq, transpose(linear(reshape(cond_seq, (B*T, -1)), w_k, b_k), (0, 1)))
    vp = matmul(cond_seq, transpose(linear(reshape(cond_seq, (B*T, -1)), w_v, b_v), (0, 1)))
    w_q = params[f"{prefix}.w_q"]
    b_q = params[f"{prefix}.b_q"]
    qp = linear(reshape(xn, (B*H*W, C)), w_q, b_q)
    qp = reshape(qp, (B, H*W, C))
    scale = 1.0 / math.sqrt(max(1, C // params.get(f"{prefix}.num_heads", 4)))
    scores = matmul(qp, transpose(kp, (0, 2, 1))) * scale
    attn = softmax(scores, axis=-1)
    out = matmul(attn, vp)
    w_o = params[f"{prefix}.w_o"]
    b_o = params[f"{prefix}.b_o"]
    out = linear(reshape(out, (B*H*W, C)), w_o, b_o)
    out = reshape(out, (B, H*W, C))
    out = transpose(out, (0, 2, 1))
    out = reshape(out, (B, C, H, W))
    x = x.add(out)
    residual = x
    xn = group_norm(x, ln_g, ln_b)
    xn = reshape(xn, (B, C, H * W))
    xn = transpose(xn, (0, 2, 1))
    w_mlp1 = params[f"{prefix}.w_mlp1"]
    b_mlp1 = params[f"{prefix}.b_mlp1"]
    h = linear(reshape(xn, (B*H*W, C)), w_mlp1, b_mlp1)
    h = Tensor(np.maximum(0.0, h.data), requires_grad=True, name=f"{prefix}_mlp_relu")
    w_mlp2 = params[f"{prefix}.w_mlp2"]
    b_mlp2 = params[f"{prefix}.b_mlp2"]
    h = linear(h, w_mlp2, b_mlp2)
    h = reshape(h, (B, H*W, C))
    h = transpose(h, (0, 2, 1))
    h = reshape(h, (B, C, H, W))
    return residual.add(h)


def v4_unet_forward_autograd(model: NumpyUNetV4, x_np: np.ndarray, t_np: np.ndarray,
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

    t_emb_np = _sinusoidal_embedding(t_np, cfg.time_dim)
    t_emb_t = Tensor(t_emb_np, requires_grad=False, name="t_emb")
    t_h = linear(t_emb_t, params["time_mlp_w1"], params["time_mlp_b1"]).relu()
    t_emb_out = linear(t_h, params["time_mlp_w2"], params["time_mlp_b2"])

    c_emb_t = Tensor(cond_vec, requires_grad=False, name="cond_vec")
    c_h = linear(c_emb_t, params["cond_mlp_w1"], params["cond_mlp_b1"]).relu()
    c_emb_out = linear(c_h, params["cond_mlp_w2"], params["cond_mlp_b2"])

    tc_pre_np = np.concatenate([t_emb_out.data, c_emb_out.data], axis=1)
    tc_pre_t = Tensor(tc_pre_np, requires_grad=False, name="tc_pre")
    tc_h = linear(tc_pre_t, params["tc_w1"], params["tc_b1"]).relu()
    tc = linear(tc_h, params["tc_w2"], params["tc_b2"]).data

    x = Tensor(x_np, requires_grad=True, name="x")
    h = conv2d(x, params["stem_w"], params["stem_b"], pad=1)
    skips = []
    for li, lvl in enumerate(model.enc_levels):
        for bi, rb in enumerate(lvl["blocks"]):
            h = pre_norm_resblock_v4_forward(h, params, f"enc_levels.{li}.blocks.{bi}", tc)
        skips.append((h, lvl["out_ch"]))
        if lvl["downsample"]:
            h = Tensor(_avg_pool_2x2(h.data), requires_grad=True, name=f"down_{li}")
    h = pre_norm_resblock_v4_forward(h, params, "mid1", tc)
    h = pre_norm_resblock_v4_forward(h, params, "mid2", tc)
    resolution = cfg.image_size // (2 ** (len(cfg.channel_mults) - 1))
    if resolution in cfg.attention_resolutions:
        h = cross_attention_v4_forward(h, params, f"attn_blocks.{resolution}", c_emb_out.data)
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
            h = pre_norm_resblock_v4_forward(h, params, f"dec_levels.{li}.blocks.{bi}", tc)
        res = h.data.shape[2]
        if res in cfg.attention_resolutions:
            h = cross_attention_v4_forward(h, params, f"attn_blocks.{res}", c_emb_out.data)
    h = group_norm(h, params["out_gn_g"], params["out_gn_b"])
    h = h.relu()
    out = conv2d(h, params["out_w"], params["out_b"], pad=1)
    if "det_w" in params:
        d = conv2d(h, params["det_w"], params["det_b"], pad=1)
        d = d.relu()
        d = conv2d(d, params["det_out"],
                   Param(np.zeros((3,), dtype=np.float32), name="det_out_b"), pad=0)
        out = out.add(d)
    return out


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


@dataclass
class V4TrainingConfig:
    image_size: int = 32
    base_channels: int = 32
    channel_mults: tuple = (1, 2, 4)
    num_res_blocks: int = 3
    num_timesteps: int = 200
    batch_size: int = 4
    learning_rate: float = 3e-4
    max_steps: int = 60
    save_every: int = 20
    grad_clip: float = 1.0
    weight_decay: float = 1e-4
    seed: int = 0
    log_every: int = 5
    arch_version: str = "make-image-cpu-unet-v4"
    cfg_drop_p: float = 0.15
    dataset_name: str = "stream_v3_main"
    split: str = "train"
    val_split: str = "val"
    val_every: int = 20
    val_steps: int = 5
    resume_from: str = ""
    ema_decay: float = 0.995
    augmentation: bool = True
    time_dim: int = 128
    attention_resolutions: tuple = (8, 16)
    notes: str = ""

    def to_dict(self):
        d = asdict(self)
        d["channel_mults"] = list(self.channel_mults)
        d["attention_resolutions"] = list(self.attention_resolutions)
        return d


@dataclass
class V4TrainingResult:
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


def _save_checkpoint_v4(model: NumpyUNetV4, cfg, step: int, loss_curve: List[float],
                        out_path: str, ema_state: Optional[EMAState] = None) -> str:
    arch = model.cfg.to_dict()
    state = model.state_dict()
    payload: Dict[str, Any] = {
        "schema_version": np.int32(4),
        "owner": "MAKE",
        "arch_version": cfg.arch_version,
        "global_step": np.int32(step),
        "loss_curve": np.array(loss_curve, dtype=np.float32),
        "framework_version": "numpy",
        "arch_cfg": arch,
    }
    flat: Dict[str, Any] = {}
    for k, v in state.items():
        if isinstance(v, np.ndarray):
            flat[f"state::{k}"] = v
    payload["state_flat"] = flat
    np.savez_compressed(out_path, **payload)
    if ema_state is not None:
        ema_path = out_path.replace(".npz", ".ema.npz")
        ema_payload = {
            "schema_version": np.int32(4),
            "owner": "MAKE",
            "arch_version": cfg.arch_version,
            "ema_decay": np.float32(ema_state.decay),
            "ema_t": np.int32(ema_state.t),
            "shadow_flat": {f"shadow::{k}": np.array(v) for k, v in ema_state.shadow.items()},
        }
        np.savez_compressed(ema_path, **ema_payload)
    return out_path


def _load_checkpoint_v4(path: str, model: NumpyUNetV4, params: Dict[str, Param],
                        ema: Optional[EMAState]) -> Tuple[int, List[float]]:
    with np.load(path, allow_pickle=True) as data:
        step = int(data.get("global_step", 0))
        loss_curve = data.get("loss_curve", np.array([], dtype=np.float32)).tolist()
        flat = data.get("state_flat", {})
        for k, v in flat.items():
            if k.startswith("state::"):
                name = k[len("state::"):]
                if name in params:
                    params[name].data = np.array(v, dtype=np.float32)
        if ema is not None and "shadow_flat" in data:
            shadow = data["shadow_flat"]
            for k, v in shadow.items():
                if k.startswith("shadow::"):
                    name = k[len("shadow::"):]
                    ema.shadow[name] = np.array(v, dtype=np.float32)
    return step, loss_curve


class V4Trainer:
    def __init__(self, cfg: V4TrainingConfig):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg.seed)
        self.logger = logger
        out = ensure_dirs(None)
        self.root = out["root"]
        self.ckpt_dir = out["checkpoints"]
        self.log_dir = out["logs"]
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.ckpt_dir.mkdir(parents=True, exist_ok=True)

        cfg_dict = cfg.to_dict()
        model_cfg_keys = {f.name for f in NumpyUNetV4Config.__dataclass_fields__.values()}
        model_cfg_dict = {k: v for k, v in cfg_dict.items() if k in model_cfg_keys}
        self.model = NumpyUNetV4(NumpyUNetV4Config.from_dict(model_cfg_dict), seed=cfg.seed)
        self.params: Dict[str, Param] = {}
        for k, v in self.model.state_dict().items():
            self.params[k] = Param(np.array(v, dtype=np.float32), name=k)
        self.optimizer_state: Dict[str, AdamWState] = {}
        self.ema = EMAState({k: np.array(v, copy=True) for k, v in self.model.state_dict().items()},
                            decay=cfg.ema_decay)
        self.diffusion = GaussianDiffusion(num_timesteps=cfg.num_timesteps)
        self.global_step = 0
        self.loss_curve: List[float] = []
        self.val_loss_curve: List[float] = []
        self.step_times: List[float] = []

        if cfg.resume_from and os.path.exists(cfg.resume_from):
            self.global_step, self.loss_curve = _load_checkpoint_v4(
                cfg.resume_from, self.model, self.params, self.ema)
            self.logger.info(f"Resumed from {cfg.resume_from} at step {self.global_step}")

    def train(self, dataset_name: str, split: str = "train",
              val_split: str = "val") -> V4TrainingResult:
        t0 = time.time()
        cfg = self.cfg
        self.logger.info(f"v4 train: loading dataset '{dataset_name}' split={split}")
        x0 = _load_arrays_from_split(dataset_name, split, cfg.image_size, str(self.root))
        x0_val = _load_arrays_from_split(dataset_name, val_split, cfg.image_size, str(self.root))
        n_train = x0.shape[0]
        n_val = x0_val.shape[0]
        self.logger.info(f"v4 train: {n_train} train images, {n_val} val images")
        param_count = sum(p.data.size for p in self.params.values())
        self.logger.info(f"v4 train: {param_count} parameters")

        B = cfg.batch_size
        rng = self.rng
        try:
            for step in range(self.global_step + 1, cfg.max_steps + 1):
                ts = time.time()
                batch_idx = rng.choice(n_train, size=B, replace=False)
                x_batch = x0[batch_idx].copy()
                if cfg.augmentation:
                    x_batch = np.stack([_augment(x_batch[i], rng) for i in range(B)])
                x_batch = x_batch * 2.0 - 1.0
                t_batch = rng.integers(0, cfg.num_timesteps, size=B).astype(np.int64)
                noise = rng.standard_normal(x_batch.shape).astype(np.float32)
                ab = self.diffusion.alpha_bars[t_batch]
                sab = np.sqrt(ab)[:, None, None, None]
                somab = np.sqrt(1.0 - ab)[:, None, None, None]
                xt = sab * x_batch + somab * noise
                cond = ConditionVector(prompt="")
                if rng.random() >= cfg.cfg_drop_p:
                    cond = ConditionVector(prompt=rng.choice(["a portrait of a person",
                                                               "a landscape photograph",
                                                               "a product shot",
                                                               "a cinematic scene",
                                                               "an architectural photo"]))
                id_vec = np.zeros((B, 16), dtype=np.float32)
                pred = v4_unet_forward_autograd(self.model, xt, t_batch, cond, id_vec, self.params)
                diff = pred.data - noise
                loss = float((diff * diff).mean())
                grad_eps = 2.0 * diff / diff.size * diff.shape[0]
                pred.backward(grad_eps)
                total_norm = 0.0
                for p in self.params.values():
                    if p.grad is not None:
                        total_norm += float((p.grad * p.grad).sum())
                total_norm = math.sqrt(total_norm)
                if cfg.grad_clip > 0 and total_norm > cfg.grad_clip:
                    scale = cfg.grad_clip / total_norm
                    for p in self.params.values():
                        if p.grad is not None:
                            p.grad *= scale
                adamw_step(self.params, self.optimizer_state, cfg)
                self.ema.update({k: p.data for k, p in self.params.items()})
                dt = time.time() - ts
                self.step_times.append(dt)
                self.loss_curve.append(loss)
                if step % cfg.log_every == 0 or step == cfg.max_steps:
                    self.logger.info(f"[v4-train] step {step}/{cfg.max_steps} loss={loss:.5f} gnorm={total_norm:.3f} dt={dt:.2f}s elapsed={time.time()-t0:.1f}s")
                if step % cfg.save_every == 0 or step == cfg.max_steps:
                    ckpt_name = f"make-image-cpu-unet-v4-step{step}.npz"
                    ckpt_path = str(self.ckpt_dir / ckpt_name)
                    _save_checkpoint_v4(self.model, cfg, step, self.loss_curve, ckpt_path, self.ema)
                    sha = sha256_file(ckpt_path)
                    sidecar = {"step": step, "loss": loss, "val_loss": None,
                               "sha256": sha, "parameters": param_count,
                               "elapsed_seconds": round(time.time() - t0, 1),
                               "created_at": now_iso()}
                    with open(ckpt_path + ".training.json", "w") as f:
                        json.dump(sidecar, f, indent=2)
                    self.logger.info(f"[v4-train] saved checkpoint {ckpt_path} sha={sha[:16]}")
                if step % cfg.val_every == 0 or step == cfg.max_steps:
                    val_losses = []
                    for _ in range(cfg.val_steps):
                        vb = min(cfg.val_steps, n_val)
                        vi = rng.choice(n_val, size=vb, replace=False)
                        xv = x0_val[vi]
                        xv = xv * 2.0 - 1.0
                        tv = rng.integers(0, cfg.num_timesteps, size=vb).astype(np.int64)
                        noise_v = rng.standard_normal(xv.shape).astype(np.float32)
                        ab_v = self.diffusion.alpha_bars[tv]
                        sab_v = np.sqrt(ab_v)[:, None, None, None]
                        somab_v = np.sqrt(1.0 - ab_v)[:, None, None, None]
                        xt_v = sab_v * xv + somab_v * noise_v
                        cond_v = ConditionVector(prompt="")
                        pred_v = v4_unet_forward_autograd(self.model, xt_v, tv, cond_v,
                                                          np.zeros((vb, 16), dtype=np.float32),
                                                          self.params)
                        diff_v = pred_v.data - noise_v
                        lv = float((diff_v * diff_v).mean())
                        val_losses.append(lv)
                    avg_val = float(np.mean(val_losses))
                    self.val_loss_curve.append(avg_val)
                    self.logger.info(f"[v4-val] step {step} val_loss={avg_val:.5f}")
                self.global_step = step
            code = "OK"
            message = f"V4 training complete: {cfg.max_steps} steps"
        except Exception as e:
            self.logger.exception("V4 training failed")
            code = "ERROR"
            message = str(e)
        elapsed = time.time() - t0
        ckpt_path = str(self.ckpt_dir / f"make-image-cpu-unet-v4-step{self.global_step}.npz")
        ema_path = ckpt_path.replace(".npz", ".ema.npz")
        sha = ""
        ema_sha = ""
        if os.path.exists(ckpt_path):
            sha = sha256_file(ckpt_path)
        if os.path.exists(ema_path):
            ema_sha = sha256_file(ema_path)
        return V4TrainingResult(
            ok=(code == "OK"), code=code, message=message,
            config=cfg.to_dict(), steps_done=self.global_step,
            final_loss=float(self.loss_curve[-1]) if self.loss_curve else float("nan"),
            final_val_loss=float(self.val_loss_curve[-1]) if self.val_loss_curve else float("nan"),
            loss_curve=self.loss_curve, val_loss_curve=self.val_loss_curve,
            step_times_sec=self.step_times,
            checkpoint_path=ckpt_path, checkpoint_sha256=sha,
            ema_checkpoint_path=ema_path, ema_checkpoint_sha256=ema_sha,
            parameters=param_count, hardware={"cpu_count": os.cpu_count()},
            elapsed_seconds=round(elapsed, 1), created_at=now_iso(),
        )
