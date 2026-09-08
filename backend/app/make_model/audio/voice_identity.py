"""
Voice identity memory - persistence across generations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
import time
from pathlib import Path

from app.make_model.audio.types import VoiceGenome


class VoiceIdentityMemory:
    def __init__(self, storage_path: str = "/tmp/voice_identities.json") -> None:
        self.storage_path = Path(storage_path)
        self._identities: Dict[str, VoiceGenome] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            with open(self.storage_path, "r") as f:
                data = json.load(f)
            self._identities = {vid: VoiceGenome(**g) for vid, g in data.items()}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {vid: g.to_dict() for vid, g in self._identities.items()}
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def register(self, genome: VoiceGenome) -> None:
        self._identities[genome.voice_id] = genome
        self._save()

    def get(self, voice_id: str) -> Optional[VoiceGenome]:
        return self._identities.get(voice_id)

    def update(self, voice_id: str, updates: Dict[str, Any]) -> Optional[VoiceGenome]:
        genome = self._identities.get(voice_id)
        if not genome:
            return None
        for key, value in updates.items():
            if hasattr(genome, key):
                setattr(genome, key, value)
        genome.updated_at = time.time()
        self._save()
        return genome

    def list_voices(self) -> List[str]:
        return list(self._identities.keys())

    def delete(self, voice_id: str) -> bool:
        if voice_id in self._identities:
            del self._identities[voice_id]
            self._save()
            return True
        return False
