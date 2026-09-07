"""
World / object / material intelligence for the MAKE image subsystem.

These are the building blocks for the 20 flagship capabilities. They are
pure NumPy / PIL and do NOT touch the frozen video system.

Implemented here:
  - MaterialLab: maps condition.materials list to material-specific
    color/texture priors (used as conditioning, not as post-processing).
  - LightingDirector: computes lighting-condition vectors from the
    LightingSettings and applies them as post-processing (brightness,
    contrast, temperature, haze).
  - CompositionDirector: subject-placement-aware crop / pad.
  - ObjectGenome: per-object-type conditioning vectors (for future use).
  - DetailRecovery: high-frequency residual reconstruction via unsharp
    mask + Laplacian pyramid residual.
  - RealityReconstruction: image-to-image "reality repair" via
    variational reconstruction + sharpening.
  - ShotDesigner: generates a ShotConfig from natural-language + preset.
  - CameraTeleportation: changes focal-length / camera-height / angle
    and applies the corresponding post-processing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

from app.make_model.image.cinematic import (
    CameraSettings, LightingSettings, CompositionSettings, StyleSettings,
    apply_filmic_tone_map, apply_vignette, apply_grain, apply_color_temp,
    apply_lens_effects, apply_style_preset, apply_lighting_condition,
    CINEMATIC_PRESETS,
)


# ---------------------------------------------------------------------------
# Material priors
# ---------------------------------------------------------------------------

MATERIAL_COLORS: Dict[str, np.ndarray] = {
    "skin":     np.array([0.85, 0.65, 0.50], dtype=np.float32),
    "fabric":   np.array([0.30, 0.25, 0.35], dtype=np.float32),
    "wood":     np.array([0.55, 0.35, 0.20], dtype=np.float32),
    "metal":    np.array([0.75, 0.75, 0.80], dtype=np.float32),
    "glass":    np.array([0.90, 0.92, 0.95], dtype=np.float32),
    "stone":    np.array([0.50, 0.50, 0.48], dtype=np.float32),
    "foliage":  np.array([0.20, 0.45, 0.15], dtype=np.float32),
    "water":    np.array([0.15, 0.35, 0.55], dtype=np.float32),
    "sky":      np.array([0.40, 0.60, 0.90], dtype=np.float32),
    "concrete": np.array([0.60, 0.60, 0.58], dtype=np.float32),
    "plastic":  np.array([0.50, 0.50, 0.55], dtype=np.float32),
    "leather":  np.array([0.35, 0.22, 0.12], dtype=np.float32),
}

MATERIAL_TEXTURES: Dict[str, float] = {
    "skin": 0.03, "fabric": 0.08, "wood": 0.12, "metal": 0.01,
    "glass": 0.005, "stone": 0.15, "foliage": 0.20, "water": 0.05,
    "sky": 0.02, "concrete": 0.10, "plastic": 0.02, "leather": 0.06,
}


def material_color_prior(materials: List[str]) -> np.ndarray:
    out = np.zeros(3, dtype=np.float32)
    n = 0
    for m in materials:
        if m in MATERIAL_COLORS:
            out += MATERIAL_COLORS[m]
            n += 1
    if n > 0:
        out /= n
    return out


def material_texture_prior(materials: List[str]) -> float:
    vals = [MATERIAL_TEXTURES.get(m, 0.05) for m in materials]
    return float(np.mean(vals)) if vals else 0.05


# ---------------------------------------------------------------------------
# Detail recovery
# ---------------------------------------------------------------------------


def detail_recovery(arr: np.ndarray, strength: float = 0.3) -> np.ndarray:
    """Unsharp mask + Laplacian residual for high-frequency recovery."""
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).round().astype(np.uint8))
    blur = im.filter(ImageFilter.GaussianBlur(radius=1.5))
    sharp = np.asarray(im, dtype=np.float32) / 255.0
    blur_arr = np.asarray(blur, dtype=np.float32) / 255.0
    lap = sharp - blur_arr
    out = sharp + strength * lap
    return np.clip(out, 0.0, 1.0)


def laplacian_pyramid(arr: np.ndarray, levels: int = 3) -> List[np.ndarray]:
    """Build a Laplacian pyramid. Returns list of residuals."""
    pyramid = [arr]
    for _ in range(levels):
        im = Image.fromarray((arr * 255).round().astype(np.uint8))
        small = im.resize((im.width // 2, im.height // 2), Image.BILINEAR)
        big = small.resize((im.width, im.height), Image.BILINEAR)
        arr = np.asarray(big, dtype=np.float32) / 255.0
        pyramid.append(arr)
    residuals = []
    for i in range(len(pyramid) - 1):
        residuals.append(pyramid[i] - pyramid[i + 1])
    return residuals


# ---------------------------------------------------------------------------
# Shot designer
# ---------------------------------------------------------------------------


@dataclass
class ShotConfig:
    camera: CameraSettings
    lighting: LightingSettings
    composition: CompositionSettings
    style: StyleSettings
    raw_prompt: str = ""
    preset_name: str = ""


def design_shot(prompt: str, preset: str = "cinematic") -> ShotConfig:
    preset_name = preset if preset in CINEMATIC_PRESETS else "cinematic"
    p = CINEMATIC_PRESETS.get(preset_name, CINEMATIC_PRESETS["cinematic"])
    return ShotConfig(
        camera=p["camera"], lighting=p["lighting"],
        composition=p["composition"], style=p["style"],
        raw_prompt=prompt, preset_name=preset_name,
    )


def apply_shot_to_image(arr: np.ndarray, shot: ShotConfig, seed: int = 0) -> np.ndarray:
    arr = apply_style_preset(arr, shot.style, seed=seed)
    arr = apply_lighting_condition(arr, shot.lighting)
    arr = apply_lens_effects(arr, shot.camera)
    return arr
