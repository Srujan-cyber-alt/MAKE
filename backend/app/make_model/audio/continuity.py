"""
Audio continuity memory - remember how a scene sounded.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import time
import json
from pathlib import Path


class AudioContinuityMemory:
    def __init__(self, storage_path: str = "/tmp/audio_continuity.json") -> None:
        self.storage_path = Path(storage_path)
        self._scenes: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            with open(self.storage_path, "r") as f:
                self._scenes = json.load(f)

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self._scenes, f, indent=2)

    def record_scene(self, scene_id: str, audio_state: Dict[str, Any]) -> None:
        self._scenes[scene_id] = {
            "audio_state": audio_state,
            "timestamp": time.time(),
        }
        self._save()

    def get_scene(self, scene_id: str) -> Optional[Dict[str, Any]]:
        return self._scenes.get(scene_id)

    def update_scene(self, scene_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return None
        scene["audio_state"].update(updates)
        scene["timestamp"] = time.time()
        self._save()
        return scene

    def list_scenes(self) -> List[str]:
        return list(self._scenes.keys())

    def get_continuity_report(self, scene_id: str) -> Dict[str, Any]:
        scene = self._scenes.get(scene_id)
        if not scene:
            return {"status": "not_found"}
        return {
            "status": "found",
            "last_updated": scene["timestamp"],
            "audio_state": scene["audio_state"],
        }
