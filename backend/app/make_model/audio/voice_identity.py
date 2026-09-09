"""
Voice Identity Engine - production-level voice identity management.

Features:
- persistent voice genome
- voice embedding (deterministic, seed-controlled)
- speaker consistency
- multi-reference identity
- identity strength control
- identity drift detection
- identity versioning
- identity rollback
- identity provenance
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
import hashlib
import json


@dataclass
class VoiceGenome:
    genome_id: str
    speaker_id: str
    embedding: np.ndarray
    version: int
    created_at: float
    parent_genome_id: Optional[str]
    reference_hashes: List[str]
    strength: float
    provenance: Dict[str, Any]


class VoiceIdentityEngine:
    def __init__(self, embed_dim: int = 128):
        self.embed_dim = embed_dim
        self.genomes: Dict[str, VoiceGenome] = {}
        self._genome_counter = 0

    def _deterministic_embedding(self, speaker_id: str, seed: int = 42, reference_texts: Optional[List[str]] = None) -> np.ndarray:
        rng = np.random.RandomState(seed + hash(speaker_id) % 100000)
        base = rng.normal(0, 1, self.embed_dim).astype(np.float32)
        if reference_texts:
            for txt in reference_texts:
                h = hashlib.sha256(txt.encode()).digest()
                ref_vec = np.frombuffer(h, dtype=np.float32)[:self.embed_dim]
                if len(ref_vec) < self.embed_dim:
                    ref_vec = np.pad(ref_vec, (0, self.embed_dim - len(ref_vec)))
                ref_vec = ref_vec / (np.linalg.norm(ref_vec) + 1e-10)
                base += ref_vec * 0.3
        base = base / (np.linalg.norm(base) + 1e-10)
        return base.astype(np.float32)

    def create_voice(self, speaker_id: str, reference_texts: Optional[List[str]] = None, strength: float = 1.0) -> VoiceGenome:
        self._genome_counter += 1
        genome_id = hashlib.sha256(f"{speaker_id}_{self._genome_counter}".encode()).hexdigest()[:16]
        embedding = self._deterministic_embedding(speaker_id, 42, reference_texts)
        genome = VoiceGenome(
            genome_id=genome_id,
            speaker_id=speaker_id,
            embedding=embedding,
            version=1,
            created_at=float(__import__('time').time()),
            parent_genome_id=None,
            reference_hashes=[hashlib.sha256(t.encode()).hexdigest()[:16] for t in (reference_texts or [])],
            strength=strength,
            provenance={"creation_method": "deterministic_seed", "reference_count": len(reference_texts or [])},
        )
        self.genomes[genome_id] = genome
        return genome

    def branch_voice(
        self, parent_id: str, speaker_id: str,
        reference_texts: Optional[List[str]] = None, strength: float = 1.0,
    ) -> VoiceGenome:
        parent = self.genomes.get(parent_id)
        if parent is None:
            raise ValueError(f"Parent genome {parent_id} not found")
        self._genome_counter += 1
        genome_id = hashlib.sha256(f"{speaker_id}_branch_{self._genome_counter}".encode()).hexdigest()[:16]
        new_embedding = self._deterministic_embedding(speaker_id, 42 + len(parent.embedding), reference_texts)
        blended = parent.embedding * 0.7 + new_embedding * 0.3
        blended = blended / (np.linalg.norm(blended) + 1e-10)
        genome = VoiceGenome(
            genome_id=genome_id,
            speaker_id=speaker_id,
            embedding=blended,
            version=parent.version + 1,
            created_at=float(__import__('time').time()),
            parent_genome_id=parent_id,
            reference_hashes=[hashlib.sha256(t.encode()).hexdigest()[:16] for t in (reference_texts or [])] + parent.reference_hashes,
            strength=strength,
            provenance={"creation_method": "branch_with_blend", "parent_id": parent_id, "blend_ratio": 0.7},
        )
        self.genomes[genome_id] = genome
        return genome

    def get_voice(self, genome_id: str) -> Optional[VoiceGenome]:
        return self.genomes.get(genome_id)

    def get_active_voice(self, speaker_id: str) -> Optional[VoiceGenome]:
        candidates = [g for g in self.genomes.values() if g.speaker_id == speaker_id]
        if not candidates:
            return None
        return max(candidates, key=lambda g: g.version)

    def detect_drift(self, genome_id: str, new_embedding: np.ndarray, threshold: float = 0.1) -> Tuple[float, bool]:
        genome = self.genomes.get(genome_id)
        if genome is None:
            return 0.0, False
        drift = float(1.0 - np.dot(genome.embedding, new_embedding))
        drift = np.clip(drift, 0, 2.0)
        return float(drift), bool(drift > threshold)

    def check_consistency(self, embeddings: List[np.ndarray]) -> float:
        if len(embeddings) < 2:
            return 1.0
        centroid = np.mean(embeddings, axis=0)
        centroid = centroid / (np.linalg.norm(centroid) + 1e-10)
        deviations = []
        for emb in embeddings:
            emb_n = emb / (np.linalg.norm(emb) + 1e-10)
            deviations.append(float(np.dot(centroid, emb_n)))
        return float(np.mean(deviations))

    def rollback(self, speaker_id: str, to_version: int) -> Optional[VoiceGenome]:
        candidates = [g for g in self.genomes.values() if g.speaker_id == speaker_id and g.version <= to_version]
        if not candidates:
            return None
        return max(candidates, key=lambda g: g.version)

    def get_history(self, speaker_id: str) -> List[VoiceGenome]:
        return sorted(
            [g for g in self.genomes.values() if g.speaker_id == speaker_id],
            key=lambda g: g.version,
        )

    def multi_reference_identity(
        self, speaker_id: str, references: List[Tuple[List[str], float]],
    ) -> VoiceGenome:
        self._genome_counter += 1
        genome_id = hashlib.sha256(f"{speaker_id}_multi_{self._genome_counter}".encode()).hexdigest()[:16]
        embeddings = []
        for ref_texts, weight in references:
            emb = self._deterministic_embedding(speaker_id, 42, ref_texts)
            embeddings.append((emb, weight))
        combined = np.zeros(self.embed_dim, dtype=np.float32)
        total_weight = sum(w for _, w in embeddings)
        for emb, w in embeddings:
            combined += emb * (w / total_weight)
        combined = combined / (np.linalg.norm(combined) + 1e-10)
        genome = VoiceGenome(
            genome_id=genome_id,
            speaker_id=speaker_id,
            embedding=combined,
            version=len([g for g in self.genomes.values() if g.speaker_id == speaker_id]) + 1,
            created_at=float(__import__('time').time()),
            parent_genome_id=None,
            reference_hashes=[],
            strength=1.0,
            provenance={"creation_method": "multi_reference_blend", "reference_count": len(references)},
        )
        self.genomes[genome_id] = genome
        return genome

    def serialize(self) -> Dict[str, Any]:
        return {
            "embed_dim": self.embed_dim,
            "genomes": {
                gid: {
                    "genome_id": g.genome_id,
                    "speaker_id": g.speaker_id,
                    "embedding": g.embedding.tolist(),
                    "version": g.version,
                    "created_at": g.created_at,
                    "parent_genome_id": g.parent_genome_id,
                    "reference_hashes": g.reference_hashes,
                    "strength": g.strength,
                    "provenance": g.provenance,
                }
                for gid, g in self.genomes.items()
            },
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.embed_dim = data["embed_dim"]
        for gid, g_data in data["genomes"].items():
            genome = VoiceGenome(
                genome_id=g_data["genome_id"],
                speaker_id=g_data["speaker_id"],
                embedding=np.array(g_data["embedding"], dtype=np.float32),
                version=g_data["version"],
                created_at=g_data["created_at"],
                parent_genome_id=g_data["parent_genome_id"],
                reference_hashes=g_data["reference_hashes"],
                strength=g_data["strength"],
                provenance=g_data["provenance"],
            )
            self.genomes[gid] = genome
