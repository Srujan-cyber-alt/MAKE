"""MAKE Image Engine — Conditioning Engine.

Unified conditioning system accepting text, image, identity, object,
camera, lighting, material, world state, style, composition, and
spatial constraints. Conditioning is composable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Sequence

import numpy as np


# ----------------------------------------------------------------------
# Conditioning bundle
# ----------------------------------------------------------------------


@dataclass
class ConditioningBundle:
    text_emb: Optional[np.ndarray] = None
    image_emb: Optional[np.ndarray] = None
    identity_emb: Optional[np.ndarray] = None
    object_emb: Optional[np.ndarray] = None
    scene_emb: Optional[np.ndarray] = None
    camera_emb: Optional[np.ndarray] = None
    lighting_emb: Optional[np.ndarray] = None
    material_emb: Optional[np.ndarray] = None
    world_emb: Optional[np.ndarray] = None
    mask: Optional[np.ndarray] = None
    depth: Optional[np.ndarray] = None
    pose: Optional[np.ndarray] = None
    edges: Optional[np.ndarray] = None
    segmentation: Optional[np.ndarray] = None
    layout: Optional[np.ndarray] = None
    style_emb: Optional[np.ndarray] = None
    composition_emb: Optional[np.ndarray] = None
    spatial_constraints: Optional[np.ndarray] = None
    seed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for f in [
            "text_emb", "image_emb", "identity_emb", "object_emb", "scene_emb",
            "camera_emb", "lighting_emb", "material_emb", "world_emb",
            "mask", "depth", "pose", "edges", "segmentation", "layout",
            "style_emb", "composition_emb", "spatial_constraints",
        ]:
            val = getattr(self, f, None)
            if val is not None:
                d[f] = val
        d["seed"] = self.seed
        return d


# ----------------------------------------------------------------------
# Conditioning modules
# ----------------------------------------------------------------------


class TextConditioning:
    def __init__(self, vocab_size: int = 4096, embed_dim: int = 128, out_dim: int = 256):
        self.vocab_size = vocab_size
        self.embed_dim = embed_dim
        self.out_dim = out_dim
        self.embed = np.random.uniform(-0.01, 0.01, (vocab_size, embed_dim)).astype(np.float32)
        self.proj = np.random.uniform(-0.01, 0.01, (embed_dim, out_dim)).astype(np.float32)

    def __call__(self, tokens: np.ndarray) -> np.ndarray:
        x = self.embed[np.asarray(tokens, dtype=np.int64)]
        return x @ self.proj


class ImageConditioning:
    def __init__(self, in_channels: int = 3, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_channels, out_dim)).astype(np.float32)

    def __call__(self, image: np.ndarray) -> np.ndarray:
        x = np.asarray(image, dtype=np.float32)
        if x.ndim == 3:
            x = x[None]
        pooled = x.mean(axis=(2, 3))
        return pooled @ self.proj


class IdentityConditioning:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class ObjectConditioning:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class CameraConditioning:
    def __init__(self, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (10, out_dim)).astype(np.float32)

    def __call__(self, camera: Dict[str, Any]) -> np.ndarray:
        x = np.array([
            camera.get("focal_length", 50.0),
            camera.get("aperture", 2.8),
            camera.get("focus_distance", 1.0),
            camera.get("sensor_width", 36.0),
            camera.get("sensor_height", 24.0),
            camera.get("shutter_angle", 180.0),
            camera.get("frame_rate", 24.0),
            camera.get("position", (0.0, 0.0, 1.0))[0],
            camera.get("position", (0.0, 0.0, 1.0))[1],
            camera.get("position", (0.0, 0.0, 1.0))[2],
        ], dtype=np.float32)
        return x @ self.proj


class LightingConditioning:
    def __init__(self, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (12, out_dim)).astype(np.float32)

    def __call__(self, lighting: Dict[str, Any]) -> np.ndarray:
        x = np.array([
            lighting.get("key_intensity", 1.0),
            lighting.get("fill_intensity", 0.3),
            lighting.get("rim_intensity", 0.0),
            lighting.get("ambient", 0.2),
            lighting.get("exposure", 0.0),
            lighting.get("contrast", 1.0),
            lighting.get("key_color", (1.0, 0.95, 0.9))[0],
            lighting.get("key_color", (1.0, 0.95, 0.9))[1],
            lighting.get("key_color", (1.0, 0.95, 0.9))[2],
            lighting.get("key_direction", (0.0, 1.0, 0.0))[0],
            lighting.get("key_direction", (0.0, 1.0, 0.0))[1],
            lighting.get("key_direction", (0.0, 1.0, 0.0))[2],
        ], dtype=np.float32)
        return x @ self.proj


class MaterialConditioning:
    def __init__(self, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (10, out_dim)).astype(np.float32)

    def __call__(self, material: Dict[str, Any]) -> np.ndarray:
        x = np.array([
            material.get("metallic", 0.0),
            material.get("roughness", 0.5),
            material.get("specular", 0.5),
            material.get("clearcoat", 0.0),
            material.get("transmission", 0.0),
            material.get("ior", 1.5),
            material.get("subsurface", 0.0),
            material.get("sheen", 0.0),
            material.get("anisotropic", 0.0),
            material.get("base_color", (0.8, 0.8, 0.8))[0],
        ], dtype=np.float32)
        return x @ self.proj


class WorldConditioning:
    def __init__(self, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (8, out_dim)).astype(np.float32)

    def __call__(self, world: Dict[str, Any]) -> np.ndarray:
        x = np.array([
            len(world.get("scenes", {})) / 10.0,
            len(world.get("objects", {})) / 100.0,
            len(world.get("humans", {})) / 10.0,
            len(world.get("relationships", [])) / 100.0,
            1.0 if world.get("camera") else 0.0,
            1.0 if world.get("lighting") else 0.0,
            1.0 if world.get("environment") else 0.0,
            1.0 if world.get("atmosphere") else 0.0,
        ], dtype=np.float32)
        return x @ self.proj


# ----------------------------------------------------------------------
# Conditioning engine
# ----------------------------------------------------------------------


class ConditioningEngine:
    def __init__(self, dim: int = 256):
        self.dim = dim
        self.text = TextConditioning(out_dim=dim)
        self.image = ImageConditioning(out_dim=dim)
        self.identity = IdentityConditioning(out_dim=dim)
        self.object = ObjectConditioning(out_dim=dim)
        self.camera = CameraConditioning(out_dim=dim)
        self.lighting = LightingConditioning(out_dim=dim)
        self.material = MaterialConditioning(out_dim=dim)
        self.world = WorldConditioning(out_dim=dim)
        self.style_proj = np.random.uniform(-0.01, 0.01, (dim, dim)).astype(np.float32)
        self.composition_proj = np.random.uniform(-0.01, 0.01, (dim, dim)).astype(np.float32)

    def compose(self, bundle: ConditioningBundle) -> np.ndarray:
        c = np.zeros((1, self.dim), dtype=np.float32)
        if bundle.text_emb is not None:
            c = c + np.asarray(bundle.text_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.image_emb is not None:
            c = c + np.asarray(bundle.image_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.identity_emb is not None:
            c = c + np.asarray(bundle.identity_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.object_emb is not None:
            c = c + np.asarray(bundle.object_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.camera_emb is not None:
            c = c + np.asarray(bundle.camera_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.lighting_emb is not None:
            c = c + np.asarray(bundle.lighting_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.material_emb is not None:
            c = c + np.asarray(bundle.material_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.world_emb is not None:
            c = c + np.asarray(bundle.world_emb, dtype=np.float32).mean(axis=0, keepdims=True)
        if bundle.style_emb is not None:
            c = c + np.asarray(bundle.style_emb, dtype=np.float32).mean(axis=0, keepdims=True) @ self.style_proj
        if bundle.composition_emb is not None:
            c = c + np.asarray(bundle.composition_emb, dtype=np.float32).mean(axis=0, keepdims=True) @ self.composition_proj
        return c


def compose_conditioning(
    text: Optional[str] = None,
    image: Optional[np.ndarray] = None,
    identity: Optional[np.ndarray] = None,
    obj: Optional[np.ndarray] = None,
    camera: Optional[Dict[str, Any]] = None,
    lighting: Optional[Dict[str, Any]] = None,
    material: Optional[Dict[str, Any]] = None,
    world: Optional[Dict[str, Any]] = None,
    style: Optional[np.ndarray] = None,
    composition: Optional[np.ndarray] = None,
    seed: int = 0,
) -> ConditioningBundle:
    bundle = ConditioningBundle(seed=seed)
    engine = ConditioningEngine()
    if text is not None:
        tokens = np.array([ord(c) % 4096 for c in text], dtype=np.int64)[:16]
        tokens = np.pad(tokens, (0, max(0, 16 - tokens.size)))
        bundle.text_emb = engine.text(tokens)
    if image is not None:
        bundle.image_emb = engine.image(image)
    if identity is not None:
        bundle.identity_emb = engine.identity(identity)
    if obj is not None:
        bundle.object_emb = engine.object(obj)
    if camera is not None:
        bundle.camera_emb = engine.camera(camera)
    if lighting is not None:
        bundle.lighting_emb = engine.lighting(lighting)
    if material is not None:
        bundle.material_emb = engine.material(material)
    if world is not None:
        bundle.world_emb = engine.world(world)
    if style is not None:
        bundle.style_emb = np.asarray(style, dtype=np.float32)
    if composition is not None:
        bundle.composition_emb = np.asarray(composition, dtype=np.float32)
    return bundle


__all__ = [
    "ConditioningBundle",
    "ConditioningEngine",
    "TextConditioning",
    "ImageConditioning",
    "IdentityConditioning",
    "ObjectConditioning",
    "CameraConditioning",
    "LightingConditioning",
    "MaterialConditioning",
    "WorldConditioning",
    "compose_conditioning",
]
