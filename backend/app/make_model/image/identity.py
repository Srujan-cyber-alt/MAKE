"""
Identity system for the MAKE image subsystem.

Components:
  - IdentityMemoryBank: per-identity embedding store with LRU eviction.
  - contrastive_identity_loss: pushes same-identity embeddings together
    and different-identity embeddings apart.
  - identity_consistency_score: measures how much a generated sample
    matches a reference identity (cosine similarity on the identity
    bypass embedding).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

import numpy as np


class IdentityMemoryBank:
    """Capped per-identity embedding store.

    Stores the most recent N identity embeddings (LRU-style). Used
    during training to give the model access to previous identity
    examples, and during inference to provide identity-consistent
    samples.
    """

    def __init__(self, capacity: int = 64, dim: int = 16):
        self.capacity = capacity
        self.dim = dim
        self._bank: Dict[str, np.ndarray] = {}
        self._order: List[str] = []

    def add(self, identity: str, embedding: np.ndarray) -> None:
        if not identity:
            return
        emb = np.asarray(embedding, dtype=np.float32).flatten()
        if emb.shape[0] != self.dim:
            return
        if identity not in self._bank:
            if len(self._order) >= self.capacity:
                oldest = self._order.pop(0)
                self._bank.pop(oldest, None)
            self._order.append(identity)
        self._bank[identity] = emb / max(1e-6, np.linalg.norm(emb))

    def get(self, identity: str) -> Optional[np.ndarray]:
        return self._bank.get(identity)

    def all_embeddings(self) -> np.ndarray:
        if not self._bank:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack(list(self._bank.values()), axis=0)

    def __len__(self) -> int:
        return len(self._bank)


def contrastive_identity_loss(id_embeddings: np.ndarray,
                               identities: List[str],
                               bank: IdentityMemoryBank,
                               margin: float = 0.5) -> float:
    """Contrastive identity loss.

    For each sample:
      - if the same identity appears elsewhere in the batch, minimize distance.
      - if a different identity appears, maximize distance beyond margin.
    """
    if id_embeddings.shape[0] < 2:
        return 0.0
    B = id_embeddings.shape[0]
    loss = 0.0
    count = 0
    for i in range(B):
        for j in range(B):
            if i == j:
                continue
            d = 1.0 - np.dot(id_embeddings[i], id_embeddings[j])  # cosine distance
            if identities[i] == identities[j]:
                loss += d
                count += 1
            else:
                loss += max(0.0, margin - d)
                count += 1
    return float(loss / max(1, count))


def identity_consistency_score(generated_identity_emb: np.ndarray,
                                reference_identity_emb: np.ndarray) -> float:
    """Cosine similarity in [-1, 1] mapped to [0, 1]."""
    a = generated_identity_emb.flatten()
    b = reference_identity_emb.flatten()
    if a.shape != b.shape:
        return 0.0
    sim = float(np.dot(a, b) / (max(1e-6, np.linalg.norm(a)) * max(1e-6, np.linalg.norm(b))))
    return (sim + 1.0) / 2.0
