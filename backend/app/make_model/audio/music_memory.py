"""
Persistent musical identity with motifs.

Stores a musical DNA for a project or artist, including recurring motifs
that can be reused across cues.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.music_intelligence_v2 import (
    MusicIntelligence,
    Key,
    Meter,
    Harmony,
    Melody,
    RhythmPattern,
    Instrumentation,
)


@dataclass
class MusicalMotif:
    """A recurring musical idea."""

    motif_id: str
    notes: List[int] = field(default_factory=list)
    rhythm: List[float] = field(default_factory=list)
    instruments: List[str] = field(default_factory=list)
    name: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "motif_id": self.motif_id,
            "notes": list(self.notes),
            "rhythm": list(self.rhythm),
            "instruments": list(self.instruments),
            "name": self.name,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicalMotif":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def hash(self) -> str:
        payload = repr({"notes": self.notes, "rhythm": self.rhythm, "instruments": self.instruments})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class MusicMemory:
    """Persistent musical identity with motifs."""

    def __init__(self, memory_id: str = "") -> None:
        self.memory_id = memory_id or f"music_{int(time.time())}"
        self.musical_dna: Optional[MusicIntelligence] = None
        self.motifs: Dict[str, MusicalMotif] = {}
        self.cues: List[Dict[str, Any]] = []
        self.created_at = time.time()
        self.updated_at = self.created_at

    # ------------------------------------------------------------------
    # DNA management
    # ------------------------------------------------------------------
    def set_dna(self, dna: MusicIntelligence) -> None:
        self.musical_dna = dna
        self.updated_at = time.time()

    def get_dna(self) -> Optional[MusicIntelligence]:
        return self.musical_dna

    # ------------------------------------------------------------------
    # Motif management
    # ------------------------------------------------------------------
    def add_motif(self, motif: MusicalMotif) -> MusicalMotif:
        self.motifs[motif.motif_id] = motif
        self.updated_at = time.time()
        return motif

    def get_motif(self, motif_id: str) -> Optional[MusicalMotif]:
        return self.motifs.get(motif_id)

    def remove_motif(self, motif_id: str) -> bool:
        if motif_id not in self.motifs:
            return False
        del self.motifs[motif_id]
        self.updated_at = time.time()
        return True

    def list_motifs(self) -> List[MusicalMotif]:
        return list(self.motifs.values())

    def find_motifs_by_notes(self, notes: List[int]) -> List[MusicalMotif]:
        note_set = set(notes)
        return [m for m in self.motifs.values() if note_set.issubset(set(m.notes))]

    # ------------------------------------------------------------------
    # Cue management
    # ------------------------------------------------------------------
    def add_cue(self, cue: Dict[str, Any]) -> Dict[str, Any]:
        cue = dict(cue)
        cue.setdefault("timestamp", time.time())
        self.cues.append(cue)
        self.updated_at = time.time()
        return cue

    def list_cues(self) -> List[Dict[str, Any]]:
        return list(self.cues)

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "musical_dna": self.musical_dna.to_dict() if self.musical_dna else None,
            "motifs": {mid: m.to_dict() for mid, m in self.motifs.items()},
            "cues": list(self.cues),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MusicMemory":
        mem = cls(memory_id=data.get("memory_id", ""))
        mem.created_at = data.get("created_at", time.time())
        mem.updated_at = data.get("updated_at", time.time())
        if data.get("musical_dna"):
            mem.musical_dna = MusicIntelligence.from_dict(data["musical_dna"])
        for raw in data.get("motifs", {}).values():
            mem.add_motif(MusicalMotif.from_dict(raw))
        mem.cues = list(data.get("cues", []))
        return mem

    def identity_hash(self) -> str:
        payload = repr({
            "dna": self.musical_dna.to_dict() if self.musical_dna else None,
            "motifs": sorted(m.hash() for m in self.motifs.values()),
        })
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]