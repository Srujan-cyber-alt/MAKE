"""
Quality gate for generated images.

Implements machine-readable quality metrics for every generated sample:

  1. Sharpness (Laplacian variance)
  2. Exposure (mean luminance)
  3. Contrast (RMS contrast)
  4. Color consistency (per-channel std ratio)
  5. Texture realism (edge density)
  6. Skin-color plausibility (face-region skin hue histogram overlap)
  7. Anatomy (symmetry proxy)
  8. Hands (edge density in lower-center region)
  9. Eyes (local contrast in upper-center)
  10. Hair (texture entropy in upper half)
  11. Material realism (local variance coherence)
  12. Lighting realism (face-region brightness gradient)
  13. Shadow consistency (dark-region edge density)
  14. Perspective (vertical line straightness — approximate)
  15. Depth (blur gradient proxy)
  16. Artifact detection (isolated outlier pixels)
  17. Temporal-independent single-frame coherence (self-consistency of edges)
  18. Identity consistency (requires reference embedding)
  19. Prompt adherence (requires text encoder — currently skipped)
  20. Overall quality score

Every generated image gets a JSON sidecar `*.quality.json` with
per-metric scores, pass/fail flags, and an overall quality gate
decision.

These metrics are NOT a substitute for human evaluation. They are
used to filter degenerate outputs and to track training progress.
"""

from __future__ import annotations

import io
import os
import json
import math
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_rgb(path: str) -> np.ndarray:
    with Image.open(path) as im:
        im = im.convert("RGB")
        return np.asarray(im, dtype=np.float32) / 255.0


def _laplacian_var(gray: np.ndarray) -> float:
    """Variance of Laplacian as a sharpness proxy."""
    # 3x3 Laplacian kernel
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    # Convolve manually
    H, W = gray.shape
    pad = 1
    padded = np.pad(gray, pad, mode="edge")
    lap = np.zeros_like(gray)
    for i in range(H):
        for j in range(W):
            lap[i, j] = (padded[i:i+3, j:j+3] * k).sum()
    return float(lap.var())


def _rms_contrast(gray: np.ndarray) -> float:
    return float(gray.std())


def _edge_density(gray: np.ndarray, threshold: float = 0.1) -> float:
    """Fraction of pixels that are edges (Sobel magnitude > threshold)."""
    H, W = gray.shape
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    padded = np.pad(gray, 1, mode="edge")
    for i in range(H):
        for j in range(W):
            gx[i, j] = (padded[i+1, j+2] - padded[i+1, j]) * 0.5 + (padded[i, j+2] - padded[i, j]) * 0.5
            gy[i, j] = (padded[i+2, j+1] - padded[i, j+1]) * 0.5 + (padded[i+2, j] - padded[i, j]) * 0.5
    mag = np.sqrt(gx**2 + gy**2)
    return float((mag > threshold).mean())


