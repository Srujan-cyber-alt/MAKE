"""
Structured conditioning module for the MAKE image v2 architecture.

Beyond a text prompt, the v2 model can be conditioned on:

  - camera: distance (close/medium/wide), angle (eye/low/high/aerial), lens (24/35/50/85/135mm)
  - lighting: time-of-day (dawn/morning/noon/afternoon/golden/blue-hour/night), direction (front/side/back/top), mood (soft/hard/diffuse/rim)
  - material: skin/fabric/wood/metal/glass/stone/foliage/water/sky/concrete
  - composition: rule-of-thirds/centered/symmetric/diagonal/minimal
  - style: photoreal/cinematic/portrait/street/landscape/abstract/film-emulation
  - identity: a stable hashed string that produces a consistent "person/object" identity across samples

Each dimension is encoded as a small learned embedding (8-D per category),
concatenated with the time embedding and the prompt embedding before FiLM.
Identity uses a deeper hash-based embedding (16-D) so that re-sampling the
same identity string with different seeds gives recognizably related outputs.

This is the v2 surface; the v1 model keeps the prompt-only interface for
backwards compatibility.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

import numpy as np


# Categorical enums (kept as plain strings for JSON friendliness)
CAMERA_DISTANCES = ("close", "medium", "wide", "extreme_wide")
CAMERA_ANGLES = ("eye_level", "low", "high", "aerial", "overhead", "dutch")
CAMERA_LENSES = ("24mm", "35mm", "50mm", "85mm", "135mm", "200mm")
LIGHTING_TIME = ("dawn", "morning", "noon", "afternoon", "golden_hour", "blue_hour", "night", "studio")
LIGHTING_DIRECTION = ("front", "side", "back", "top", "under", "rim", "butterfly")
LIGHTING_MOOD = ("soft", "hard", "diffuse", "dramatic", "high_key", "low_key")
MATERIALS = ("skin", "fabric", "wood", "metal", "glass", "stone", "foliage", "water", "sky", "concrete", "plastic", "leather")
COMPOSITIONS = ("rule_of_thirds", "centered", "symmetric", "diagonal", "minimal", "dynamic", "leading_lines")
STYLES = ("photoreal", "cinematic", "portrait", "street", "landscape", "abstract", "film_emulation", "vintage", "monochrome")


def _one_hot(value: str, options: Tuple[str, ...]) -> np.ndarray:
    """Returns a 1-D float32 one-hot vector of length len(options)."""
    out = np.zeros((len(options),), dtype=np.float32)
    if value in options:
        out[options.index(value)] = 1.0
    return out


def _identity_embedding(identity: str, dim: int = 16, seed: int = 0) -> np.ndarray:
    """Deterministic identity embedding. Same identity string -> same vector
    (regardless of random seed elsewhere)."""
    if not identity:
        return np.zeros((dim,), dtype=np.float32)
    h = hashlib.sha256(f"identity::{identity}::v2".encode("utf-8")).digest()
    s = int.from_bytes(h[:8], "big") ^ seed
    rng = np.random.default_rng(s & 0x7FFFFFFF)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= max(1e-6, np.linalg.norm(v))
    return v


def _prompt_embedding_v2(prompt: str, dim: int = 32) -> np.ndarray:
    if not prompt:
        return np.zeros((dim,), dtype=np.float32)
    h = hashlib.sha256(prompt.encode("utf-8")).digest()
    seed = int.from_bytes(h[:8], "big") & 0x7FFFFFFF
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    v /= max(1e-6, np.linalg.norm(v))
    return v


@dataclass
class ConditionVector:
    """Structured conditioning vector. All fields optional; missing fields
    default to "unconditional" (zero embedding)."""
    prompt: str = ""
    camera_distance: str = ""
    camera_angle: str = ""
    camera_lens: str = ""
    lighting_time: str = ""
    lighting_direction: str = ""
    lighting_mood: str = ""
    materials: List[str] = field(default_factory=lambda: ["", "", "", ""])
    composition: str = ""
    style: str = ""
    identity: str = ""
    # Embedding sizes
    prompt_dim: int = 32
    cat_dim: int = 8
    identity_dim: int = 16
    # Unconditional dropout (for classifier-free guidance training)
    drop_prompt: bool = False
    drop_camera: bool = False
    drop_lighting: bool = False
    drop_materials: bool = False
    drop_composition: bool = False
    drop_style: bool = False
    drop_identity: bool = False
    # Number of material slots (always reserved)
    num_material_slots: int = 4

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConditionVector":
        return cls(**d)

    def total_dim(self) -> int:
        return (self.prompt_dim + len(CAMERA_DISTANCES) + len(CAMERA_ANGLES)
                + len(CAMERA_LENSES) + len(LIGHTING_TIME) + len(LIGHTING_DIRECTION)
                + len(LIGHTING_MOOD) + self.num_material_slots * len(MATERIALS)
                + len(COMPOSITIONS) + len(STYLES) + self.identity_dim)

    def to_array(self) -> np.ndarray:
        """Flatten the structured conditioning into a single float32 vector."""
        parts: List[np.ndarray] = []
        if self.drop_prompt:
            parts.append(np.zeros((self.prompt_dim,), dtype=np.float32))
        else:
            parts.append(_prompt_embedding_v2(self.prompt, self.prompt_dim))
        cat_fields = [
            ("camera_distance", self.camera_distance, CAMERA_DISTANCES, self.drop_camera),
            ("camera_angle", self.camera_angle, CAMERA_ANGLES, self.drop_camera),
            ("camera_lens", self.camera_lens, CAMERA_LENSES, self.drop_camera),
            ("lighting_time", self.lighting_time, LIGHTING_TIME, self.drop_lighting),
            ("lighting_direction", self.lighting_direction, LIGHTING_DIRECTION, self.drop_lighting),
            ("lighting_mood", self.lighting_mood, LIGHTING_MOOD, self.drop_lighting),
        ]
        for _name, value, options, dropped in cat_fields:
            if dropped:
                parts.append(np.zeros((len(options),), dtype=np.float32))
            elif value:
                parts.append(_one_hot(value, options))
            else:
                parts.append(np.zeros((len(options),), dtype=np.float32))
        # Materials (multi-hot): each slot is a full one-hot over MATERIALS
        n_mat = max(self.num_material_slots, len(self.materials))
        if self.drop_materials or not self.materials:
            parts.append(np.zeros((n_mat * len(MATERIALS),), dtype=np.float32))
        else:
            mat_vec = np.zeros((n_mat * len(MATERIALS),), dtype=np.float32)
            for i, m in enumerate(self.materials):
                if m in MATERIALS:
                    start = i * len(MATERIALS)
                    mat_vec[start:start + len(MATERIALS)] = _one_hot(m, MATERIALS)
            parts.append(mat_vec)
        # Composition
        if self.drop_composition:
            parts.append(np.zeros((len(COMPOSITIONS),), dtype=np.float32))
        elif self.composition:
            parts.append(_one_hot(self.composition, COMPOSITIONS))
        else:
            parts.append(np.zeros((len(COMPOSITIONS),), dtype=np.float32))
        # Style
        if self.drop_style:
            parts.append(np.zeros((len(STYLES),), dtype=np.float32))
        elif self.style:
            parts.append(_one_hot(self.style, STYLES))
        else:
            parts.append(np.zeros((len(STYLES),), dtype=np.float32))
        # Identity
        if self.drop_identity:
            parts.append(np.zeros((self.identity_dim,), dtype=np.float32))
        else:
            parts.append(_identity_embedding(self.identity, self.identity_dim))
        return np.concatenate(parts).astype(np.float32)


# Default conditioning schema: prompt_dim + 6 cat_dim + 4 mat slots + 2 more
# Each one-hot uses len(options) entries, not cat_dim. We pick sizes that
# match the actual enum lengths to keep the math simple.
#   prompt: 32
#   camera_distance: 4  (close/medium/wide/extreme_wide)
#   camera_angle:     6  (eye/low/high/aerial/overhead/dutch)
#   camera_lens:      6
#   lighting_time:    8
#   lighting_direction: 7
#   lighting_mood:    6
#   materials (4 slots, each 12): 4 * 12 = 48
#   composition:      7
#   style:            9
#   identity:        16
DEFAULT_CONDITION_DIM = (32 + 4 + 6 + 6 + 8 + 7 + 6 + 4 * 12 + 7 + 9 + 16)