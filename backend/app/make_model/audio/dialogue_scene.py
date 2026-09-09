"""
Dialogue scene management with turn tracking and interruption markers.

A ``DialogueScene`` holds ordered ``DialogueTurn`` objects and tracks
interruptions, overlaps, and turn-taking metadata.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.make_model.audio.continuous_emotion import ContinuousEmotion


class TurnType(str, Enum):
    SPEECH = "speech"
    OVERLAP = "overlap"
    INTERRUPTEE = "interruption"
    BREATH = "breath"
    SILENCE = "silence"


@dataclass
class DialogueTurn:
    """A single conversational turn."""

    turn_id: str
    speaker_id: str
    text: str
    start_time: float = 0.0
    duration: float = 1.0
    emotion: ContinuousEmotion = field(default_factory=ContinuousEmotion.neutral)
    turn_type: TurnType = TurnType.SPEECH
    voice_id: Optional[str] = None
    interrupting: bool = False
    overlap_with: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "speaker_id": self.speaker_id,
            "text": self.text,
            "start_time": self.start_time,
            "duration": self.duration,
            "emotion": self.emotion.to_dict(),
            "turn_type": self.turn_type.value,
            "voice_id": self.voice_id,
            "interrupting": self.interrupting,
            "overlap_with": self.overlap_with,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueTurn":
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        if "emotion" in filtered and isinstance(filtered["emotion"], dict):
            filtered["emotion"] = ContinuousEmotion.from_dict(filtered["emotion"])
        if "turn_type" in filtered and not isinstance(filtered["turn_type"], TurnType):
            filtered["turn_type"] = TurnType(filtered["turn_type"])
        return cls(**filtered)


@dataclass
class InterruptionMarker:
    """Records an interruption or overlap event."""

    timestamp: float
    interrupter: str
    interrupted: str
    type: str = "interruption"  # interruption | overlap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "interrupter": self.interrupter,
            "interrupted": self.interrupted,
            "type": self.type,
        }


class DialogueScene:
    """Container for ordered dialogue turns with interruption/overlap markers."""

    def __init__(self, scene_id: str = "") -> None:
        self.scene_id = scene_id or f"scene_{int(time.time())}"
        self.turns: List[DialogueTurn] = []
        self.interruptions: List[InterruptionMarker] = []
        self.speakers: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {"created_at": time.time()}

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------
    def add_turn(self, turn: DialogueTurn) -> DialogueTurn:
        self.turns.append(turn)
        self.turns.sort(key=lambda t: t.start_time)
        if turn.speaker_id not in self.speakers:
            self.speakers[turn.speaker_id] = {"turn_count": 0, "total_speech": 0.0}
        self.speakers[turn.speaker_id]["turn_count"] += 1
        self.speakers[turn.speaker_id]["total_speech"] += turn.duration
        return turn

    def add_speech(
        self,
        speaker_id: str,
        text: str,
        start_time: float,
        duration: float,
        emotion: Optional[ContinuousEmotion] = None,
        voice_id: Optional[str] = None,
        turn_id: Optional[str] = None,
    ) -> DialogueTurn:
        turn = DialogueTurn(
            turn_id=turn_id or f"turn_{len(self.turns)}_{int(time.time() * 1000)}",
            speaker_id=speaker_id,
            text=text,
            start_time=start_time,
            duration=duration,
            emotion=emotion or ContinuousEmotion.neutral(),
            voice_id=voice_id,
        )
        return self.add_turn(turn)

    def remove_turn(self, turn_id: str) -> bool:
        before = len(self.turns)
        self.turns = [t for t in self.turns if t.turn_id != turn_id]
        return len(self.turns) != before

    def get_turn(self, turn_id: str) -> Optional[DialogueTurn]:
        for t in self.turns:
            if t.turn_id == turn_id:
                return t
        return None

    def get_speaker_turns(self, speaker_id: str) -> List[DialogueTurn]:
        return [t for t in self.turns if t.speaker_id == speaker_id]

    # ------------------------------------------------------------------
    # Interruption / overlap markers
    # ------------------------------------------------------------------
    def add_interruption(
        self,
        timestamp: float,
        interrupter: str,
        interrupted: str,
        type: str = "interruption",
    ) -> InterruptionMarker:
        marker = InterruptionMarker(
            timestamp=timestamp,
            interrupter=interrupter,
            interrupted=interrupted,
            type=type,
        )
        self.interruptions.append(marker)
        return marker

    def get_interruptions_for(self, speaker_id: str) -> List[InterruptionMarker]:
        return [
            m for m in self.interruptions
            if m.interrupter == speaker_id or m.interrupted == speaker_id
        ]

    def overlaps_at(self, timestamp: float) -> List[DialogueTurn]:
        """Return all turns active at ``timestamp``."""
        return [t for t in self.turns if t.start_time <= timestamp <= t.end_time]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    @property
    def duration(self) -> float:
        if not self.turns:
            return 0.0
        return max(t.end_time for t in self.turns)

    @property
    def turn_count(self) -> int:
        return len(self.turns)

    def speaker_ids(self) -> List[str]:
        return list(self.speakers.keys())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "turns": [t.to_dict() for t in self.turns],
            "interruptions": [m.to_dict() for m in self.interruptions],
            "speakers": dict(self.speakers),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DialogueScene":
        scene = cls(scene_id=data.get("scene_id", ""))
        scene.speakers = data.get("speakers", {})
        scene.metadata = data.get("metadata", {})
        for raw in data.get("turns", []):
            scene.add_turn(DialogueTurn.from_dict(raw))
        for raw in data.get("interruptions", []):
            scene.interruptions.append(InterruptionMarker(
                timestamp=raw["timestamp"],
                interrupter=raw["interrupter"],
                interrupted=raw["interrupted"],
                type=raw.get("type", "interruption"),
            ))
        return scene