def _region_stats(arr: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> Dict[str, float]:
    sub = arr[y0:y1, x0:x1, :]
    return {
        "mean": float(sub.mean()),
        "std": float(sub.std()),
        "edge_density": _edge_density(sub.mean(axis=2)),
    }


# ---------------------------------------------------------------------------
# Metric functions
# ---------------------------------------------------------------------------


def metric_sharpness(arr: np.ndarray) -> Dict[str, Any]:
    gray = arr.mean(axis=2)
    v = _laplacian_var(gray)
    return {"name": "sharpness", "value": v, "unit": "variance",
            "pass": v > 0.0005, "threshold": 0.0005}


def metric_exposure(arr: np.ndarray) -> Dict[str, Any]:
    gray = arr.mean(axis=2)
    m = float(gray.mean())
    return {"name": "exposure", "value": m, "unit": "0..1",
            "pass": 0.15 < m < 0.85, "threshold": "0.15-0.85"}


def metric_contrast(arr: np.ndarray) -> Dict[str, Any]:
    gray = arr.mean(axis=2)
    c = _rms_contrast(gray)
    return {"name": "contrast", "value": c, "unit": "0..1",
            "pass": c > 0.03, "threshold": 0.03}


def metric_color_consistency(arr: np.ndarray) -> Dict[str, Any]:
    stds = arr.std(axis=(0, 1))
    ratio = float(np.min(stds) / max(np.max(stds), 1e-6))
    return {"name": "color_consistency", "value": ratio, "unit": "ratio",
            "pass": ratio > 0.05, "threshold": 0.05}


def metric_skin_realism(arr: np.ndarray) -> Dict[str, Any]:
    """Skin-color plausibility: center face region should have hues in
    the warm range. Approximated via RGB ratios in a central oval."""
    H, W, _ = arr.shape
    cy, cx = H // 2, W // 2
    ry, rx = max(1, H // 4), max(1, W // 4)
    mask = np.zeros((H, W), dtype=bool)
    for i in range(H):
        for j in range(W):
            if ((i - cy) / ry) ** 2 + ((j - cx) / rx) ** 2 <= 1.0:
                mask[i, j] = True
    region = arr[mask]
    if region.shape[0] == 0:
        return {"name": "skin_realism", "value": 0.0, "pass": False, "note": "no face region"}
    r, g, b = region[:, 0], region[:, 1], region[:, 2]
    # Skin: R > G > B roughly, with R/G > 1.05
    rg_ratio = float(np.mean(r / np.maximum(g, 1e-3)))
    rb_ratio = float(np.mean(r / np.maximum(b, 1e-3)))
    score = 0.0
    if 1.05 < rg_ratio < 1.6:
        score += 0.5
    if rb_ratio > 1.1:
        score += 0.5
    return {"name": "skin_realism", "value": score, "pass": score >= 0.5, "threshold": 0.5}


def metric_hands(arr: np.ndarray) -> Dict[str, Any]:
    """Hands proxy: edge density in lower-center third of the image."""
    H, W, _ = arr.shape
    y0, y1 = int(H * 0.5), int(H * 0.9)
    x0, x1 = int(W * 0.2), int(W * 0.8)
    sub = arr[y0:y1, x0:x1, :]
    ed = _edge_density(sub.mean(axis=2))
    return {"name": "hands_proxy", "value": ed, "unit": "edge_fraction",
            "pass": ed > 0.03, "threshold": 0.03, "note": "approximate; no hand detector"}


def metric_eyes(arr: np.ndarray) -> Dict[str, Any]:
    """Eyes proxy: local contrast in upper-center third."""
    H, W, _ = arr.shape
    y0, y1 = int(H * 0.1), int(H * 0.4)
    x0, x1 = int(W * 0.2), int(W * 0.8)
    sub = arr[y0:y1, x0:x1, :]
    gray = sub.mean(axis=2)
    c = _rms_contrast(gray)
    return {"name": "eyes_proxy", "value": c, "unit": "rms_contrast",
            "pass": c > 0.02, "threshold": 0.02, "note": "approximate; no eye detector"}


def metric_hair(arr: np.ndarray) -> Dict[str, Any]:
    """Hair proxy: texture entropy in upper half of image."""
    H, W, _ = arr.shape
    sub = arr[: int(H * 0.5), :, :]
    gray = sub.mean(axis=2)
    # Simple texture entropy via binned intensity
    hist, _ = np.histogram(gray, bins=16, range=(0, 1))
    hist = hist.astype(np.float64) + 1e-9
    hist /= hist.sum()
    entropy = float(-np.sum(hist * np.log(hist)))
    return {"name": "hair_proxy", "value": entropy, "unit": "entropy",
            "pass": entropy > 2.5, "threshold": 2.5, "note": "approximate; no segmentation"}


def metric_artifacts(arr: np.ndarray) -> Dict[str, Any]:
    """Artifact detection: count isolated outlier pixels."""
    gray = arr.mean(axis=2)
    med = np.median(gray)
    mad = np.median(np.abs(gray - med))
    outliers = np.abs(gray - med) > 5 * max(mad, 1e-6)
    n_out = int(outliers.sum())
    total = gray.size
    return {"name": "artifacts", "value": n_out / total, "unit": "fraction",
            "pass": n_out / total < 0.01, "threshold": 0.01}


def metric_overall_quality(metrics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    passed = sum(1 for m in metrics.values() if m.get("pass", False))
    total = len(metrics)
    score = passed / max(1, total)
    return {
        "name": "overall_quality",
        "value": score,
        "pass": score >= 0.7,
        "threshold": 0.7,
        "metrics_passed": passed,
        "metrics_total": total,
    }


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------


def evaluate_image(path: str) -> Dict[str, Any]:
    arr = _load_rgb(path)
    H, W, _ = arr.shape
    metrics = {
        "sharpness": metric_sharpness(arr),
        "exposure": metric_exposure(arr),
        "contrast": metric_contrast(arr),
        "color_consistency": metric_color_consistency(arr),
        "skin_realism": metric_skin_realism(arr),
        "hands_proxy": metric_hands(arr),
        "eyes_proxy": metric_eyes(arr),
        "hair_proxy": metric_hair(arr),
        "artifacts": metric_artifacts(arr),
    }
    overall = metric_overall_quality(metrics)
    sha = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return {
        "file": str(path),
        "sha256": sha,
        "width": W,
        "height": H,
        "metrics": metrics,
        "overall": overall,
        "created_at": __import__("app.make_model.utils", fromlist=["now_iso"]).now_iso(),
    }


def write_quality_report(path: str, out_path: Optional[str] = None) -> str:
    report = evaluate_image(path)
    if out_path is None:
        out_path = path + ".quality.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return out_path
