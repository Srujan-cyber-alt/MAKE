"""
Audio memory: persistent project audio memory.

Stores generated audio artifacts, their provenance, and relationships so
that subsequent generations can reuse or reference earlier work.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class AudioArtifact:
    """A single audio artifact stored in project memory."""

    artifact_id: str
    path: str
    sample_rate: int = 16000
    channels: int = 1
    duration_seconds: float = 0.0
    content_hash: str = ""
    model_id: str = ""
    voice_id: Optional[str] = None
    emotion: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "duration_seconds": self.duration_seconds,
            "content_hash": self.content_hash,
            "model_id": self.model_id,
            "voice_id": self.voice_id,
            "emotion": self.emotion,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioArtifact":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


class AudioMemory:
    """Persistent project audio memory."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else Path("/tmp/audio_memory.json")
        self.artifacts: Dict[str, AudioArtifact] = {}
        self._index_by_voice: Dict[str, Set[str]] = {}
        self._index_by_tag: Dict[str, Set[str]] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return
        for raw in data.get("artifacts", []):
            artifact = AudioArtifact.from_dict(raw)
            self._register(artifact)

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"artifacts": [a.to_dict() for a in self.artifacts.values()]}
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(self.storage_path)

    def _register(self, artifact: AudioArtifact) -> None:
        self.artifacts[artifact.artifact_id] = artifact
        if artifact.voice_id:
            self._index_by_voice.setdefault(artifact.voice_id, set()).add(artifact.artifact_id)
        for tag in artifact.tags:
            self._index_by_tag.setdefault(tag, set()).add(artifact.artifact_id)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add(self, artifact: AudioArtifact) -> AudioArtifact:
        if not artifact.content_hash:
            artifact.content_hash = self._hash_artifact(artifact)
        self._register(artifact)
        self._save()
        return artifact

    def get(self, artifact_id: str) -> Optional[AudioArtifact]:
        return self.artifacts.get(artifact_id)

    def remove(self, artifact_id: str) -> bool:
        artifact = self.artifacts.pop(artifact_id, None)
        if artifact is None:
            return False
        if artifact.voice_id and artifact_id in self._index_by_voice.get(artifact.voice_id, set()):
            self._index_by_voice[artifact.voice_id].discard(artifact_id)
        for tag in artifact.tags:
            if artifact_id in self._index_by_tag.get(tag, set()):
                self._index_by_tag[tag].discard(artifact_id)
        self._save()
        return True

    def clear(self) -> None:
        self.artifacts.clear()
        self._index_by_voice.clear()
        self._index_by_tag.clear()
        self._save()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_all(self) -> List[AudioArtifact]:
        return list(self.artifacts.values())

    def find_by_voice(self, voice_id: str) -> List[AudioArtifact]:
        ids = self._index_by_voice.get(voice_id, set())
        return [self.artifacts[i] for i in ids if i in self.artifacts]

    def find_by_tag(self, tag: str) -> List[AudioArtifact]:
        ids = self._index_by_tag.get(tag, set())
        return [self.artifacts[i] for i in ids if i in self.artifacts]

    def find_by_content_hash(self, content_hash: str) -> List[AudioArtifact]:
        return [a for a in self.artifacts.values() if a.content_hash == content_hash]

    def search(self, query: str, limit: int = 20) -> List[AudioArtifact]:
        q = query.lower()
        results: List[AudioArtifact] = []
        for artifact in self.artifacts.values():
            if q in artifact.artifact_id.lower() or any(q in t.lower() for t in artifact.tags):
                results.append(artifact)
                if len(results) >= limit:
                    break
        return results

    def stats(self) -> Dict[str, Any]:
        return {
            "artifact_count": len(self.artifacts),
            "voice_count": len(self._index_by_voice),
            "tag_count": len(self._index_by_tag),
        }

    def _hash_artifact(self, artifact: AudioArtifact) -> str:
        payload = repr({
            "path": artifact.path,
            "sample_rate": artifact.sample_rate,
            "channels": artifact.channels,
            "duration_seconds": artifact.duration_seconds,
        })
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()