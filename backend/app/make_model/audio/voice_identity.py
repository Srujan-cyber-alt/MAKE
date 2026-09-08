"""MAKE Audio — Voice Identity Memory.

Persist voice genomes across sessions.  Each identity is stored as JSON and
indexed by a hash so the same voice is always reproduced deterministically.
"""

from __future__ import annotations

import json
import os
import hashlib
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from app.make_model.audio.voice import VoiceGenome


class VoiceIdentity:
    def __init__(self, name: str, genome: VoiceGenome,
                 created_at: Optional[str] = None,
                 updated_at: Optional[str] = None,
                 metadata: Optional[Dict] = None):
        self.name = name
        self.genome = genome
        self.identity_hash = genome.fingerprint()
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.updated_at = updated_at or datetime.utcnow().isoformat()
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "identity_hash": self.identity_hash,
            "genome": self.genome.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "VoiceIdentity":
        return cls(
            name=d["name"],
            genome=VoiceGenome.from_dict(d["genome"]),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            metadata=d.get("metadata", {}),
        )


class VoiceIdentityMemory:
    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        self._cache: Dict[str, VoiceIdentity] = {}
        self._index_path = os.path.join(storage_path, "voice_index.json")
        os.makedirs(storage_path, exist_ok=True)
        self._load_index()

    def _load_index(self) -> None:
        if os.path.isfile(self._index_path):
            with open(self._index_path) as f:
                data = json.load(f)
            for entry in data.get("voices", []):
                self._cache[entry["name"]] = VoiceIdentity.from_dict(entry)

    def _save_index(self) -> None:
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        data = {"voices": [vi.to_dict() for vi in self._cache.values()]}
        with open(self._index_path, "w") as f:
            json.dump(data, f, indent=2)

    def register(self, name: str, genome: VoiceGenome,
                 metadata: Optional[Dict] = None) -> VoiceIdentity:
        identity = VoiceIdentity(name=name, genome=genome, metadata=metadata or {})
        self._cache[name] = identity
        self._save_index()
        return identity

    def get(self, name: str) -> Optional[VoiceIdentity]:
        return self._cache.get(name)

    def get_by_hash(self, hash_prefix: str) -> Optional[VoiceIdentity]:
        for vi in self._cache.values():
            if vi.identity_hash.startswith(hash_prefix):
                return vi
        return None

    def list_voices(self) -> List[str]:
        return sorted(self._cache.keys())

    def update(self, name: str, genome: VoiceGenome) -> VoiceIdentity:
        identity = self._cache.get(name)
        if identity is None:
            identity = VoiceIdentity(name=name, genome=genome)
        else:
            identity.genome = genome
            identity.identity_hash = genome.fingerprint()
            identity.updated_at = datetime.utcnow().isoformat()
        self._cache[name] = identity
        self._save_index()
        return identity

    def remove(self, name: str) -> bool:
        if name in self._cache:
            del self._cache[name]
            self._save_index()
            return True
        return False

    def clear(self) -> None:
        self._cache.clear()
        if os.path.isfile(self._index_path):
            os.remove(self._index_path)

    def save(self) -> None:
        self._save_index()

    def load(self) -> None:
        self._load_index()
