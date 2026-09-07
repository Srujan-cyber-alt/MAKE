"""
Advanced editing for the MAKE image subsystem.

Edits:
  - outpaint (expand canvas with mirror fill, then regenerate border)
  - relight (change lighting direction / temperature)
  - recolor (shift hue / saturation of selected regions)
  - background_replace (composite a new background)
  - object_replace (swap object color via mask)

All edits are pure NumPy / PIL and operate on the image array directly.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance


def outpaint(arr: np.ndarray, target_size: int, fill: str = "mirror") -> np.ndarray:
    """Expand an image to `target_size` x `target_size` by mirroring."""
    H, W, _ = arr.shape
    canvas = np.zeros((target_size, target_size, 3), dtype=np.float32)
    # Place original in center
    y0 = max(0, (target_size - H) // 2)
    x0 = max(0, (target_size - W) // 2)
    y1 = min(target_size, y0 + H)
    x1 = min(target_size, x0 + W)
    canvas[y0:y1, x0:x1] = arr[:y1 - y0, :x1 - x0]
    # Mirror-fill the borders
    if fill == "mirror":
        if y0 > 0:
            canvas[:y0] = np.flipud(arr[:y0]) if y0 <= H else np.flipud(arr[:min(y0, H)])
        if y1 < target_size:
            canvas[y1:] = np.flipud(arr[max(0, H - (target_size - y1)):])
        if x0 > 0:
            canvas[:, :x0] = np.fliplr(canvas[:, :x0])
        if x1 < target_size:
            canvas[:, x1:] = np.fliplr(canvas[:, x1:])
    return canvas


def relight(arr: np.ndarray, temperature_shift: float = 0.0,
            brightness: float = 1.0, contrast: float = 1.0) -> np.ndarray:
    """Adjust lighting via brightness/contrast and color temperature."""
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8))
    im = ImageEnhance.Brightness(im).enhance(brightness)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    out = np.asarray(im, dtype=np.float32) / 255.0
    if temperature_shift != 0.0:
        out[:, :, 0] = np.clip(out[:, :, 0] + temperature_shift * 0.1, 0, 1)
        out[:, :, 2] = np.clip(out[:, :, 2] - temperature_shift * 0.1, 0, 1)
    return out


def recolor(arr: np.ndarray, hue_shift_deg: float = 0.0,
            saturation_scale: float = 1.0, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Shift hue and saturation. mask is (H, W) in [0,1]."""
    if mask is None:
        mask = np.ones(arr.shape[:2], dtype=np.float32)
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8))
    if saturation_scale != 1.0:
        im = ImageEnhance.Color(im).enhance(saturation_scale)
    out = np.asarray(im, dtype=np.float32) / 255.0
    if hue_shift_deg != 0.0:
        # Approximate hue shift via channel rotation in HSV-ish space
        shift = hue_shift_deg / 360.0
        r, g, b = out[:, :, 0], out[:, :, 1], out[:, :, 2]
        out[:, :, 0] = np.clip(r * (1 - shift) + g * shift, 0, 1)
        out[:, :, 1] = np.clip(g * (1 - shift) + b * shift, 0, 1)
        out[:, :, 2] = np.clip(b * (1 - shift) + r * shift, 0, 1)
    mask3 = mask[:, :, None]
    return np.clip(arr * (1 - mask3) + out * mask3, 0, 1)


def background_replace(arr: np.ndarray, background: np.ndarray,
                       fg_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Replace background behind a foreground mask."""
    H, W = arr.shape[:2]
    if fg_mask is None:
        fg_mask = np.ones((H, W), dtype=np.float32)
    bg = np.asarray(Image.fromarray((background * 255).round().astype(np.uint8)).resize((W, H)), dtype=np.float32) / 255.0
    m = fg_mask[:, :, None]
    return arr * m + bg * (1 - m)
