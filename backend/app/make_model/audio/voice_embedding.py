"""
Deterministic voice embedding generator.

A SHA-256 hash of the ``voice_id`` seeds a NumPy ``RandomState`` so that the
same voice always produces the same embedding vector.  The embedding is a
fixed-length numeric fingerprint used downstream by the voice identity store
and the consistency engine.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

import numpy as np


def _hash_to_seed(value: str) -> int:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class VoiceEmbedding:
    """Deterministic embedding derived from a voice id."""

    DEFAULT_DIM = 256

    def __init__(self, dim: int = DEFAULT_DIM, seed: Optional[int] = None) -> None:
        self.dim = dim
        self.seed = seed if seed is not None else 0
        self._rng: Optional[np.random.RandomState] = None

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------
    def embed(self, voice_id: str) -> np.ndarray:
        """Return a deterministic embedding vector for ``voice_id``."""
        seed = _hash_to_seed(voice_id) ^ (self.seed & 0xFFFFFFFF)
        rng = np.random.RandomState(seed)
        # Use a Gaussian distribution so the embedding has unit-ish variance.
        vec = rng.normal(0.0, 1.0, self.dim).astype(np.float32)
        # Normalise to unit length for cosine similarity comparisons.
        norm = float(np.linalg.norm(vec))
        if norm > 0.0:
            vec = vec / norm
        return vec

    def embed_many(self, voice_ids: List[str]) -> Dict[str, np.ndarray]:
        return {vid: self.embed(vid) for vid in voice_ids}

    def similarity(self, voice_id_a: str, voice_id_b: str) -> float:
        a = self.embed(voice_id_a)
        b = self.embed(voice_id_b)
        return float(np.clip(np.dot(a, b), -1.0, 1.0))

    def distance(self, voice_id_a: str, voice_id_b: str) -> float:
        a = self.embed(voice_id_a)
        b = self.embed(voice_id_b)
        return float(np.linalg.norm(a - b))

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"dim": self.dim, "seed": self.seed, "type": "VoiceEmbedding"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceEmbedding":
        return cls(dim=data.get("dim", cls.DEFAULT_DIM), seed=data.get("seed", 0))

    @property
    def rng(self) -> np.random.RandomState:
        if self._rng is None:
            self._rng = np.random.RandomState(self.seed)
        return self._rng