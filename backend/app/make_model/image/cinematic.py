"""
Cinematic engine: camera, lighting, composition, style presets, and filmic
tone mapping for the MAKE image subsystem.

Everything here is pure-NumPy / PIL post-processing. No PyTorch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


@dataclass
class CameraSettings:
    focal_length_mm: float = 50.0
    aperture: float = 2.8
    shutter_angle: float = 180.0
    focus_distance: float = 3.0
    camera_height: str = "eye_level"
    camera_angle: str = "eye_level"
    lens_distortion: float = 0.0
    field_of_view_deg: float = 46.0


@dataclass
class LightingSettings:
    time_of_day: str = "golden_hour"
    direction: str = "side"
    mood: str = "soft"
    key_intensity: float = 1.0
    fill_intensity: float = 0.3
    rim_intensity: float = 0.4
    color_temperature_k: float = 3200.0
    haze: float = 0.0
    volumetric: float = 0.0


@dataclass
class CompositionSettings:
    rule: str = "rule_of_thirds"
    subject_placement: str = "center"
    foreground_separation: float = 0.5
    leading_lines: bool = True
    symmetry: bool = False


@dataclass
class StyleSettings:
    preset: str = "cinematic"
    contrast: float = 1.2
    saturation: float = 1.1
    warmth: float = 0.05
    grain: float = 0.03
    vignette: float = 0.15
    highlight_rolloff: float = 0.9
    shadow_lift: float = 0.02
    tone_curve: str = "filmic"


CINEMATIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "imax_inspired": {
        "camera": CameraSettings(focal_length_mm=24.0, aperture=5.6, camera_height="low"),
        "lighting": LightingSettings(time_of_day="golden_hour", direction="front", mood="soft"),
        "composition": CompositionSettings(rule="rule_of_thirds", subject_placement="lower_third"),
        "style": StyleSettings(preset="imax", contrast=1.3, saturation=1.2, warmth=0.08, vignette=0.2),
    },
    "premium_commercial": {
        "camera": CameraSettings(focal_length_mm=85.0, aperture=1.4, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="studio", direction="front", mood="soft"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="commercial", contrast=1.15, saturation=1.05, warmth=0.0, vignette=0.05),
    },
    "hollywood_style": {
        "camera": CameraSettings(focal_length_mm=50.0, aperture=2.0, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="studio", direction="side", mood="dramatic"),
        "composition": CompositionSettings(rule="rule_of_thirds", subject_placement="center"),
        "style": StyleSettings(preset="hollywood", contrast=1.4, saturation=1.15, warmth=0.05, vignette=0.25),
    },
    "documentary": {
        "camera": CameraSettings(focal_length_mm=35.0, aperture=4.0, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="morning", direction="side", mood="soft"),
        "composition": CompositionSettings(rule="rule_of_thirds", leading_lines=True),
        "style": StyleSettings(preset="documentary", contrast=1.05, saturation=1.0, warmth=0.02, vignette=0.05, grain=0.05),
    },
    "fashion_editorial": {
        "camera": CameraSettings(focal_length_mm=85.0, aperture=1.8, camera_height="high"),
        "lighting": LightingSettings(time_of_day="studio", direction="front", mood="soft"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="fashion", contrast=1.25, saturation=1.1, warmth=0.0, vignette=0.1, grain=0.02),
    },
    "portrait_photography": {
        "camera": CameraSettings(focal_length_mm=85.0, aperture=1.4, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="golden_hour", direction="side", mood="soft"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="portrait", contrast=1.1, saturation=1.0, warmth=0.03, vignette=0.2, grain=0.02),
    },
    "luxury_product": {
        "camera": CameraSettings(focal_length_mm=100.0, aperture=5.6, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="studio", direction="top", mood="soft"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="luxury", contrast=1.2, saturation=1.05, warmth=0.0, vignette=0.1, grain=0.0),
    },
    "architectural": {
        "camera": CameraSettings(focal_length_mm=24.0, aperture=8.0, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="noon", direction="side", mood="soft"),
        "composition": CompositionSettings(rule="symmetry", symmetry=True),
        "style": StyleSettings(preset="arch", contrast=1.15, saturation=0.9, warmth=0.0, vignette=0.0, grain=0.01),
    },
    "nature": {
        "camera": CameraSettings(focal_length_mm=35.0, aperture=5.6, camera_height="low"),
        "lighting": LightingSettings(time_of_day="golden_hour", direction="back", mood="soft"),
        "composition": CompositionSettings(rule="rule_of_thirds", leading_lines=True),
        "style": StyleSettings(preset="nature", contrast=1.1, saturation=1.15, warmth=0.05, vignette=0.1, grain=0.03),
    },
    "night_cinema": {
        "camera": CameraSettings(focal_length_mm=35.0, aperture=1.4, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="night", direction="front", mood="dramatic"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="night", contrast=1.4, saturation=0.8, warmth=0.1, vignette=0.3, grain=0.06),
    },
    "golden_hour_cinema": {
        "camera": CameraSettings(focal_length_mm=50.0, aperture=2.0, camera_height="low"),
        "lighting": LightingSettings(time_of_day="golden_hour", direction="back", mood="soft"),
        "composition": CompositionSettings(rule="rule_of_thirds", leading_lines=True),
        "style": StyleSettings(preset="golden", contrast=1.25, saturation=1.2, warmth=0.1, vignette=0.2, grain=0.02),
    },
    "studio_photography": {
        "camera": CameraSettings(focal_length_mm=85.0, aperture=5.6, camera_height="eye_level"),
        "lighting": LightingSettings(time_of_day="studio", direction="top", mood="soft"),
        "composition": CompositionSettings(rule="centered", subject_placement="center"),
        "style": StyleSettings(preset="studio", contrast=1.1, saturation=1.0, warmth=0.0, vignette=0.05, grain=0.0),
    },
}


# ---------------------------------------------------------------------------
# Film / cinematic post-processing (pure NumPy / PIL)
# ---------------------------------------------------------------------------


def _arr_to_pil(arr: np.ndarray) -> Image.Image:
    arr = np.clip(arr, 0, 1)
    return Image.fromarray((arr * 255.0).round().astype(np.uint8))


def _pil_to_arr(im: Image.Image) -> np.ndarray:
    return np.asarray(im, dtype=np.float32) / 255.0


def apply_filmic_tone_map(arr: np.ndarray, highlight_rolloff: float = 0.9,
                          shadow_lift: float = 0.02) -> np.ndarray:
    """Simple filmic S-curve tone map applied per-channel."""
    x = arr.astype(np.float32)
    x = np.clip(x, 0.0, 1.0)
    # Sigmoid S-curve
    k = 8.0
    x = 1.0 / (1.0 + np.exp(-k * (x - 0.5)))
    x = (x - x.min(axis=(0, 1), keepdims=True)) / max(x.max(axis=(0, 1), keepdims=True).max(), 1e-6)
    # Roll off highlights, lift shadows
    x = highlight_rolloff * x + shadow_lift
    return np.clip(x, 0.0, 1.0)


def apply_vignette(arr: np.ndarray, strength: float = 0.15) -> np.ndarray:
    H, W, _ = arr.shape
    cy, cx = H / 2, W / 2
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(cx, cy)
    vig = 1.0 - strength * (r ** 1.5)
    vig = np.clip(vig, 0.0, 1.0)[:, :, None]
    return arr * vig


def apply_grain(arr: np.ndarray, strength: float = 0.03, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(arr.shape).astype(np.float32) * strength
    return np.clip(arr + noise, 0.0, 1.0)


def apply_color_temp(arr: np.ndarray, temp_k: float = 3200.0) -> np.ndarray:
    """Shift color temperature. 6500K is neutral; lower = warmer."""
    neutral = 6500.0
    t = (temp_k - neutral) / (neutral + 1e-6)
    r_gain = 1.0 + 0.4 * t
    b_gain = 1.0 - 0.4 * t
    out = arr.copy()
    out[:, :, 0] *= r_gain
    out[:, :, 2] *= b_gain
    return np.clip(out, 0.0, 1.0)


def apply_style_preset(arr: np.ndarray, style: StyleSettings,
                       seed: int = 0) -> np.ndarray:
    """Apply a cinematic style preset to a float32 RGB image in [0,1]."""
    im = _arr_to_pil(arr)
    # Contrast
    im = ImageEnhance.Contrast(im).enhance(style.contrast)
    # Saturation
    im = ImageEnhance.Color(im).enhance(style.saturation)
    arr = _pil_to_arr(im)
    # Color temperature
    arr = apply_color_temp(arr, style.color_temperature_k)
    # Tone curve
    arr = apply_filmic_tone_map(arr, style.highlight_rolloff, style.shadow_lift)
    # Vignette
    arr = apply_vignette(arr, style.vignette)
    # Grain
    arr = apply_grain(arr, style.grain, seed=seed)
    return arr


def apply_lighting_condition(arr: np.ndarray, lighting: LightingSettings) -> np.ndarray:
    """Approximate lighting modification via brightness/contrast shifts."""
    im = _arr_to_pil(arr)
    # Key intensity
    if lighting.key_intensity != 1.0:
        im = ImageEnhance.Brightness(im).enhance(lighting.key_intensity)
    # Mood via contrast
    mood_contrast = {"soft": 0.9, "hard": 1.3, "diffuse": 0.85,
                     "dramatic": 1.4, "high_key": 0.9, "low_key": 1.3}.get(lighting.mood, 1.0)
    im = ImageEnhance.Contrast(im).enhance(mood_contrast)
    # Color temperature
    return _pil_to_arr(im)


# ---------------------------------------------------------------------------
# Camera effects
# ---------------------------------------------------------------------------


def apply_lens_effects(arr: np.ndarray, cam: CameraSettings) -> np.ndarray:
    """Simulate lens characteristics: bokeh, barrel/pincushion, sharpness."""
    # Focal length affects the perceived perspective (approximated by a
    # gentle central crop + resize, simulating the "telephoto look").
    H, W, _ = arr.shape
    fl = cam.focal_length_mm
    crop_frac = max(0.5, min(1.0, 24.0 / max(fl, 1.0)))
    if crop_frac < 1.0:
        cy, cx = int(H * (1 - crop_frac) / 2), int(W * (1 - crop_frac) / 2)
        cy2, cx2 = int(H - cy), int(W - cx)
        arr = arr[cy:cy2, cx:cx2, :]
        im = Image.fromarray((arr * 255).round().astype(np.uint8)).resize((W, H), Image.BILINEAR)
        arr = np.asarray(im, dtype=np.float32) / 255.0
    # Aperture affects contrast / micro-contrast
    ap = cam.aperture
    im = _arr_to_pil(arr)
    if ap < 2.8:
        im = im.filter(ImageFilter.GaussianBlur(radius=0.5))
    arr = _pil_to_arr(im)
    return arr
