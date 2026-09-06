"""MAKE Image Engine — Identity Genome.

Persistent identity representations for humans and important objects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class IdentityGenome:
    identity_id: str
    kind: str = "human"
    embedding: Optional[np.ndarray] = None
    face_embedding: Optional[np.ndarray] = None
    body_embedding: Optional[np.ndarray] = None
    hair_embedding: Optional[np.ndarray] = None
    skin_characteristics: Optional[np.ndarray] = None
    age_characteristics: Optional[np.ndarray] = None
    expression_tendencies: Optional[np.ndarray] = None
    clothing_identity: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def merge(self, other: "IdentityGenome", weight: float = 0.5) -> "IdentityGenome":
        if self.embedding is None or other.embedding is None:
            return self
        merged = IdentityGenome(
            identity_id=f"{self.identity_id}__{other.identity_id}",
            kind=self.kind,
            embedding=(1 - weight) * self.embedding + weight * other.embedding,
            face_embedding=(1 - weight) * self.face_embedding + weight * other.face_embedding if self.face_embedding is not None and other.face_embedding is not None else self.face_embedding,
            body_embedding=(1 - weight) * self.body_embedding + weight * other.body_embedding if self.body_embedding is not None and other.body_embedding is not None else self.body_embedding,
            hair_embedding=(1 - weight) * self.hair_embedding + weight * other.hair_embedding if self.hair_embedding is not None and other.hair_embedding is not None else self.hair_embedding,
            skin_characteristics=(1 - weight) * self.skin_characteristics + weight * other.skin_characteristics if self.skin_characteristics is not None and other.skin_characteristics is not None else self.skin_characteristics,
            age_characteristics=(1 - weight) * self.age_characteristics + weight * other.age_characteristics if self.age_characteristics is not None and other.age_characteristics is not None else self.age_characteristics,
            expression_tendencies=(1 - weight) * self.expression_tendencies + weight * other.expression_tendencies if self.expression_tendencies is not None and other.expression_tendencies is not None else self.expression_tendencies,
            clothing_identity=(1 - weight) * self.clothing_identity + weight * other.clothing_identity if self.clothing_identity is not None and other.clothing_identity is not None else self.clothing_identity,
            metadata={**self.metadata, **other.metadata},
        )
        return merged

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            "kind": self.kind,
            "has_embedding": self.embedding is not None,
            "has_face": self.face_embedding is not None,
            "has_body": self.body_embedding is not None,
            "has_hair": self.hair_embedding is not None,
            "has_skin": self.skin_characteristics is not None,
            "has_age": self.age_characteristics is not None,
            "has_expression": self.expression_tendencies is not None,
            "has_clothing": self.clothing_identity is not None,
            "metadata": dict(self.metadata),
        }


class IdentityEncoder:
    def __init__(self, in_dim: int = 128, out_dim: int = 256):
        self.out_dim = out_dim
        self.proj = np.random.uniform(-0.01, 0.01, (in_dim, out_dim)).astype(np.float32)

    def __call__(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float32)
        if x.ndim == 1:
            x = x[None]
        return x @ self.proj


class IdentityPreservationEngine:
    def __init__(self):
        self.registry: Dict[str, IdentityGenome] = {}

    def register(self, genome: IdentityGenome) -> None:
        self.registry[genome.identity_id] = genome

    def get(self, identity_id: str) -> Optional[IdentityGenome]:
        return self.registry.get(identity_id)

    def measure_drift(self, a: IdentityGenome, b: IdentityGenome) -> float:
        if a.embedding is None or b.embedding is None:
            return 1.0
        return float(np.linalg.norm(a.embedding - b.embedding))

    def enforce(self, target: IdentityGenome, current: IdentityGenome, strength: float = 0.8) -> IdentityGenome:
        if target.embedding is None or current.embedding is None:
            return current
        corrected = IdentityGenome(
            identity_id=current.identity_id,
            kind=current.kind,
            embedding=(1 - strength) * current.embedding + strength * target.embedding,
            face_embedding=(1 - strength) * current.face_embedding + strength * target.face_embedding if current.face_embedding is not None and target.face_embedding is not None else current.face_embedding,
            body_embedding=(1 - strength) * current.body_embedding + strength * target.body_embedding if current.body_embedding is not None and target.body_embedding is not None else current.body_embedding,
            hair_embedding=(1 - strength) * current.hair_embedding + strength * target.hair_embedding if current.hair_embedding is not None and target.hair_embedding is not None else current.hair_embedding,
            skin_characteristics=(1 - strength) * current.skin_characteristics + strength * target.skin_characteristics if current.skin_characteristics is not None and target.skin_characteristics is not None else current.skin_characteristics,
            age_characteristics=(1 - strength) * current.age_characteristics + strength * target.age_characteristics if current.age_characteristics is not None and target.age_characteristics is not None else current.age_characteristics,
            expression_tendencies=(1 - strength) * current.expression_tendencies + strength * target.expression_tendencies if current.expression_tendencies is not None and target.expression_tendencies is not None else current.expression_tendencies,
            clothing_identity=(1 - strength) * current.clothing_identity + strength * target.clothing_identity if current.clothing_identity is not None and target.clothing_identity is not None else current.clothing_identity,
            metadata={**current.metadata, **target.metadata},
        )
        return corrected


__all__ = [
    "IdentityGenome",
    "IdentityEncoder",
    "IdentityPreservationEngine",
]
