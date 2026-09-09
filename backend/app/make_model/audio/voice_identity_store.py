"""
Persistent JSON-backed store for voice identities.

Implements atomic writes (write to temp file then rename) so a crash mid-save
can never leave a corrupt primary file.  Provides full CRUD semantics over
``VoiceGenome`` objects keyed by ``voice_id``.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.make_model.audio.voice_genome import VoiceGenome


class VoiceIdentityStore:
    """Persistent JSON storage with atomic writes and CRUD operations."""

    def __init__(self, storage_path: str = "/tmp/voice_identities.json") -> None:
        self.storage_path = Path(storage_path)
        self._voices: Dict[str, VoiceGenome] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return
        for vid, raw in data.items():
            if isinstance(raw, dict):
                self._voices[vid] = VoiceGenome.from_dict(raw)

    def _atomic_write(self, data: Dict[str, Any]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        # Write to a sibling temp file and rename for atomicity.
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self.storage_path.parent),
            prefix=self.storage_path.name + ".",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, self.storage_path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _save(self) -> None:
        payload = {vid: voice.to_dict() for vid, voice in self._voices.items()}
        self._atomic_write(payload)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def create(self, voice: VoiceGenome) -> VoiceGenome:
        voice.created_at = time.time()
        voice.updated_at = voice.created_at
        self._voices[voice.voice_id] = voice
        self._save()
        return voice

    def get(self, voice_id: str) -> Optional[VoiceGenome]:
        return self._voices.get(voice_id)

    def get_or_create(self, voice_id: str, **defaults: Any) -> VoiceGenome:
        existing = self._voices.get(voice_id)
        if existing is not None:
            return existing
        voice = VoiceGenome(voice_id=voice_id, **defaults)
        return self.create(voice)

    def update(self, voice_id: str, updates: Dict[str, Any]) -> Optional[VoiceGenome]:
        voice = self._voices.get(voice_id)
        if voice is None:
            return None
        voice.update(updates)
        self._save()
        return voice

    def upsert(self, voice_id: str, updates: Dict[str, Any]) -> VoiceGenome:
        voice = self._voices.get(voice_id)
        if voice is None:
            voice = VoiceGenome(voice_id=voice_id)
        voice.update(updates)
        self._voices[voice_id] = voice
        self._save()
        return voice

    def delete(self, voice_id: str) -> bool:
        if voice_id not in self._voices:
            return False
        del self._voices[voice_id]
        self._save()
        return True

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def list_ids(self) -> List[str]:
        return list(self._voices.keys())

    def __contains__(self, voice_id: str) -> bool:
        return voice_id in self._voices

    def __iter__(self) -> Iterator[str]:
        return iter(self._voices)

    def __len__(self) -> int:
        return len(self._voices)

    def search(self, query: str, limit: int = 10) -> List[VoiceGenome]:
        """Case-insensitive substring search over voice ids."""
        q = query.lower()
        results: List[VoiceGenome] = []
        for vid, voice in self._voices.items():
            if q in vid.lower():
                results.append(voice)
                if len(results) >= limit:
                    break
        return results

    def clear(self) -> None:
        self._voices.clear()
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return {vid: voice.to_dict() for vid, voice in self._voices.items()}