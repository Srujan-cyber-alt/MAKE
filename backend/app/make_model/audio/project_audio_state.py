"""
Project audio state persistence.

Stores scene ordering and continuity information (voice, emotion, room, mic,
background, spatial, loudness, acoustic) for an entire project.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.make_model.audio.audio_continuity_engine import (
    AudioContinuityEngine,
    ContinuityType,
)


@dataclass
class SceneEntry:
    scene_id: str
    order: int
    audio_state: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "order": self.order,
            "audio_state": dict(self.audio_state),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneEntry":
        return cls(
            scene_id=data["scene_id"],
            order=int(data.get("order", 0)),
            audio_state=dict(data.get("audio_state", {})),
            timestamp=float(data.get("timestamp", time.time())),
        )


class ProjectAudioState:
    """JSON persistence, scene ordering, and continuity tracking."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else Path("/tmp/project_audio_state.json")
        self.continuity = AudioContinuityEngine(str(self.storage_path.with_suffix(".continuity.json")))
        self.scenes: List[SceneEntry] = []
        self.metadata: Dict[str, Any] = {"created_at": time.time()}
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
        self.scenes = [SceneEntry.from_dict(s) for s in data.get("scenes", [])]
        self.scenes.sort(key=lambda s: s.order)
        self.metadata = data.get("metadata", {"created_at": time.time()})

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "scenes": [s.to_dict() for s in self.scenes],
            "metadata": dict(self.metadata),
        }
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(self.storage_path)

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------
    def add_scene(self, scene_id: str, audio_state: Dict[str, Any], order: Optional[int] = None) -> SceneEntry:
        if order is None:
            order = len(self.scenes)
        entry = SceneEntry(scene_id=scene_id, order=order, audio_state=audio_state)
        self.scenes.append(entry)
        self.scenes.sort(key=lambda s: s.order)
        # Update continuity from this scene's audio state.
        self._apply_continuity(audio_state)
        self._save()
        return entry

    def remove_scene(self, scene_id: str) -> bool:
        before = len(self.scenes)
        self.scenes = [s for s in self.scenes if s.scene_id != scene_id]
        if len(self.scenes) != before:
            self._renumber()
            self._save()
            return True
        return False

    def _renumber(self) -> None:
        for idx, scene in enumerate(self.scenes):
            scene.order = idx

    def get_scene(self, scene_id: str) -> Optional[SceneEntry]:
        for s in self.scenes:
            if s.scene_id == scene_id:
                return s
        return None

    def get_scene_order(self) -> List[str]:
        return [s.scene_id for s in self.scenes]

    def reorder(self, scene_ids: List[str]) -> None:
        order_map = {sid: idx for idx, sid in enumerate(scene_ids)}
        for scene in self.scenes:
            if scene.scene_id in order_map:
                scene.order = order_map[scene.scene_id]
        self.scenes.sort(key=lambda s: s.order)
        self._save()

    # ------------------------------------------------------------------
    # Continuity helpers
    # ------------------------------------------------------------------
    def _apply_continuity(self, audio_state: Dict[str, Any]) -> None:
        mapping = {
            "voice": ContinuityType.VOICE,
            "emotion": ContinuityType.EMOTION,
            "room": ContinuityType.ROOM,
            "mic": ContinuityType.MIC,
            "background": ContinuityType.BACKGROUND,
            "spatial": ContinuityType.SPATIAL,
            "loudness": ContinuityType.LOUDNESS,
            "acoustic": ContinuityType.ACOUSTIC,
        }
        for key, ctype in mapping.items():
            if key in audio_state:
                self.continuity.set_state(ctype, audio_state[key])

    def set_continuity(self, continuity_type: ContinuityType, value: Any) -> None:
        self.continuity.set_state(continuity_type, value)

    def get_continuity(self, continuity_type: ContinuityType) -> Optional[Any]:
        state = self.continuity.get_state(continuity_type)
        return state.value if state else None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "scene_order": self.get_scene_order(),
            "scenes": [s.to_dict() for s in self.scenes],
            "continuity": self.continuity.snapshot(),
            "metadata": dict(self.metadata),
        }