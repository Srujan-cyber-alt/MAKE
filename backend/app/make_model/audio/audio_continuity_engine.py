"""
Audio continuity engine.

Maintains continuity across a project by tracking eight continuity types:
voice, emotion, room, mic, background, spatial, loudness, acoustic.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ContinuityType(str, Enum):
    VOICE = "voice"
    EMOTION = "emotion"
    ROOM = "room"
    MIC = "mic"
    BACKGROUND = "background"
    SPATIAL = "spatial"
    LOUDNESS = "loudness"
    ACOUSTIC = "acoustic"


CONTINUITY_TYPES: Tuple[str, ...] = tuple(t.value for t in ContinuityType)


@dataclass
class ContinuityState:
    """Snapshot of a single continuity dimension."""

    continuity_type: ContinuityType
    value: Any
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "continuity_type": self.continuity_type.value,
            "value": self.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContinuityState":
        return cls(
            continuity_type=ContinuityType(data.get("continuity_type", "voice")),
            value=data.get("value"),
            confidence=float(data.get("confidence", 1.0)),
            timestamp=float(data.get("timestamp", time.time())),
        )


class AudioContinuityEngine:
    """Maintains continuity across a project with 8 continuity types."""

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self.storage_path = Path(storage_path) if storage_path else Path("/tmp/audio_continuity_engine.json")
        self._states: Dict[str, ContinuityState] = {}
        self._history: List[ContinuityState] = []
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
        for raw in data.get("states", []):
            state = ContinuityState.from_dict(raw)
            self._states[state.continuity_type.value] = state
            self._history.append(state)

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "states": [s.to_dict() for s in self._states.values()],
            "history": [s.to_dict() for s in self._history[-100:]],
        }
        tmp = self.storage_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        tmp.replace(self.storage_path)

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------
    def set_state(self, continuity_type: ContinuityType, value: Any, confidence: float = 1.0) -> ContinuityState:
        state = ContinuityState(continuity_type=continuity_type, value=value, confidence=confidence)
        self._states[continuity_type.value] = state
        self._history.append(state)
        self._save()
        return state

    def get_state(self, continuity_type: ContinuityType) -> Optional[ContinuityState]:
        return self._states.get(continuity_type.value)

    def get_all_states(self) -> Dict[str, ContinuityState]:
        return dict(self._states)

    def get_history(self, continuity_type: Optional[ContinuityType] = None) -> List[ContinuityState]:
        if continuity_type is None:
            return list(self._history)
        return [s for s in self._history if s.continuity_type == continuity_type]

    def snapshot(self) -> Dict[str, Any]:
        return {ct: self.get_state(ContinuityType(ct)).value if self.get_state(ContinuityType(ct)) else None for ct in CONTINUITY_TYPES}

    # ------------------------------------------------------------------
    # Diffing
    # ------------------------------------------------------------------
    def diff(self, other: "AudioContinuityEngine") -> Dict[str, Dict[str, Any]]:
        result: Dict[str, Dict[str, Any]] = {}
        for ct in CONTINUITY_TYPES:
            ctype = ContinuityType(ct)
            a = self.get_state(ctype)
            b = other.get_state(ctype)
            result[ct] = {
                "before": a.value if a else None,
                "after": b.value if b else None,
                "changed": (a.value if a else None) != (b.value if b else None),
            }
        return result

    def continuity_hash(self) -> str:
        payload = repr(sorted((k, str(v.value)) for k, v in self._states.items()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]