"""MAKE World Model X — Scaling presets.

Each preset records parameter count, activation memory, estimated
VRAM (single-GPU), and the resolution / frames we expect to train at.

These are engineering estimates derived from the architecture math,
NOT measured benchmarks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

import numpy as np

from app.make_model.world.arch import MakeWorldModelConfig, MakeWorldModelV0


@dataclass
class ScalingRow:
    preset: str
    hidden_dim: int
    num_layers: int
    num_heads: int
    ffn_mult: int
    default_frames: int
    default_short_side: int
    parameter_count: int
    activation_gb_at_default: float
    est_vram_gb_b1: float     # B=1, fp16 weights, fp32 optim+grad (Adam)
    est_vram_gb_b4: float


def _row(preset: str) -> ScalingRow:
    cfg = MakeWorldModelConfig.from_preset(preset)
    model = MakeWorldModelV0(cfg)
    params = model.parameter_count()
    # activation: B * N * D * num_layers * 4 bytes (rough)
    P = cfg.patch_size
    Tt = max(1, cfg.default_frames // cfg.temporal_patch)
    H = W = max(1, cfg.default_short_side // P)
    N = Tt * H * W
    act_gb = (1.0 * N * cfg.hidden_dim * cfg.num_layers * 4) / 1e9
    # weights fp16 + optim (Adam = 2 fp32 moments) + grad fp16
    weights_gb = (params * 2) / 1e9
    opt_gb = (params * 8) / 1e9
    grad_gb = (params * 2) / 1e9
    b1 = weights_gb + opt_gb + grad_gb + act_gb
    b4 = b1 + 3.0 * act_gb
    return ScalingRow(
        preset=preset,
        hidden_dim=cfg.hidden_dim,
        num_layers=cfg.num_layers,
        num_heads=cfg.num_heads,
        ffn_mult=cfg.ffn_mult,
        default_frames=cfg.default_frames,
        default_short_side=cfg.default_short_side,
        parameter_count=params,
        activation_gb_at_default=float(act_gb),
        est_vram_gb_b1=float(b1),
        est_vram_gb_b4=float(b4),
    )


def scaling_table() -> Dict[str, ScalingRow]:
    return {p: _row(p) for p in ("TINY", "SMALL", "MEDIUM", "LARGE")}


def scaling_table_dict() -> Dict[str, Dict[str, Any]]:
    return {k: vars(v) for k, v in scaling_table().items()}


__all__ = ["ScalingRow", "scaling_table", "scaling_table_dict"]
