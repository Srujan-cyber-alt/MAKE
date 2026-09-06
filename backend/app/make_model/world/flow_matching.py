"""MAKE World Model X — Flow matching training and inference.

Implements:
    - timestep / sigma schedules (linear, cosine, sigmoid)
    - flow-matching objective: x_t = (1-t)*x0 + t*x1, target = x1 - x0
    - Euler sampler
    - Heun (2nd order) sampler
    - DDIM-compatible deterministic sampler
    - Classifier-free guidance (CFG)
    - Batched inference with deterministic seeding

All implementations are backend-agnostic (numpy / torch).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, Sequence, Tuple

import numpy as np

from app.make_model.world.arch import _to_npy, _to_backend


# ----------------------------------------------------------------------
# Schedules
# ----------------------------------------------------------------------


def linear_schedule(steps: int) -> np.ndarray:
    """Linear t schedule from 0 to 1."""
    return np.linspace(0.0, 1.0, steps + 1, dtype=np.float32)


def cosine_schedule(steps: int, s: float = 0.008) -> np.ndarray:
    """Cosine t schedule (Nichol & Dhariwal, 2021)."""
    t = np.linspace(0.0, 1.0, steps + 1, dtype=np.float32)
    schedule = np.cos((t + s) / (1.0 + s) * math.pi * 0.5) ** 2
    schedule = schedule / schedule[0]
    schedule = 1.0 - schedule
    schedule = np.clip(schedule, 0.0, 1.0)
    return schedule


def sigmoid_schedule(steps: int, start: float = -3.0, end: float = 3.0) -> np.ndarray:
    """Sigmoid t schedule."""
    t = np.linspace(1.0, 0.0, steps + 1, dtype=np.float32)
    schedule = 1.0 / (1.0 + np.exp(-((end - start) * t - start)))
    schedule = (schedule - schedule[0]) / (schedule[-1] - schedule[0])
    return np.clip(schedule, 0.0, 1.0)


@dataclass
class FlowMatchingSchedule:
    kind: str = "linear"  # linear | cosine | sigmoid
    steps: int = 20

    def sample_timesteps(self, batch_size: int, seed: int = 0) -> np.ndarray:
        rng = np.random.default_rng(seed)
        if self.kind == "linear":
            t = rng.uniform(0.0, 1.0, size=(batch_size,)).astype(np.float32)
        elif self.kind == "cosine":
            t = rng.beta(2.0, 1.0, size=(batch_size,)).astype(np.float32)
        elif self.kind == "sigmoid":
            t = rng.uniform(0.0, 1.0, size=(batch_size,)).astype(np.float32)
            t = sigmoid_schedule(self.steps)[None, :] * t[:, None]
            t = t.sum(axis=1)
            t = np.clip(t / self.steps, 0.0, 1.0)
        else:
            raise ValueError(f"unknown schedule: {self.kind}")
        return t


# ----------------------------------------------------------------------
# Flow matching objective
# ----------------------------------------------------------------------


def flow_matching_target(x0: Any, x1: Any, t: Any) -> np.ndarray:
    """Compute flow-matching target: x1 - x0 (velocity).

    x0, x1: (B, C, T, H, W) or broadcastable
    t: (B,) or scalar
    Returns velocity v = x1 - x0.
    """
    x0 = _to_npy(x0)
    x1 = _to_npy(x1)
    return x1 - x0


def flow_matching_sample(x0: Any, x1: Any, t: Any) -> np.ndarray:
    """Sample x_t = (1-t)*x0 + t*x1.

    t can be broadcastable to x0 shape.
    """
    x0 = _to_npy(x0)
    x1 = _to_npy(x1)
    t = _to_npy(t)
    # reshape t for broadcasting: (B,) -> (B, 1, 1, 1, 1)
    while t.ndim < x0.ndim:
        t = t[..., None]
    return (1.0 - t) * x0 + t * x1


def flow_matching_loss(
    pred_velocity: Any,
    target_velocity: Any,
    mask: Optional[Any] = None,
) -> np.ndarray:
    """MSE between predicted and target velocity.

    pred_velocity, target_velocity: (B, C, T, H, W)
    mask: optional (B, C, T, H, W) boolean mask
    """
    pv = _to_npy(pred_velocity)
    tv = _to_npy(target_velocity)
    diff = (pv - tv) ** 2
    if mask is not None:
        m = _to_npy(mask).astype(np.float32)
        diff = diff * m
        return np.sum(diff) / (np.sum(m) + 1e-8)
    return np.mean(diff)


# ----------------------------------------------------------------------
# Samplers
# ----------------------------------------------------------------------


class FlowMatchingSampler:
    """Base class for flow matching samplers."""

    def __init__(self, cfg: Any, schedule: Optional[FlowMatchingSchedule] = None) -> None:
        self.cfg = cfg
        self.schedule = schedule or FlowMatchingSchedule()

    def sample(
        self,
        model: Any,
        cond: Any,
        steps: int = 20,
        seed: int = 0,
        cfg_scale: float = 1.0,
        scheduler: str = "linear",
    ) -> np.ndarray:
        raise NotImplementedError


class EulerSampler(FlowMatchingSampler):
    """First-order Euler sampler for flow matching."""

    def sample(
        self,
        model: Any,
        cond: Any,
        steps: int = 20,
        seed: int = 0,
        cfg_scale: float = 1.0,
        scheduler: str = "linear",
    ) -> np.ndarray:
        rng = np.random.default_rng(seed)
        C = self.cfg.latent_channels
        Tt = max(1, self.cfg.default_frames // self.cfg.temporal_patch)
        H = W = max(1, self.cfg.default_short_side // self.cfg.patch_size)
        x = rng.standard_normal((1, C, Tt, H, W)).astype(np.float32)

        if scheduler == "linear":
            ts = linear_schedule(steps)
        elif scheduler == "cosine":
            ts = cosine_schedule(steps)
        elif scheduler == "sigmoid":
            ts = sigmoid_schedule(steps)
        else:
            ts = linear_schedule(steps)

        text_tok = cond.text_tokens if cond.text_tokens is not None else np.zeros(
            (1, self.cfg.text_seq_len), dtype=np.int64
        )
        conditioning = cond.to_dict() if hasattr(cond, "to_dict") else cond

        for i in range(steps):
            t = np.full((1,), i, dtype=np.int64)
            t_frac = np.full((1,), ts[i], dtype=np.float32)

            eps = _to_npy(
                model.forward(
                    x_noisy=x,
                    t=t,
                    text_tok=text_tok,
                    cross_ctx=None,
                    first_frame=getattr(cond, "first_frame", None),
                    last_frame=getattr(cond, "last_frame", None),
                    ref_slots=getattr(cond, "ref_slots", None),
                    conditioning=conditioning,
                )
            )

            if cfg_scale > 1.0:
                eps_uncond = _to_npy(
                    model.forward(
                        x_noisy=x,
                        t=t,
                        text_tok=text_tok,
                        cross_ctx=None,
                        first_frame=getattr(cond, "first_frame", None),
                        last_frame=getattr(cond, "last_frame", None),
                        ref_slots=getattr(cond, "ref_slots", None),
                        conditioning={},
                    )
                )
                eps = eps_uncond + cfg_scale * (eps - eps_uncond)

            dt = ts[i + 1] - ts[i] if i + 1 < len(ts) else 1.0 - ts[i]
            x = x + dt * eps

        return x


class HeunSampler(FlowMatchingSampler):
    """Second-order Heun sampler for flow matching."""

    def sample(
        self,
        model: Any,
        cond: Any,
        steps: int = 20,
        seed: int = 0,
        cfg_scale: float = 1.0,
        scheduler: str = "linear",
    ) -> np.ndarray:
        rng = np.random.default_rng(seed)
        C = self.cfg.latent_channels
        Tt = max(1, self.cfg.default_frames // self.cfg.temporal_patch)
        H = W = max(1, self.cfg.default_short_side // self.cfg.patch_size)
        x = rng.standard_normal((1, C, Tt, H, W)).astype(np.float32)

        if scheduler == "linear":
            ts = linear_schedule(steps)
        elif scheduler == "cosine":
            ts = cosine_schedule(steps)
        elif scheduler == "sigmoid":
            ts = sigmoid_schedule(steps)
        else:
            ts = linear_schedule(steps)

        text_tok = cond.text_tokens if cond.text_tokens is not None else np.zeros(
            (1, self.cfg.text_seq_len), dtype=np.int64
        )
        conditioning = cond.to_dict() if hasattr(cond, "to_dict") else cond
        first_frame = getattr(cond, "first_frame", None)
        last_frame = getattr(cond, "last_frame", None)
        ref_slots = getattr(cond, "ref_slots", None)

        for i in range(steps):
            t = np.full((1,), i, dtype=np.int64)
            dt = ts[i + 1] - ts[i] if i + 1 < len(ts) else 1.0 - ts[i]

            eps1 = _to_npy(
                model.forward(
                    x_noisy=x,
                    t=t,
                    text_tok=text_tok,
                    cross_ctx=None,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    ref_slots=ref_slots,
                    conditioning=conditioning,
                )
            )

            if cfg_scale > 1.0:
                eps_uncond = _to_npy(
                    model.forward(
                        x_noisy=x,
                        t=t,
                        text_tok=text_tok,
                        cross_ctx=None,
                        first_frame=first_frame,
                        last_frame=last_frame,
                        ref_slots=ref_slots,
                        conditioning={},
                    )
                )
                eps1 = eps_uncond + cfg_scale * (eps1 - eps_uncond)

            x_euler = x + dt * eps1

            eps2 = _to_npy(
                model.forward(
                    x_noisy=x_euler,
                    t=t + 1,
                    text_tok=text_tok,
                    cross_ctx=None,
                    first_frame=first_frame,
                    last_frame=last_frame,
                    ref_slots=ref_slots,
                    conditioning=conditioning,
                )
            )

            if cfg_scale > 1.0:
                eps2 = eps_uncond + cfg_scale * (eps2 - eps_uncond)

            x = x + dt * 0.5 * (eps1 + eps2)

        return x


class DDIMLikeSampler(FlowMatchingSampler):
    """Deterministic DDIM-like sampler compatible with flow matching."""

    def sample(
        self,
        model: Any,
        cond: Any,
        steps: int = 20,
        seed: int = 0,
        cfg_scale: float = 1.0,
        scheduler: str = "linear",
    ) -> np.ndarray:
        rng = np.random.default_rng(seed)
        C = self.cfg.latent_channels
        Tt = max(1, self.cfg.default_frames // self.cfg.temporal_patch)
        H = W = max(1, self.cfg.default_short_side // self.cfg.patch_size)
        x = rng.standard_normal((1, C, Tt, H, W)).astype(np.float32)

        if scheduler == "linear":
            ts = linear_schedule(steps)
        elif scheduler == "cosine":
            ts = cosine_schedule(steps)
        elif scheduler == "sigmoid":
            ts = sigmoid_schedule(steps)
        else:
            ts = linear_schedule(steps)

        text_tok = cond.text_tokens if cond.text_tokens is not None else np.zeros(
            (1, self.cfg.text_seq_len), dtype=np.int64
        )

        for i in range(steps - 1, -1, -1):
            t = np.full((1,), i, dtype=np.int64)
            a_t = ts[i]
            a_prev = ts[max(0, i - 1)]

            eps = _to_npy(
                model.forward(
                    x_noisy=x,
                    t=t,
                    text_tok=text_tok,
                    cross_ctx=None,
                    first_frame=cond.first_frame,
                    ref_slots=cond.ref_slots,
                    conditioning=cond.to_dict() if hasattr(cond, "to_dict") else cond,
                )
            )

            if cfg_scale > 1.0:
                eps_uncond = _to_npy(
                    model.forward(
                        x_noisy=x,
                        t=t,
                        text_tok=text_tok,
                        cross_ctx=None,
                        first_frame=cond.first_frame,
                        ref_slots=cond.ref_slots,
                        conditioning={},
                    )
                )
                eps = eps_uncond + cfg_scale * (eps - eps_uncond)

            x0_pred = (x - np.sqrt(1.0 - a_t) * eps) / np.sqrt(a_t)
            x = np.sqrt(a_prev) * x0_pred + np.sqrt(1.0 - a_prev) * eps

        return x


# ----------------------------------------------------------------------
# CFG helper
# ----------------------------------------------------------------------


def apply_cfg(
    cond_output: Any,
    uncond_output: Any,
    cfg_scale: float,
) -> np.ndarray:
    """Apply classifier-free guidance.

    cond_output, uncond_output: (B, C, T, H, W) or (B, N, D)
    Returns: uncond + cfg_scale * (cond - uncond)
    """
    c = _to_npy(cond_output)
    u = _to_npy(uncond_output)
    return u + cfg_scale * (c - u)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------


@dataclass
class FlowMatchingConfig:
    """Flow matching configuration."""

    kind: str = "linear"  # linear | cosine | sigmoid
    steps: int = 20
    sampler: str = "euler"  # euler | heun | ddim
    cfg_scale: float = 1.0
    seed: int = 42


def sample_with_flow_matching(
    model: Any,
    cond: Any,
    cfg: Any,
    fm_cfg: Optional[FlowMatchingConfig] = None,
) -> np.ndarray:
    """High-level sampling API.

    Selects sampler and schedule, runs inference, returns x0 prediction.
    """
    if fm_cfg is None:
        fm_cfg = FlowMatchingConfig()

    schedule = FlowMatchingSchedule(kind=fm_cfg.kind, steps=fm_cfg.steps)

    if fm_cfg.sampler == "euler":
        sampler = EulerSampler(cfg, schedule)
    elif fm_cfg.sampler == "heun":
        sampler = HeunSampler(cfg, schedule)
    elif fm_cfg.sampler == "ddim":
        sampler = DDIMLikeSampler(cfg, schedule)
    else:
        raise ValueError(f"unknown sampler: {fm_cfg.sampler}")

    return sampler.sample(
        model=model,
        cond=cond,
        steps=fm_cfg.steps,
        seed=fm_cfg.seed,
        cfg_scale=fm_cfg.cfg_scale,
        scheduler=fm_cfg.kind,
    )


__all__ = [
    "FlowMatchingSchedule",
    "FlowMatchingConfig",
    "linear_schedule",
    "cosine_schedule",
    "sigmoid_schedule",
    "flow_matching_target",
    "flow_matching_sample",
    "flow_matching_loss",
    "FlowMatchingSampler",
    "EulerSampler",
    "HeunSampler",
    "DDIMLikeSampler",
    "apply_cfg",
    "sample_with_flow_matching",
]
