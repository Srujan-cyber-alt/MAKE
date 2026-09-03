"""Losses for MAKE World Model X.

Each loss has:
    - a pure-function math definition
    - a numpy reference implementation
    - unit tests under tests/test_world_model.py

Losses:
    reconstruction_loss          - DDPM-style MSE on noise
    temporal_consistency_loss    - L1 between consecutive frames
    motion_consistency_loss      - L1 between predicted and gt optical flow
    text_alignment_loss          - cosine between pooled text and frame mean
    identity_consistency_loss    - L2 between predicted face emb and reference
    product_consistency_loss     - L2 between predicted product emb and reference
    camera_adherence_loss        - L1 between predicted and target camera params
    perceptual_loss              - placeholder; real impl uses a frozen VGG
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np


def _to_npy(x: Any) -> np.ndarray:
    return np.asarray(x, dtype=np.float32)


def reconstruction_loss(pred: Any, target: Any) -> np.ndarray:
    """DDPM-style MSE on predicted noise.

    pred, target: (B, C, T, H, W) latents
    Returns a 0-d numpy array (mean).
    """
    p = _to_npy(pred)
    t = _to_npy(target)
    return np.mean((p - t) ** 2)


def temporal_consistency_loss(pred_frames: Any) -> np.ndarray:
    """L1 between consecutive predicted frames.

    pred_frames: (B, C, T, H, W)
    """
    p = _to_npy(pred_frames)
    if p.shape[2] < 2:
        return np.float32(0.0)
    diff = np.abs(p[:, :, 1:] - p[:, :, :-1])
    return np.mean(diff)


def motion_consistency_loss(pred_flow: Any, gt_flow: Any) -> np.ndarray:
    """L1 between predicted and gt optical flow.

    pred_flow, gt_flow: (B, 2, T, H, W)
    """
    p = _to_npy(pred_flow)
    g = _to_npy(gt_flow)
    return np.mean(np.abs(p - g))


def text_alignment_loss(pooled_text: Any, frame_mean: Any) -> np.ndarray:
    """1 - cosine similarity (averaged)."""
    p = _to_npy(pooled_text)
    f = _to_npy(frame_mean)
    pn = p / (np.linalg.norm(p, axis=-1, keepdims=True) + 1e-8)
    fn = f / (np.linalg.norm(f, axis=-1, keepdims=True) + 1e-8)
    return np.mean(1.0 - np.sum(pn * fn, axis=-1))


def identity_consistency_loss(pred_emb: Any, ref_emb: Any) -> np.ndarray:
    p = _to_npy(pred_emb)
    r = _to_npy(ref_emb)
    return np.mean((p - r) ** 2)


def product_consistency_loss(pred_emb: Any, ref_emb: Any) -> np.ndarray:
    return identity_consistency_loss(pred_emb, ref_emb)


def camera_adherence_loss(pred_cam: Any, target_cam: Any) -> np.ndarray:
    p = _to_npy(pred_cam)
    t = _to_npy(target_cam)
    return np.mean(np.abs(p - t))


def perceptual_loss(pred_frames: Any, target_frames: Any) -> np.ndarray:
    """Placeholder. Real implementation uses a frozen VGG/CLIP.

    Without torch + a model checkpoint we cannot run VGG here. We
    return a simple L1 loss so the training loop is well-defined.
    """
    p = _to_npy(pred_frames)
    t = _to_npy(target_frames)
    return np.mean(np.abs(p - t))


@dataclass
class LossWeights:
    recon: float = 1.0
    temporal: float = 0.1
    motion: float = 0.0
    text_align: float = 0.0
    identity: float = 0.0
    product: float = 0.0
    camera: float = 0.0
    perceptual: float = 0.0


def total_loss(
    weights: LossWeights,
    recon: Optional[Any] = None,
    temporal: Optional[Any] = None,
    motion: Optional[Any] = None,
    text_align: Optional[Any] = None,
    identity: Optional[Any] = None,
    product: Optional[Any] = None,
    camera: Optional[Any] = None,
    perceptual: Optional[Any] = None,
) -> Dict[str, Any]:
    """Combine a set of per-component losses using LossWeights.

    Returns a dict with 'total' (numpy 0-d) and per-component floats.
    """
    parts: Dict[str, float] = {}
    total = np.float32(0.0)
    if recon is not None and weights.recon > 0:
        v = float(np.asarray(recon))
        parts["recon"] = v
        total = total + weights.recon * v
    if temporal is not None and weights.temporal > 0:
        v = float(np.asarray(temporal))
        parts["temporal"] = v
        total = total + weights.temporal * v
    if motion is not None and weights.motion > 0:
        v = float(np.asarray(motion))
        parts["motion"] = v
        total = total + weights.motion * v
    if text_align is not None and weights.text_align > 0:
        v = float(np.asarray(text_align))
        parts["text_align"] = v
        total = total + weights.text_align * v
    if identity is not None and weights.identity > 0:
        v = float(np.asarray(identity))
        parts["identity"] = v
        total = total + weights.identity * v
    if product is not None and weights.product > 0:
        v = float(np.asarray(product))
        parts["product"] = v
        total = total + weights.product * v
    if camera is not None and weights.camera > 0:
        v = float(np.asarray(camera))
        parts["camera"] = v
        total = total + weights.camera * v
    if perceptual is not None and weights.perceptual > 0:
        v = float(np.asarray(perceptual))
        parts["perceptual"] = v
        total = total + weights.perceptual * v
    parts["total"] = float(total)
    return parts


__all__ = [
    "LossWeights",
    "reconstruction_loss",
    "temporal_consistency_loss",
    "motion_consistency_loss",
    "text_alignment_loss",
    "identity_consistency_loss",
    "product_consistency_loss",
    "camera_adherence_loss",
    "perceptual_loss",
    "total_loss",
]
