"""MAKE Image Engine — Object Genome.

Persistent object representations and manipulation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class ObjectGenome:
    object_id: str
    label: str = "object"
    embedding: Optional[np.ndarray] = None
    geometry_signature: Optional[np.ndarray] = None
    material_signature: Optional[np.ndarray] = None
    color_signature: Optional[np.ndarray] = None
    texture_signature: Optional[np.ndarray] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    mask: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def transform(self, operation: str, params: Dict[str, Any]) -> "ObjectGenome":
        new = ObjectGenome(
            object_id=f"{self.object_id}_{operation}",
            label=self.label,
            embedding=self.embedding,
            geometry_signature=self.geometry_signature,
            material_signature=self.material_signature,
            color_signature=self.color_signature,
            texture_signature=self.texture_signature,
            bbox=self.bbox,
            mask=self.mask,
            metadata={**self.metadata, "last_operation": operation, "last_params": params},
        )
        if operation == "move" and self.bbox:
            dx = params.get("dx", 0.0)
            dy = params.get("dy", 0.0)
            x1, y1, x2, y2 = self.bbox
            new.bbox = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
        elif operation == "resize" and self.bbox:
            scale = params.get("scale", 1.0)
            cx = (self.bbox[0] + self.bbox[2]) / 2
            cy = (self.bbox[1] + self.bbox[3]) / 2
            hw = (self.bbox[2] - self.bbox[0]) * scale / 2
            hh = (self.bbox[3] - self.bbox[1]) * scale / 2
            new.bbox = (cx - hw, cy - hh, cx + hw, cy + hh)
        elif operation == "recolor" and self.color_signature is not None:
            tint = np.array(params.get("tint", [1.0, 1.0, 1.0]), dtype=np.float32)
            new.color_signature = self.color_signature * tint
        elif operation == "retexture" and self.texture_signature is not None:
            noise = np.random.uniform(-0.05, 0.05, self.texture_signature.shape).astype(np.float32)
            new.texture_signature = self.texture_signature + noise
        elif operation == "rotate" and self.geometry_signature is not None:
            angle = params.get("angle", 0.0)
            new.geometry_signature = self.geometry_signature + np.full_like(self.geometry_signature, angle * 0.01)
        return new

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "label": self.label,
            "has_embedding": self.embedding is not None,
            "has_geometry": self.geometry_signature is not None,
            "has_material": self.material_signature is not None,
            "has_color": self.color_signature is not None,
            "has_texture": self.texture_signature is not None,
            "bbox": list(self.bbox) if self.bbox else None,
            "metadata": dict(self.metadata),
        }


class ObjectEncoder:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class ObjectManipulationEngine:
    def __init__(self):
        self.registry: Dict[str, ObjectGenome] = {}

    def register(self, obj: ObjectGenome) -> None:
        self.registry[obj.object_id] = obj

    def get(self, object_id: str) -> Optional[ObjectGenome]:
        return self.registry.get(object_id)

    def move(self, object_id: str, dx: float = 0.0, dy: float = 0.0) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = obj.transform("move", {"dx": dx, "dy": dy})
        self.register(new)
        return new

    def resize(self, object_id: str, scale: float = 1.0) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = obj.transform("resize", {"scale": scale})
        self.register(new)
        return new

    def recolor(self, object_id: str, tint: List[float]) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = obj.transform("recolor", {"tint": tint})
        self.register(new)
        return new

    def retexture(self, object_id: str) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = obj.transform("retexture", {})
        self.register(new)
        return new

    def rotate(self, object_id: str, angle: float) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = obj.transform("rotate", {"angle": angle})
        self.register(new)
        return new

    def duplicate(self, object_id: str) -> Optional[ObjectGenome]:
        obj = self.get(object_id)
        if obj is None:
            return None
        new = ObjectGenome(
            object_id=f"{object_id}_dup",
            label=obj.label,
            embedding=obj.embedding.copy() if obj.embedding is not None else None,
            geometry_signature=obj.geometry_signature.copy() if obj.geometry_signature is not None else None,
            material_signature=obj.material_signature.copy() if obj.material_signature is not None else None,
            color_signature=obj.color_signature.copy() if obj.color_signature is not None else None,
            texture_signature=obj.texture_signature.copy() if obj.texture_signature is not None else None,
            bbox=obj.bbox,
            mask=obj.mask.copy() if obj.mask is not None else None,
            metadata={**obj.metadata, "duplicated_from": object_id},
        )
        self.register(new)
        return new

    def remove(self, object_id: str) -> bool:
        if object_id in self.registry:
            del self.registry[object_id]
            return True
        return False

    def replace(self, object_id: str, replacement: ObjectGenome) -> Optional[ObjectGenome]:
        if object_id not in self.registry:
            return None
        replacement.object_id = object_id
        self.register(replacement)
        return replacement


__all__ = [
    "ObjectGenome",
    "ObjectEncoder",
    "ObjectManipulationEngine",
]
